"""
Database routers para controlar el acceso a múltiples bases de datos.
Maneja routing entre MySQL (fuente) y Supabase (destino).
"""


class DatabaseRouter:
    """
    Router principal para dirigir operaciones entre múltiples bases de datos:
    - source_mysql: Base de datos MySQL de origen (solo lectura)
    - default: Supabase PostgreSQL de destino (lectura/escritura)
    """

    # Modelos que deben ir a MySQL (solo lectura)
    mysql_source_models = {
        'stginstitucionmysql',  # Modelos de staging desde MySQL
    }
    
    # Apps que van a la base de datos principal (Supabase)
    target_apps = {'etl', 'core', 'reports', 'auth', 'contenttypes', 'sessions', 'admin'}

    def db_for_read(self, model, **hints):
        """Determina qué base de datos usar para lectura."""
        model_name = model._meta.model_name.lower()
        
        # Modelos de staging van a MySQL
        if model_name in self.mysql_source_models:
            return 'source_mysql'
        
        # Todos los demás a Supabase por defecto
        return 'default'

    def db_for_write(self, model, **hints):
        """Determina qué base de datos usar para escritura."""
        model_name = model._meta.model_name.lower()
        
        # NUNCA escribir en MySQL (solo lectura)
        if model_name in self.mysql_source_models:
            return None  # Esto previene escrituras
        
        # Escribir en Supabase para todos los demás
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """
        Permite relaciones entre objetos.
        Solo permite relaciones dentro de la misma BD.
        """
        db_set = {'default', 'source_mysql'}
        
        if obj1 and obj2:
            if hasattr(obj1, '_state') and hasattr(obj2, '_state'):
                if obj1._state.db in db_set and obj2._state.db in db_set:
                    # Permite relaciones si están en la misma BD
                    return obj1._state.db == obj2._state.db
        
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Controla qué migraciones van a qué base de datos.
        """
        # NUNCA migrar en MySQL (es fuente externa)
        if db == 'source_mysql':
            return False
        
        # Migrar en Supabase solo para apps específicas
        if db == 'default':
            return app_label in self.target_apps
        
        return None


class SourceReadOnlyRouter:
    """
    Router legacy mantenido por compatibilidad.
    Redirige a DatabaseRouter para funcionalidad completa.
    """
    
    def __init__(self):
        self.main_router = DatabaseRouter()
    
    def db_for_read(self, model, **hints):
        return self.main_router.db_for_read(model, **hints)
    
    def db_for_write(self, model, **hints):
        return self.main_router.db_for_write(model, **hints)
    
    def allow_relation(self, obj1, obj2, **hints):
        return self.main_router.allow_relation(obj1, obj2, **hints)
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return self.main_router.allow_migrate(db, app_label, model_name, **hints)