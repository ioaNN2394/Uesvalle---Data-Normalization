import logging
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


class NotificationService:
    """
    Servicio para verificar cambios en el concepto sanitario y generar notificaciones.
    
    Flujo:
    1. Consulta MySQL para obtener el concepto más reciente de cada institución
    2. Compara con el concepto actual en Supabase
    3. Si hay diferencia: actualiza Supabase y crea notificación
    """

    def check_for_updates(self):
        """
        Verifica si hay cambios en el concepto sanitario en MySQL comparado con Supabase.
        Si hay cambios:
        1. Actualiza Supabase.
        2. Crea una notificación.
        
        IMPORTANTE: Ahora usa clave compuesta (identificacion + nombreestablecimiento) porque
        puede haber instituciones con el mismo código pero diferente nombre.
        
        Returns:
            int: Número de notificaciones creadas
        """
        try:
            # Usar MySQLExtractor para obtener los datos de MySQL
            extractor = MySQLExtractor(db_alias='source_mysql')
            
            # Query para obtener el concepto más reciente de cada institución en MySQL
            # IMPORTANTE: Incluir nombreestablecimiento para identificar instituciones únicas
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
            
            # Extraer datos de MySQL
            result = extractor.extract(
                table_name='visitas_instituciones_educativos',
                query=query
            )
            
            mysql_results = result.dataframe.values if result.dataframe is not None else []
            logger.info(f"[NotificationService] MySQL returned {len(mysql_results)} rows for concept check.")
            
            notifications_created = 0

            for row in mysql_results:
                uesvalle_id = str(row[0]).strip()   # identificacion
                nombre_mysql = str(row[1]).strip() if row[1] else ''  # nombreestablecimiento
                mysql_concept_raw = row[2]          # conceptovisita (raw)
                fecha_visita = row[3]               # fechavisita
                
                # Normalizar el concepto de MySQL
                mysql_concept = normalize_concept(mysql_concept_raw)
                
                # Si el concepto no es válido, ignorar
                if mysql_concept is None:
                    continue

                # Buscar la institución en Supabase usando clave compuesta
                institucion = None
                if nombre_mysql:
                    # Buscar por uesvalle_ie_id + nombre (clave compuesta)
                    institucion = Institucion.objects.filter(
                        uesvalle_ie_id=uesvalle_id,
                        nombre__iexact=nombre_mysql
                    ).first()
                
                # Fallback: buscar solo por uesvalle_ie_id (tomar el primero)
                if not institucion:
                    institucion = Institucion.objects.filter(
                        uesvalle_ie_id=uesvalle_id
                    ).first()
                
                if not institucion:
                    continue

                # Buscar la última visita registrada en Supabase para esta institución
                last_visit = Visita.objects.filter(
                    institucion_id=institucion.id
                ).order_by('-fechavisita').first()

                # Obtener y normalizar el concepto actual en Supabase
                supabase_concept = None
                if last_visit:
                    supabase_concept = normalize_concept(last_visit.conceptovisita)

                # Comparar conceptos normalizados
                # Solo generar notificación si AMBOS tienen valores válidos y son DIFERENTES
                if last_visit and supabase_concept is not None and mysql_concept != supabase_concept:
                    
                    # Verificar que no exista ya una notificación pendiente (no leída) 
                    # para esta institución con el mismo cambio
                    existing_notification = Notification.objects.filter(
                        institucion=institucion,
                        old_concept=supabase_concept,
                        new_concept=mysql_concept,
                        is_read=False
                    ).exists()
                    
                    if existing_notification:
                        logger.debug(f"[NotificationService] Skipping duplicate notification for {institucion.nombre}")
                        continue
                    
                    logger.info(f"[NotificationService] Change detected for {institucion.nombre} ({uesvalle_id}): {supabase_concept} -> {mysql_concept}")
                    
                    # Usar transacción para asegurar consistencia
                    with transaction.atomic():
                        # Crear notificación
                        Notification.objects.create(
                            institucion=institucion,
                            old_concept=supabase_concept,
                            new_concept=mysql_concept
                        )
                        notifications_created += 1
                        
                        # Actualizar la visita en Supabase
                        # Convertir fecha_visita a date si es datetime
                        if hasattr(fecha_visita, 'date'):
                            fecha_visita_date = fecha_visita.date()
                        else:
                            fecha_visita_date = fecha_visita

                        # Actualizar el concepto de la última visita existente
                        last_visit.conceptovisita = mysql_concept
                        last_visit.save()
                        
                        logger.info(f"[NotificationService] Updated Supabase for {institucion.nombre}: conceptovisita = {mysql_concept}")
                
                # Caso: No hay visita en Supabase, crear una nueva (sin notificación)
                elif not last_visit:
                    # Convertir fecha
                    if hasattr(fecha_visita, 'date'):
                        fecha_visita_date = fecha_visita.date()
                    else:
                        fecha_visita_date = fecha_visita
                    
                    Visita.objects.create(
                        institucion_id=institucion.id,
                        fechavisita=fecha_visita_date,
                        conceptovisita=mysql_concept,
                    )
                    logger.debug(f"[NotificationService] Created initial visit for {institucion.nombre}: {mysql_concept}")

            logger.info(f"[NotificationService] Check complete. Created {notifications_created} notifications.")
            return notifications_created

        except Exception as e:
            logger.error(f"[NotificationService] Error verificando actualizaciones: {e}", exc_info=True)
            return 0
