"""
Configuración del Admin de Django para el módulo ETL.
Registra los modelos para administración desde la interfaz web.
"""
from django.contrib import admin
from .models import (
    ETLRun, DimMunicipio, DimSede, FactInstitucion, 
    ChangeLog, StgInstitucionMySQL, Institucion, Sede,
    FactMatricula, FactMatriculaEtnica, PaeAsignacion, Visita
)


@admin.register(ETLRun)
class ETLRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'started_at', 'finished_at', 'status', 'duration_formatted')
    list_filter = ('status', 'started_at')
    search_fields = ('id', 'status')
    readonly_fields = ('started_at', 'duration')
    ordering = ('-started_at',)
    
    def duration_formatted(self, obj):
        """Duración formateada para el admin."""
        if obj.duration is None:
            return "N/A"
        
        seconds = int(obj.duration)
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds = seconds % 60
            return f"{hours}h {minutes}m {seconds}s"
    
    duration_formatted.short_description = 'Duración'


@admin.register(DimMunicipio)
class DimMunicipioAdmin(admin.ModelAdmin):
    list_display = ('codigo_municipio', 'nombre', 'codigo_departamento')
    list_filter = ('codigo_departamento',)
    search_fields = ('codigo_municipio', 'nombre')
    ordering = ('nombre',)


@admin.register(DimSede)
class DimSedeAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'institucion_codigo')
    search_fields = ('codigo', 'nombre', 'institucion_codigo')
    ordering = ('nombre',)


# @admin.register(FactInstitucion)  # Comentado temporalmente - modelo legacy
class FactInstitucionAdmin(admin.ModelAdmin):
    list_display = (
        'codigo_dane', 'nombre', 'municipio', 'estado', 
        'sector', 'zona', 'source_system', 'updated_at'
    )
    list_filter = ('estado', 'sector', 'zona', 'source_system', 'municipio__departamento_nombre')
    search_fields = ('codigo_dane', 'nombre', 'municipio__nombre')
    readonly_fields = ('updated_hash', 'created_at', 'updated_at')
    ordering = ('nombre',)
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo_dane', 'nombre', 'municipio')
        }),
        ('Clasificación', {
            'fields': ('estado', 'sector', 'zona')
        }),
        ('Contacto', {
            'fields': ('direccion', 'telefono', 'email'),
            'classes': ('collapse',)
        }),
        ('Ubicación', {
            'fields': ('latitud', 'longitud'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('source_system', 'updated_hash', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(ChangeLog)
class ChangeLogAdmin(admin.ModelAdmin):
    list_display = ('etl_run', 'table_name', 'record_id', 'action', 'timestamp')
    list_filter = ('action', 'table_name', 'timestamp')
    search_fields = ('record_id', 'table_name')
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)
    
    def has_add_permission(self, request):
        """No permitir agregar logs manualmente."""
        return False


@admin.register(StgInstitucionMySQL)
class StgInstitucionMySQLAdmin(admin.ModelAdmin):
    list_display = ('etl_run', 'processed_at')
    list_filter = ('processed_at', 'etl_run__status')
    readonly_fields = ('processed_at',)
    ordering = ('-processed_at',)
    
    def has_add_permission(self, request):
        """Solo lectura."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Solo lectura."""
        return False


# Nuevos modelos - Admin básico
@admin.register(Institucion)
class InstitucionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'dane_ie_id', 'sed_ie_id', 'uesvalle_ie_id', 'estado', 'codigo_municipio')
    list_filter = ('estado', 'codigo_municipio')
    search_fields = ('nombre', 'dane_ie_id', 'sed_ie_id', 'uesvalle_ie_id')
    ordering = ('nombre',)


@admin.register(Sede)
class SedeAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'institucion_id', 'codigo_municipio', 'estado')
    list_filter = ('estado', 'codigo_municipio')
    search_fields = ('nombre', 'dane_sede_id', 'sed_sede_id', 'uesvalle_sede_id')
    ordering = ('nombre',)


@admin.register(FactMatricula)
class FactMatriculaAdmin(admin.ModelAdmin):
    list_display = ('sede_id', 'corte_fecha', 'nivel', 'grado', 'genero', 'total_alumnos')
    list_filter = ('corte_fecha', 'nivel', 'grado', 'genero')
    search_fields = ('sede_id__nombre',)
    ordering = ('-corte_fecha',)


# Configuración adicional del admin
admin.site.site_header = "ETL UESVALLE - Administración"
admin.site.site_title = "ETL UESVALLE"
admin.site.index_title = "Sistema de Normalización de Datos Educativos"