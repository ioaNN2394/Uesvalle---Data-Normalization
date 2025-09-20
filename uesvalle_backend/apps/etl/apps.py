from django.apps import AppConfig


class EtlConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.etl'
    verbose_name = 'ETL - Extract Transform Load'
    
    def ready(self):
        """Configuración cuando la app está lista."""
        import logging
        
        # Configurar logging para ETL
        logger = logging.getLogger('apps.etl')
        logger.setLevel(logging.INFO)
