import logging
from django.db import transaction
from django.utils import timezone
from .models import Institucion, Visita, Notification
from .services import MySQLExtractor

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
        extractor = MySQLExtractor()
        conn = extractor._get_mysql_connection()
        
        if not conn:
            logger.error("No se pudo conectar a MySQL para verificar actualizaciones.")
            return 0

        try:
            cursor = conn.cursor()
            # Consulta para obtener la última visita por institución en MySQL
            # Asumimos que la tabla es 'visitas_instituciones_educativos' y tiene 'identificacion' (uesvalle_ie_id)
            # y 'conceptovisita'.
            # Necesitamos la visita más reciente por institución.
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
            cursor.execute(query)
            mysql_results = cursor.fetchall()
            
            notifications_created = 0

            for row in mysql_results:
                uesvalle_id = str(row[0]) # identificacion
                new_concept = row[1]      # conceptovisita
                fecha_visita = row[2]     # fechavisita

                # Buscar la institución en Supabase
                try:
                    institucion = Institucion.objects.get(uesvalle_ie_id=uesvalle_id)
                except Institucion.DoesNotExist:
                    continue

                # Buscar la última visita registrada en Supabase para esta institución
                last_visit = Visita.objects.filter(institucion_id=institucion.id).order_by('-fechavisita').first()

                old_concept = None
                if last_visit:
                    old_concept = last_visit.conceptovisita

                # Si no hay visita previa, o el concepto es diferente, y la fecha es más reciente o igual (para actualizar)
                # Pero la notificación solo tiene sentido si CAMBIÓ el concepto respecto a lo que teníamos.
                
                # Caso 1: Ya teníamos una visita, y el concepto cambió
                if last_visit and old_concept != new_concept:
                    # Verificar si esta visita "nueva" de MySQL es realmente nueva o es una corrección de la misma fecha
                    # O si es una fecha posterior.
                    
                    # Si la fecha de MySQL es posterior a la que tenemos, es una nueva visita -> Cambio de concepto
                    # Si la fecha es la misma, puede ser una corrección -> Cambio de concepto
                    
                    # Actualizamos o creamos la visita en Supabase
                    # Para simplificar, asumimos que si detectamos diferencia en la "última" visita, notificamos.
                    
                    # Crear notificación
                    Notification.objects.create(
                        institucion=institucion,
                        old_concept=old_concept,
                        new_concept=new_concept
                    )
                    notifications_created += 1
                    
                    # Actualizar la visita en Supabase (o crear una nueva si la fecha es distinta)
                    if last_visit.fechavisita == fecha_visita:
                        last_visit.conceptovisita = new_concept
                        last_visit.save()
                    else:
                        # Es una nueva visita en fecha distinta
                        Visita.objects.create(
                            institucion_id=institucion.id,
                            fechavisita=fecha_visita,
                            conceptovisita=new_concept,
                            # Otros campos se podrían llenar si hiciéramos un fetch completo
                        )
                
                # Caso 2: No teníamos visita, es la primera.
                elif not last_visit:
                     # Crear la visita
                    Visita.objects.create(
                        institucion_id=institucion.id,
                        fechavisita=fecha_visita,
                        conceptovisita=new_concept
                    )
                    # Opcional: Notificar "Nuevo concepto inicial"
                    # El requerimiento dice "si una institucion antes tenia el concepto en F y luego paso a FCR"
                    # Implica cambio. Si no tenía nada, tal vez no sea notificación de cambio.
                    pass

            return notifications_created

        except Exception as e:
            logger.error(f"Error verificando actualizaciones: {e}")
            return 0
        finally:
            if conn:
                conn.close()
