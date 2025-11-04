"""
Modelos para almacenar los datos procesados del ETL.
Sigue el patrón dim_* (dimensiones) y fact_* (hechos) para el data warehouse.

Estructura sincronizada EXACTAMENTE con Supabase PostgreSQL (2025-11-04).
"""
import uuid
from django.db import models


# =====================================================================
# DIMENSIONES (Catálogos/Lookups)
# =====================================================================

class DimEtnia(models.Model):
    """Dimensión de etnias/grupos étnicos."""
    
    id = models.AutoField(primary_key=True)
    nombre = models.TextField(verbose_name="Nombre de la etnia")
    
    class Meta:
        verbose_name = "Etnia"
        verbose_name_plural = "Etnias"
        db_table = 'uesvalle"."dim_etnia'
        managed = True
    
    def __str__(self):
        return self.nombre


class DimGrado(models.Model):
    """Dimensión de grados educativos."""
    
    id = models.AutoField(primary_key=True)
    nombre = models.TextField(verbose_name="Nombre del grado")
    
    class Meta:
        verbose_name = "Grado"
        verbose_name_plural = "Grados"
        db_table = 'uesvalle"."dim_grado'
        managed = True
    
    def __str__(self):
        return self.nombre


class DimJornada(models.Model):
    """Dimensión de jornadas escolares."""
    
    id = models.AutoField(primary_key=True)
    nombre = models.TextField(verbose_name="Nombre de la jornada")
    
    class Meta:
        verbose_name = "Jornada"
        verbose_name_plural = "Jornadas"
        db_table = 'uesvalle"."dim_jornada'
        managed = True
    
    def __str__(self):
        return self.nombre


class DimNivel(models.Model):
    """Dimensión de niveles educativos."""
    
    id = models.AutoField(primary_key=True)
    nombre = models.TextField(verbose_name="Nombre del nivel")
    
    class Meta:
        verbose_name = "Nivel Educativo"
        verbose_name_plural = "Niveles Educativos"
        db_table = 'uesvalle"."dim_nivel'
        managed = True
    
    def __str__(self):
        return self.nombre


class DimModalidadPAE(models.Model):
    """Dimensión de modalidades del Programa de Alimentación Escolar."""
    
    id = models.AutoField(primary_key=True)
    nombre = models.TextField(verbose_name="Nombre de la modalidad")
    
    class Meta:
        verbose_name = "Modalidad PAE"
        verbose_name_plural = "Modalidades PAE"
        db_table = 'uesvalle"."dim_modalidad_pae'
        managed = True
    
    def __str__(self):
        return self.nombre


class DimMunicipio(models.Model):
    """Dimensión de municipios - catálogo normalizado."""
    
    codigo_municipio = models.TextField(
        primary_key=True,
        verbose_name="Código DANE",
        help_text="Código único DANE del municipio"
    )
    nombre = models.TextField(verbose_name="Nombre del municipio")
    codigo_departamento = models.TextField(
        verbose_name="Código del departamento"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Municipio"
        verbose_name_plural = "Municipios" 
        db_table = 'uesvalle"."dim_municipio'
        managed = True
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.nombre} ({self.codigo_municipio})"


# =====================================================================
# ENTIDADES PRINCIPALES
# =====================================================================

class ETLRun(models.Model):
    """Registro de ejecuciones del ETL para auditoría y monitoreo."""
    
    STATUS_CHOICES = [
        ('running', 'En ejecución'),
        ('success', 'Exitoso'),
        ('failed', 'Fallido'),
        ('cancelled', 'Cancelado'),
    ]
    
    id = models.BigAutoField(primary_key=True)
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
        db_table = 'uesvalle"."etl_run'
        managed = True
    
    def __str__(self):
        return f"ETL Run {self.id} - {self.status} ({self.started_at})"


class Institucion(models.Model):
    """Institución educativa - entidad principal."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    nombre = models.TextField(verbose_name="Nombre de la institución")
    
    # IDs oficiales (pueden ser nulos)
    dane_ie_id = models.TextField(null=True, blank=True, unique=True)
    sed_ie_id = models.TextField(null=True, blank=True, unique=True) 
    uesvalle_ie_id = models.TextField(null=True, blank=True, unique=True)
    
    # Ubicación
    codigo_municipio = models.TextField(null=True, blank=True)
    direccion = models.TextField(null=True, blank=True)
    telefono = models.TextField(null=True, blank=True)
    email = models.TextField(null=True, blank=True)
    estado = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Institución"
        verbose_name_plural = "Instituciones"
        db_table = 'uesvalle"."institucion'
        managed = True
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre


class Sede(models.Model):
    """Sede educativa - campus/planta física."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    institucion_id = models.UUIDField(null=True, blank=True, verbose_name="Institución")
    nombre = models.TextField(verbose_name="Nombre de la sede")
    
    # IDs oficiales de la sede
    dane_sede_id = models.TextField(null=True, blank=True)
    sed_sede_id = models.TextField(null=True, blank=True)
    uesvalle_sede_id = models.TextField(null=True, blank=True)
    
    # Ubicación
    codigo_municipio = models.TextField(null=True, blank=True)
    direccion = models.TextField(null=True, blank=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lon = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Información adicional
    geom = models.TextField(null=True, blank=True)  # PostGIS geometry como texto
    estado = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Sede"
        verbose_name_plural = "Sedes"
        db_table = 'uesvalle"."sede'
        managed = True
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['institucion_id']),
            models.Index(fields=['codigo_municipio']),
        ]
    
    def __str__(self):
        return f"{self.nombre}"


