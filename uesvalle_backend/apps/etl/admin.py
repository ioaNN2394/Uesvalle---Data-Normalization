"""
Configuración del Admin de Django para el módulo ETL.
Registra los modelos para administración desde la interfaz web.
"""
from django.contrib import admin
from .models import (
    ETLRun, DimMunicipio, DimEtnia, DimGrado, DimJornada, DimNivel, DimModalidadPAE,
    Institucion, Sede,
    FactMatricula, FactMatriculaEtnica, PaeAsignacion, Visita, ETLFile
)


@admin.register(ETLRun)
class ETLRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'started_at', 'finished_at', 'status')
    list_filter = ('status', 'started_at')
    search_fields = ('id', 'status')
    readonly_fields = ('started_at',)
    ordering = ('-started_at',)


@admin.register(DimMunicipio)
class DimMunicipioAdmin(admin.ModelAdmin):
    list_display = ('codigo_municipio', 'nombre', 'codigo_departamento')
    list_filter = ('codigo_departamento',)
    search_fields = ('codigo_municipio', 'nombre')
    ordering = ('nombre',)


@admin.register(DimEtnia)
class DimEtniaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)
    ordering = ('nombre',)


@admin.register(DimGrado)
class DimGradoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)
    ordering = ('nombre',)


@admin.register(DimJornada)
class DimJornadaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)
    ordering = ('nombre',)


@admin.register(DimNivel)
class DimNivelAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)
    ordering = ('nombre',)


@admin.register(DimModalidadPAE)
class DimModalidadPAEAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)
    ordering = ('nombre',)


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
    search_fields = ('sede_id',)
    ordering = ('-corte_fecha',)


@admin.register(FactMatriculaEtnica)
class FactMatriculaEtnicaAdmin(admin.ModelAdmin):
    list_display = ('sede_id', 'corte_fecha', 'grupo_etnico', 'total_alumnos')
    list_filter = ('corte_fecha', 'grupo_etnico')
    search_fields = ('sede_id', 'grupo_etnico')
    ordering = ('-corte_fecha',)


@admin.register(PaeAsignacion)
class PaeAsignacionAdmin(admin.ModelAdmin):
    list_display = ('sede_id', 'anio', 'periodo', 'modalidad', 'beneficiarios')
    list_filter = ('anio', 'periodo', 'modalidad')
    search_fields = ('sede_id', 'modalidad')
    ordering = ('-anio',)


@admin.register(Visita)
class VisitaAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha', 'sede_id', 'institucion_id', 'programa')
    list_filter = ('fecha', 'programa')
    search_fields = ('sede_id', 'institucion_id', 'programa')
    ordering = ('-fecha',)


@admin.register(ETLFile)
class ETLFileAdmin(admin.ModelAdmin):
    list_display = ('filename', 'file_type', 'status', 'rows_processed', 'rows_failed', 'uploaded_at')
    list_filter = ('file_type', 'status', 'uploaded_at')
    search_fields = ('filename',)
    readonly_fields = ('uploaded_at', 'processed_at')
    ordering = ('-uploaded_at',)


# Configuración adicional del admin
admin.site.site_header = "ETL UESVALLE - Administración"
admin.site.site_title = "ETL UESVALLE"
admin.site.index_title = "Sistema de Normalización de Datos Educativos"