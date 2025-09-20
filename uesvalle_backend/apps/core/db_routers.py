"""
Database routers para controlar el acceso a múltiples bases de datos.
"""


class SourceReadOnlyRouter:
    """
    Router para evitar que Django migre o escriba en la BD de origen (MySQL).
    Controla donde se ejecutan las operaciones de base de datos basado en el modelo.
    """

    source_label = "etl_source"  # si usas modelos 'inspectdb' para leer

    def db_for_read(self, model, **hints):
        """Determina qué base de datos usar para leer un modelo específico."""
        if model._meta.app_label == self.source_label:
            return "source_mysql"
        return None

    def db_for_write(self, model, **hints):
        """Determina qué base de datos usar para escribir un modelo específico."""
        if model._meta.app_label == self.source_label:
            # Retorna None para evitar escrituras en la fuente MySQL
            return None
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """Permite relaciones entre objetos si están en la misma base de datos."""
        db_set = {'default', 'source_mysql'}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Controla qué migraciones se ejecutan en cada base de datos.
        Evita migraciones en la BD fuente MySQL.
        """
        if app_label == self.source_label:
            return False
        
        # Solo permite migraciones en la BD default (Supabase) para apps del ETL
        if db == 'source_mysql':
            return False
        elif db == 'default':
            return app_label in ['etl', 'core', 'reports', 'auth', 'contenttypes', 'sessions', 'admin']
        
        return None