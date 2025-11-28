import logging
from datetime import date, datetime
from django.db import transaction
from django.utils import timezone
from ..models import Institucion, Visita, Notification
from ..services import MySQLExtractor

logger = logging.getLogger(__name__)


def normalize_concept(concept):
    """
    Normaliza el valor del concepto de visita para comparación consistente.
    Elimina espacios, convierte a mayúsculas y valida valores permitidos.
    """
    if concept is None:
        return None
    
    # Convertir a string, eliminar espacios y convertir a mayúsculas
    normalized = str(concept).strip().upper()
    
    # Validar que sea un valor permitido
    if normalized in ('F', 'D', 'FCR'):
        return normalized
    
    # Si no es válido, retornar None
    return None


def make_composite_key(identificacion: str, nombre: str) -> str:
    """
    Crea una clave compuesta normalizada para identificar instituciones únicas.
    """
    id_norm = str(identificacion).strip().upper() if identificacion else ''
    nombre_norm = str(nombre).strip().upper() if nombre else ''
    return f"{id_norm}|{nombre_norm}"


class NotificationService:
    """
    Servicio para verificar cambios en el concepto sanitario y generar notificaciones.
    
    IMPORTANTE: Este servicio SOLO debe generar notificaciones cuando hay CAMBIOS NUEVOS
    en MySQL que aún no están reflejados en Supabase. Después de un ETL fresco, 
    NO debe generar notificaciones porque los datos ya están sincronizados.
    
    Flujo:
    1. Consulta MySQL para obtener el concepto más reciente de cada institución
    2. Compara con el concepto actual en Supabase usando clave compuesta (identificacion + nombre)
    3. Solo genera notificación si:
       - La institución existe en ambas fuentes (coincidencia exacta por clave compuesta)
       - El concepto en MySQL es DIFERENTE al de Supabase
       - La fecha de visita en MySQL es MÁS RECIENTE que la de Supabase
    """

    def check_for_updates(self):
        """
        Verifica si hay cambios NUEVOS en el concepto sanitario en MySQL comparado con Supabase.
        
        Returns:
            int: Número de notificaciones creadas
        """
        try:
            # 1. PRIMERO: Construir diccionario de instituciones de Supabase por clave compuesta
            logger.info("[NotificationService] Construyendo índice de instituciones de Supabase...")
            
            supabase_instituciones = {}
            for inst in Institucion.objects.filter(uesvalle_ie_id__isnull=False).select_related():
                key = make_composite_key(inst.uesvalle_ie_id, inst.nombre)
                supabase_instituciones[key] = inst
            
            logger.info(f"[NotificationService] {len(supabase_instituciones)} instituciones indexadas en Supabase")
            
            # 2. Obtener última visita de cada institución en Supabase
            logger.info("[NotificationService] Obteniendo última visita de cada institución...")
            
            supabase_last_visits = {}
            for inst_key, inst in supabase_instituciones.items():
                last_visit = Visita.objects.filter(
                    institucion_id=inst.id
                ).order_by('-fechavisita').first()
                
                if last_visit:
                    supabase_last_visits[inst_key] = {
                        'visita': last_visit,
                        'concepto': normalize_concept(last_visit.conceptovisita),
                        'fecha': last_visit.fechavisita
                    }
            
            logger.info(f"[NotificationService] {len(supabase_last_visits)} visitas indexadas")
            
            # 3. Consultar MySQL para obtener el concepto más reciente de cada institución
            extractor = MySQLExtractor(db_alias='source_mysql')
            
            query = """
                SELECT 
                    v.identificacion, 
                    v.nombreestablecimiento,
                    v.conceptovisita,
                    v.fechavisita
                FROM visitas_instituciones_educativos v
                INNER JOIN (
                    SELECT identificacion, nombreestablecimiento, MAX(fechavisita) as max_fecha
                    FROM visitas_instituciones_educativos
                    GROUP BY identificacion, nombreestablecimiento
                ) latest ON v.identificacion = latest.identificacion 
                        AND v.nombreestablecimiento = latest.nombreestablecimiento 
                        AND v.fechavisita = latest.max_fecha
                WHERE v.conceptovisita IS NOT NULL 
                  AND TRIM(v.conceptovisita) != ''
            """
            
            result = extractor.extract(
                table_name='visitas_instituciones_educativos',
                query=query
            )
            
            mysql_results = result.dataframe.values if result.dataframe is not None else []
            logger.info(f"[NotificationService] MySQL returned {len(mysql_results)} rows for concept check.")
            
            # 4. Comparar y generar notificaciones solo donde hay cambios REALES
            notifications_created = 0
            skipped_same_concept = 0
            skipped_not_newer = 0
            skipped_no_match = 0

            for row in mysql_results:
                uesvalle_id = str(row[0]).strip()
                nombre_mysql = str(row[1]).strip() if row[1] else ''
                mysql_concept_raw = row[2]
                fecha_visita_mysql = row[3]
                
                # Normalizar concepto de MySQL
                mysql_concept = normalize_concept(mysql_concept_raw)
                if mysql_concept is None:
                    continue
                
                # Crear clave compuesta para buscar coincidencia EXACTA
                mysql_key = make_composite_key(uesvalle_id, nombre_mysql)
                
                # Buscar institución en Supabase por clave compuesta EXACTA (sin fallbacks)
                if mysql_key not in supabase_instituciones:
                    skipped_no_match += 1
                    continue
                
                institucion = supabase_instituciones[mysql_key]
                
                # Verificar si existe visita en Supabase para esta institución
                if mysql_key not in supabase_last_visits:
                    # No hay visita en Supabase - esto no debería pasar después de ETL
                    # pero por si acaso, no generar notificación
                    continue
                
                supabase_data = supabase_last_visits[mysql_key]
                supabase_concept = supabase_data['concepto']
                supabase_fecha = supabase_data['fecha']
                last_visit = supabase_data['visita']
                
                # Si los conceptos son iguales, no hay cambio
                if mysql_concept == supabase_concept:
                    skipped_same_concept += 1
                    continue
                
                # Convertir fechas para comparación
                mysql_fecha = self._normalize_date(fecha_visita_mysql)
                supabase_fecha_norm = self._normalize_date(supabase_fecha)
                
                # IMPORTANTE: Solo generar notificación si la fecha de MySQL es MÁS RECIENTE
                # Esto evita notificaciones falsas cuando los datos ya están sincronizados
                if mysql_fecha and supabase_fecha_norm:
                    if mysql_fecha <= supabase_fecha_norm:
                        # La visita de MySQL no es más reciente - no hay cambio nuevo
                        skipped_not_newer += 1
                        continue
                
                # Verificar que no exista notificación pendiente duplicada
                existing_notification = Notification.objects.filter(
                    institucion=institucion,
                    old_concept=supabase_concept,
                    new_concept=mysql_concept,
                    is_read=False
                ).exists()
                
                if existing_notification:
                    logger.debug(f"[NotificationService] Skipping duplicate notification for {institucion.nombre}")
                    continue
                
                # ¡HAY UN CAMBIO REAL! Crear notificación
                logger.info(f"[NotificationService] CAMBIO DETECTADO: {institucion.nombre} ({uesvalle_id}): {supabase_concept} -> {mysql_concept}")
                logger.info(f"   Fecha MySQL: {mysql_fecha}, Fecha Supabase: {supabase_fecha_norm}")
                
                with transaction.atomic():
                    # Crear notificación
                    Notification.objects.create(
                        institucion=institucion,
                        old_concept=supabase_concept,
                        new_concept=mysql_concept
                    )
                    notifications_created += 1
                    
                    # Actualizar la visita en Supabase
                    last_visit.conceptovisita = mysql_concept
                    last_visit.save()
                    
                    logger.info(f"[NotificationService] Actualizado en Supabase: {institucion.nombre}")

            # Resumen
            logger.info(f"[NotificationService] === RESUMEN ===")
            logger.info(f"   Notificaciones creadas: {notifications_created}")
            logger.info(f"   Omitidos (mismo concepto): {skipped_same_concept}")
            logger.info(f"   Omitidos (fecha no más reciente): {skipped_not_newer}")
            logger.info(f"   Omitidos (sin coincidencia exacta): {skipped_no_match}")
            
            return notifications_created

        except Exception as e:
            logger.error(f"[NotificationService] Error verificando actualizaciones: {e}", exc_info=True)
            return 0
    
    def _normalize_date(self, fecha) -> date:
        """Normaliza una fecha a tipo date para comparación."""
        if fecha is None:
            return None
        if isinstance(fecha, datetime):
            return fecha.date()
        if isinstance(fecha, date):
            return fecha
        # Intentar parsear string
        try:
            from dateutil import parser
            return parser.parse(str(fecha)).date()
        except:
            return None
