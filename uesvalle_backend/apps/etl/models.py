"""
Modelos para almacenar los datos procesados del ETL.
Sigue el patrón dim_* (dimensiones) y fact_* (hechos) para el data warehouse.
"""
from django.db import models
from django.utils import timezone


class ETLRun(models.Model):
    """Registro de ejecuciones del ETL para auditoría y monitoreo."""
    
    STATUS_CHOICES = [
        ('running', 'En ejecución'),
        ('success', 'Exitoso'),
        ('failed', 'Fallido'),
        ('cancelled', 'Cancelado'),
    ]
    
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="Iniciado en")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="Finalizado en")
    status = models.CharField(
        max_length=30, 
        choices=STATUS_CHOICES,
        default="running", 
        verbose_name="Estado"
    )
    meta = models.JSONField(
        default=dict, 
        verbose_name="Metadatos",
        help_text="Información adicional como conteos, errores, etc."
    )
    
    class Meta:
        verbose_name = "Ejecución ETL"
        verbose_name_plural = "Ejecuciones ETL"
        ordering = ['-started_at']
    
    def __str__(self):
        return f"ETL Run {self.id} - {self.status} ({self.started_at})"
    
    @property
    def duration(self):
        """Duración de la ejecución en segundos."""
        if self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        elif self.status == 'running':
            return (timezone.now() - self.started_at).total_seconds()
        return None


class DimMunicipio(models.Model):
    """Dimensión de municipios - catálogo normalizado."""
    
    codigo = models.CharField(
        max_length=12, 
        unique=True, 
        verbose_name="Código DANE",
        help_text="Código único DANE del municipio"
    )
    nombre = models.CharField(max_length=120, verbose_name="Nombre del municipio")
    departamento_codigo = models.CharField(
        max_length=2, 
        null=True, 
        blank=True,
        verbose_name="Código del departamento"
    )
    departamento_nombre = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        verbose_name="Nombre del departamento"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Municipio"
        verbose_name_plural = "Municipios"
        ordering = ['departamento_nombre', 'nombre']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['departamento_codigo']),
        ]
    
    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


class DimSede(models.Model):
    """Dimensión de sedes educativas - catálogo normalizado."""
    
    codigo = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name="Código de sede"
    )
    nombre = models.CharField(max_length=255, verbose_name="Nombre de la sede")
    institucion_codigo = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Código de institución"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Sede"
        verbose_name_plural = "Sedes"
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['institucion_codigo']),
        ]
    
    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


class FactInstitucion(models.Model):
    """Tabla de hechos principal - instituciones educativas consolidadas."""
    
    ESTADO_CHOICES = [
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo'),
        ('Suspendido', 'Suspendido'),
        ('En Proceso', 'En Proceso'),
    ]
    
    SECTOR_CHOICES = [
        ('Oficial', 'Oficial'),
        ('No Oficial', 'No Oficial'),
    ]
    
    ZONA_CHOICES = [
        ('Urbana', 'Urbana'),
        ('Rural', 'Rural'),
    ]
    
    # Clave natural única
    codigo_dane = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name="Código DANE",
        help_text="Código único DANE de la institución"
    )
    
    # Información básica
    nombre = models.CharField(max_length=255, verbose_name="Nombre de la institución")
    
    # Relaciones con dimensiones
    municipio = models.ForeignKey(
        DimMunicipio, 
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Municipio"
    )
    
    # Atributos de la institución
    estado = models.CharField(
        max_length=40, 
        choices=ESTADO_CHOICES,
        default='Activo',
        verbose_name="Estado"
    )
    sector = models.CharField(
        max_length=20,
        choices=SECTOR_CHOICES,
        null=True,
        blank=True,
        verbose_name="Sector"
    )
    zona = models.CharField(
        max_length=10,
        choices=ZONA_CHOICES,
        null=True,
        blank=True,
        verbose_name="Zona"
    )
    
    # Información de contacto
    direccion = models.TextField(null=True, blank=True, verbose_name="Dirección")
    telefono = models.CharField(
        max_length=50, 
        null=True, 
        blank=True, 
        verbose_name="Teléfono"
    )
    email = models.EmailField(null=True, blank=True, verbose_name="Email")
    
    # Coordenadas para el mapa
    latitud = models.DecimalField(
        max_digits=10, 
        decimal_places=8, 
        null=True, 
        blank=True,
        verbose_name="Latitud"
    )
    longitud = models.DecimalField(
        max_digits=11, 
        decimal_places=8, 
        null=True, 
        blank=True,
        verbose_name="Longitud"
    )
    
    # Control de cambios y auditoría
    updated_hash = models.CharField(
        max_length=64, 
        db_index=True,
        verbose_name="Hash de actualización",
        help_text="Hash para detectar cambios en los datos"
    )
    source_system = models.CharField(
        max_length=50,
        default='mysql',
        verbose_name="Sistema fuente",
        help_text="Sistema de donde proviene el registro (mysql, excel_a, excel_b)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Institución Educativa"
        verbose_name_plural = "Instituciones Educativas"
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['codigo_dane']),
            models.Index(fields=['estado']),
            models.Index(fields=['municipio', 'estado']),
            models.Index(fields=['updated_hash']),
            models.Index(fields=['source_system']),
            models.Index(fields=['latitud', 'longitud']),
        ]
    
    def __str__(self):
        return f"{self.nombre} ({self.codigo_dane})"
    
    @property
    def municipio_nombre(self):
        """Nombre del municipio para facilitar consultas."""
        return self.municipio.nombre if self.municipio else None


class ChangeLog(models.Model):
    """Log de cambios para auditoría detallada."""
    
    ACTION_CHOICES = [
        ('insert', 'Inserción'),
        ('update', 'Actualización'),
        ('delete', 'Eliminación'),
    ]
    
    etl_run = models.ForeignKey(
        ETLRun,
        on_delete=models.CASCADE,
        related_name='change_logs',
        verbose_name="Ejecución ETL"
    )
    table_name = models.CharField(max_length=50, verbose_name="Tabla")
    record_id = models.CharField(max_length=50, verbose_name="ID del registro")
    action = models.CharField(
        max_length=10, 
        choices=ACTION_CHOICES,
        verbose_name="Acción"
    )
    old_values = models.JSONField(
        null=True, 
        blank=True, 
        verbose_name="Valores anteriores"
    )
    new_values = models.JSONField(
        null=True, 
        blank=True, 
        verbose_name="Valores nuevos"
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Log de Cambio"
        verbose_name_plural = "Logs de Cambios"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['table_name', 'record_id']),
            models.Index(fields=['etl_run', 'action']),
        ]
    
    def __str__(self):
        return f"{self.action} en {self.table_name} - {self.record_id}"


# Modelo opcional para staging (copia fiel de datos crudos)
class StgInstitucionMySQL(models.Model):
    """Staging table - copia fiel de datos desde MySQL para auditoría."""
    
    etl_run = models.ForeignKey(ETLRun, on_delete=models.CASCADE)
    raw_data = models.JSONField(verbose_name="Datos crudos")
    processed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Staging MySQL"
        verbose_name_plural = "Staging MySQL"
        managed = True  # Django manage this table
