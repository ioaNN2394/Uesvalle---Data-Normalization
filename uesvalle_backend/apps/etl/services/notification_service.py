import logging
from django.db import transaction
from django.utils import timezone
from ..models import Institucion, Visita, Notification
from ..services import MySQLExtractor

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Servicio para verificar cambios en el concepto sanitario y generar notificaciones.
    """

    def check_for_updates(self):
        """
        Verifica si hay cambios en el concepto sanitario en MySQL comparado con Supabase.
        Si hay cambios:
        1. Actualiza Supabase.
        2. Crea una notificación.
        """
        try:
            # Usar MySQLExtractor para obtener los datos de MySQL
            extractor = MySQLExtractor(db_alias='source_mysql')
            
            query = """
                SELECT 
                    v.identificacion, 
                    v.conceptovisita,
                    v.fechavisita
                FROM visitas_instituciones_educativos v
                INNER JOIN (
                    SELECT identificacion, MAX(fechavisita) as max_fecha
                    FROM visitas_instituciones_educativos
                    GROUP BY identificacion
                ) latest ON v.identificacion = latest.identificacion AND v.fechavisita = latest.max_fecha
                WHERE v.conceptovisita IN ('F', 'D', 'FCR')
            """
            
            # Extraer datos de MySQL
            result = extractor.extract(
                table_name='visitas_instituciones_educativos',
                query=query
            )
            
            mysql_results = result.dataframe.values if result.dataframe is not None else []
            logger.info(f"MySQL returned {len(mysql_results)} rows for concept check.")
            
            notifications_created = 0

            for row in mysql_results:
                uesvalle_id = str(row[0])  # identificacion
                new_concept = row[1]       # conceptovisita
                fecha_visita = row[2]      # fechavisita

                # Buscar la institución en Supabase
                try:
                    institucion = Institucion.objects.get(uesvalle_ie_id=uesvalle_id)
                except Institucion.DoesNotExist:
                    # logger.debug(f"Institution {uesvalle_id} not found in Supabase.")
                    continue

                # Buscar la última visita registrada en Supabase para esta institución
                last_visit = Visita.objects.filter(institucion_id=institucion.id).order_by('-fechavisita').first()

                old_concept = None
                if last_visit:
                    old_concept = last_visit.conceptovisita

                # logger.debug(f"Checking {institucion.nombre} ({uesvalle_id}): Old={old_concept}, New={new_concept}")

                # Caso 1: Ya teníamos una visita, y el concepto cambió
                if last_visit and old_concept != new_concept:
                    logger.info(f"Change detected for {institucion.nombre}: {old_concept} -> {new_concept}")
                    # Crear notificación
                    Notification.objects.create(
                        institucion=institucion,
                        old_concept=old_concept,
                        new_concept=new_concept
                    )
                    notifications_created += 1
                    
                    # Actualizar la visita en Supabase (o crear una nueva si la fecha es distinta)
                    # Convertir fecha_visita a date si es datetime para comparar
                    if hasattr(fecha_visita, 'date'):
                        fecha_visita_date = fecha_visita.date()
                    else:
                        fecha_visita_date = fecha_visita

                    if last_visit.fechavisita == fecha_visita_date:
                        last_visit.conceptovisita = new_concept
                        last_visit.save()
                    else:
                        # Es una nueva visita en fecha distinta
                        Visita.objects.create(
                            institucion_id=institucion.id,
                            fechavisita=fecha_visita,
                            conceptovisita=new_concept,
                        )
                
                # Caso 2: No teníamos visita, es la primera.
                elif not last_visit:
                    logger.info(f"New visit detected for {institucion.nombre}: {new_concept}")
                    # Crear la visita
                    Visita.objects.create(
                        institucion_id=institucion.id,
                        fechavisita=fecha_visita,
                        conceptovisita=new_concept
                    )

            logger.info(f"Check complete. Created {notifications_created} notifications.")
            return notifications_created

        except Exception as e:
            logger.error(f"Error verificando actualizaciones: {e}", exc_info=True)
            return 0