# =====================================================================
# HECHOS (Facts Tables)
# =====================================================================

class FactMatricula(models.Model):
    """Hechos de matrícula por cortes de fecha."""
    
    sede_id = models.UUIDField(primary_key=False, verbose_name="Sede")
    corte_fecha = models.DateField(primary_key=False)
    nivel = models.TextField(default='')
    grado = models.TextField(default='')
    jornada = models.TextField(default='')
    genero = models.TextField(default='')
    total_alumnos = models.PositiveIntegerField()
    
    fuente = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'uesvalle"."fact_matricula'
        unique_together = ['sede_id', 'corte_fecha', 'nivel', 'grado', 'jornada', 'genero']
        verbose_name = "Matrícula"
        verbose_name_plural = "Matrículas"
        managed = True
        indexes = [
            models.Index(fields=['corte_fecha']),
            models.Index(fields=['sede_id', 'corte_fecha']),
        ]
    
    def __str__(self):
        return f"Matrícula {self.sede_id} - {self.corte_fecha}"


class FactMatriculaEtnica(models.Model):
    """Hechos de matrícula étnica por grupo poblacional."""
    
    sede_id = models.UUIDField(primary_key=False, verbose_name="Sede")
    corte_fecha = models.DateField(primary_key=False)
    grupo_etnico = models.TextField(default='')
    total_alumnos = models.PositiveIntegerField()
    
    fuente = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'uesvalle"."fact_matricula_etnica'
        unique_together = ['sede_id', 'corte_fecha', 'grupo_etnico']
        verbose_name = "Matrícula Étnica"
        verbose_name_plural = "Matrículas Étnicas"
        managed = True
        indexes = [
            models.Index(fields=['corte_fecha']),
            models.Index(fields=['sede_id']),
        ]
    
    def __str__(self):
        return f"Matrícula Étnica {self.sede_id} - {self.grupo_etnico}"


class PaeAsignacion(models.Model):
    """Hechos de asignación del PAE (Programa de Alimentación Escolar)."""
    
    sede_id = models.UUIDField(primary_key=False, verbose_name="Sede")
    anio = models.PositiveIntegerField(primary_key=False)
    periodo = models.TextField(default='')
    modalidad = models.TextField()
    beneficiarios = models.PositiveIntegerField()
    
    fuente = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'uesvalle"."pae_asignacion'
        unique_together = ['sede_id', 'anio', 'periodo', 'modalidad']
        verbose_name = "Asignación PAE"
        verbose_name_plural = "Asignaciones PAE"
        managed = True
        indexes = [
            models.Index(fields=['sede_id', 'anio']),
            models.Index(fields=['anio']),
        ]
    
    def __str__(self):
        return f"PAE {self.sede_id} - {self.anio}"


class Visita(models.Model):
    """Hechos de visitas a instituciones/sedes."""
    
    id = models.BigAutoField(primary_key=True)
    sede_id = models.UUIDField(null=True, blank=True)
    institucion_id = models.UUIDField(null=True, blank=True)
    fecha = models.DateField()
    programa = models.TextField(null=True, blank=True)
    resultado = models.TextField(null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'uesvalle"."visita'
        verbose_name = "Visita"
        verbose_name_plural = "Visitas"
        managed = True
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['sede_id']),
            models.Index(fields=['institucion_id']),
            models.Index(fields=['fecha']),
        ]
    
    def __str__(self):
        return f"Visita {self.fecha} - {self.programa or 'Sin programa'}"


class ETLFile(models.Model):
    """Archivo cargado para procesamiento ETL."""
    
    FILE_TYPES = [
        ('excel', 'Excel (.xlsx, .xls)'),
        ('csv', 'CSV'),
        ('json', 'JSON'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('processing', 'Procesando'),
        ('success', 'Exitoso'),
        ('failed', 'Fallido'),
    ]
    
    filename = models.CharField(max_length=255, verbose_name="Nombre del archivo")
    file_type = models.CharField(
        max_length=20,
        choices=FILE_TYPES,
        verbose_name="Tipo de archivo"
    )
    file_path = models.CharField(
        max_length=500,
        verbose_name="Ruta del archivo"
    )
    file_size = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="Tamaño en bytes"
    )
    
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Estado"
    )
    
    rows_processed = models.IntegerField(default=0, verbose_name="Filas procesadas")
    rows_failed = models.IntegerField(default=0, verbose_name="Filas fallidas")
    
    error_message = models.TextField(
        null=True,
        blank=True,
        verbose_name="Mensaje de error"
    )
    
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Cargado en"
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Procesado en"
    )
    
    class Meta:
        verbose_name = "Archivo ETL"
        verbose_name_plural = "Archivos ETL"
        db_table = 'public"."etl_file'
        managed = True
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.filename} ({self.file_type})"
    
    @property
    def success_rate(self):
        """Tasa de éxito del procesamiento."""
        total = self.rows_processed + self.rows_failed
        if total == 0:
            return 0
        return (self.rows_processed / total) * 100
