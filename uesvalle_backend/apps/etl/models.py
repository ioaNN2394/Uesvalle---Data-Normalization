"""
Modelos para almacenar los datos procesados del ETL.
Sigue el patrón dim_* (dimensiones) y fact_* (hechos) para el data warehouse.
"""
import uuid
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
        db_table = 'etl_run'  # Sin esquema, usar search_path
    
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
    
    codigo_municipio = models.CharField(
        max_length=12, 
        primary_key=True,
        verbose_name="Código DANE",
        help_text="Código único DANE del municipio"
    )
    nombre = models.CharField(max_length=120, verbose_name="Nombre del municipio")
    codigo_departamento = models.CharField(
        max_length=2, 
        verbose_name="Código del departamento"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Municipio"
        verbose_name_plural = "Municipios" 
        db_table = 'dim_municipio'  # Sin esquema, usar search_path
        ordering = ['nombre']
        managed = True  # Django crea/maneja las tablas
    
    def __str__(self):
        return f"{self.nombre} ({self.codigo_municipio})"


class Institucion(models.Model):
    """Institución educativa - entidad principal."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    nombre = models.CharField(max_length=255, verbose_name="Nombre de la institución")
    
    # IDs oficiales (pueden ser nulos)
    dane_ie_id = models.CharField(max_length=50, null=True, blank=True, unique=True)
    sed_ie_id = models.CharField(max_length=50, null=True, blank=True, unique=True) 
    uesvalle_ie_id = models.CharField(max_length=50, null=True, blank=True, unique=True)
    
    codigo_municipio = models.ForeignKey(
        DimMunicipio, 
        to_field='codigo_municipio',    # Apuntar a PK CharField según documentación
        db_column='codigo_municipio',   # Nombre exacto sin _id
        on_delete=models.PROTECT,       # Equivalente a ON DELETE RESTRICT
        null=True,
        blank=True
    )
    direccion = models.CharField(max_length=255, null=True, blank=True)
    telefono = models.CharField(max_length=50, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    estado = models.CharField(max_length=50, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Institución"
        verbose_name_plural = "Instituciones"
        db_table = 'institucion'  # Sin esquema, usar search_path
        ordering = ['nombre']
        managed = True  # Django crea/maneja las tablas
    
    def __str__(self):
        return self.nombre


class Sede(models.Model):
    """Sede educativa - campus/planta física."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    institucion_id = models.ForeignKey(Institucion, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=255, verbose_name="Nombre de la sede")
    
    # IDs oficiales de la sede
    dane_sede_id = models.CharField(max_length=50, null=True, blank=True)
    sed_sede_id = models.CharField(max_length=50, null=True, blank=True)
    uesvalle_sede_id = models.CharField(max_length=50, null=True, blank=True)
    
    codigo_municipio = models.ForeignKey(
        DimMunicipio,
        to_field='codigo_municipio',    # Apuntar a PK CharField
        db_column='codigo_municipio',   # Nombre exacto sin _id  
        on_delete=models.PROTECT,       # Equivalente a ON DELETE RESTRICT
        null=True,
        blank=True
    )
    direccion = models.CharField(max_length=255, null=True, blank=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lon = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    estado = models.CharField(max_length=50, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Sede"
        verbose_name_plural = "Sedes"
        db_table = 'sede'  # Sin esquema, usar search_path
        ordering = ['nombre']
        managed = True  # Django crea/maneja las tablas
        indexes = [
            models.Index(fields=['institucion_id']),
            models.Index(fields=['codigo_municipio']),
        ]
    
    def __str__(self):
        return f"{self.nombre} - {self.institucion_id.nombre}"


class FactMatricula(models.Model):
    """Hechos de matrícula por cortes de fecha."""
    
    sede_id = models.ForeignKey(Sede, on_delete=models.CASCADE)
    corte_fecha = models.DateField()
    nivel = models.CharField(max_length=50, default='')
    grado = models.CharField(max_length=50, default='')
    jornada = models.CharField(max_length=50, default='')
    genero = models.CharField(max_length=10, default='')
    total_alumnos = models.PositiveIntegerField()
    
    fuente = models.CharField(max_length=255, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'uesvalle"."fact_matricula'
        unique_together = ['sede_id', 'corte_fecha', 'nivel', 'grado', 'jornada', 'genero']
        verbose_name = "Matrícula"
        verbose_name_plural = "Matrículas"
        indexes = [
            models.Index(fields=['corte_fecha']),
            models.Index(fields=['sede_id', 'corte_fecha']),
        ]
    
    def __str__(self):
        return f"Matrícula {self.sede_id} - {self.corte_fecha}"


class FactMatriculaEtnica(models.Model):
    """Hechos de matrícula étnica por grupo poblacional."""
    
    sede_id = models.ForeignKey(Sede, on_delete=models.CASCADE)
    corte_fecha = models.DateField()
    grupo_etnico = models.CharField(max_length=100, default='')
    total_alumnos = models.PositiveIntegerField()
    
    fuente = models.CharField(max_length=255, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'uesvalle"."fact_matricula_etnica'
        unique_together = ['sede_id', 'corte_fecha', 'grupo_etnico']
        verbose_name = "Matrícula Étnica"
        verbose_name_plural = "Matrículas Étnicas"
    
    def __str__(self):
        return f"Matrícula Étnica {self.sede_id} - {self.grupo_etnico}"


class PaeAsignacion(models.Model):
    """Hechos de asignación del PAE."""
    
    sede_id = models.ForeignKey(Sede, on_delete=models.CASCADE)
    anio = models.PositiveIntegerField()
    periodo = models.CharField(max_length=50, default='')
    modalidad = models.CharField(max_length=100)
    beneficiarios = models.PositiveIntegerField()
    
    fuente = models.CharField(max_length=255, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'uesvalle"."pae_asignacion'
        unique_together = ['sede_id', 'anio', 'periodo', 'modalidad']
        verbose_name = "Asignación PAE"
        verbose_name_plural = "Asignaciones PAE"
        indexes = [
            models.Index(fields=['sede_id', 'anio']),
        ]
    
    def __str__(self):
        return f"PAE {self.sede_id} - {self.anio}"


class Visita(models.Model):
    """Hechos de visitas a instituciones/sedes."""
    
    id = models.BigAutoField(primary_key=True)
    sede_id = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True)
    institucion_id = models.ForeignKey(Institucion, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateField()
    programa = models.CharField(max_length=255, null=True, blank=True)
    resultado = models.TextField(null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'uesvalle"."visita'
        verbose_name = "Visita"
        verbose_name_plural = "Visitas"
    
    def __str__(self):
        return f"Visita {self.fecha} - {self.programa or 'Sin programa'}"


class DimSede(models.Model):
    """LEGACY: Dimensión de sedes educativas - usar modelo Sede."""
    
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


class ETLError(models.Model):
    """Registro de errores específicos durante el ETL."""
    
    ERROR_TYPES = [
        ('extraction', 'Error de Extracción'),
        ('transformation', 'Error de Transformación'), 
        ('loading', 'Error de Carga'),
        ('validation', 'Error de Validación'),
        ('connection', 'Error de Conexión'),
    ]
    
    etl_run = models.ForeignKey(ETLRun, on_delete=models.CASCADE, related_name='errors')
    error_type = models.CharField(max_length=20, choices=ERROR_TYPES)
    source_table = models.CharField(max_length=100, null=True, blank=True)
    record_id = models.CharField(max_length=100, null=True, blank=True)
    error_message = models.TextField()
    error_context = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Error ETL"
        verbose_name_plural = "Errores ETL"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['etl_run', 'error_type']),
            models.Index(fields=['source_table']),
        ]
    
    def __str__(self):
        return f"{self.get_error_type_display()} - {self.error_message[:50]}..."


class DataQualityCheck(models.Model):
    """Registro de validaciones de calidad de datos."""
    
    CHECK_TYPES = [
        ('completeness', 'Completitud'),
        ('uniqueness', 'Unicidad'),
        ('consistency', 'Consistencia'),
        ('validity', 'Validez'),
        ('accuracy', 'Precisión'),
    ]
    
    STATUS_CHOICES = [
        ('passed', 'Aprobado'),
        ('failed', 'Falló'),
        ('warning', 'Advertencia'),
    ]
    
    etl_run = models.ForeignKey(ETLRun, on_delete=models.CASCADE, related_name='quality_checks')
    check_type = models.CharField(max_length=20, choices=CHECK_TYPES)
    table_name = models.CharField(max_length=100)
    check_name = models.CharField(max_length=100)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    records_checked = models.IntegerField(default=0)
    records_failed = models.IntegerField(default=0)
    details = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Control de Calidad"
        verbose_name_plural = "Controles de Calidad"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['etl_run', 'status']),
            models.Index(fields=['table_name', 'check_type']),
        ]
    
    def __str__(self):
        return f"{self.check_name} - {self.get_status_display()}"
    
    @property
    def success_rate(self):
        """Calcula el porcentaje de éxito."""
        if self.records_checked == 0:
            return 0
        return ((self.records_checked - self.records_failed) / self.records_checked) * 100


class ETLMetrics(models.Model):
    """Métricas de rendimiento del ETL."""
    
    etl_run = models.OneToOneField(ETLRun, on_delete=models.CASCADE, related_name='metrics')
    
    # Métricas de tiempo
    extraction_duration = models.DurationField(null=True, blank=True)
    transformation_duration = models.DurationField(null=True, blank=True)
    loading_duration = models.DurationField(null=True, blank=True)
    
    # Métricas de volumen
    records_extracted_mysql = models.IntegerField(default=0)
    records_extracted_excel = models.IntegerField(default=0)
    records_transformed = models.IntegerField(default=0)
    records_loaded = models.IntegerField(default=0)
    records_rejected = models.IntegerField(default=0)
    
    # Métricas de calidad
    data_quality_score = models.FloatField(null=True, blank=True)
    
    # Uso de recursos
    memory_peak_mb = models.FloatField(null=True, blank=True)
    cpu_time_seconds = models.FloatField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Métricas ETL"
        verbose_name_plural = "Métricas ETL"
    
    def __str__(self):
        return f"Métricas ETL Run {self.etl_run.id}"
