"""
Serializadores para la API REST del módulo ETL.
Maneja la serialización de modelos y validación de datos.
"""
from rest_framework import serializers
from .models import (
    ETLRun, DimMunicipio, DimEtnia, DimGrado, DimJornada, DimNivel, DimModalidadPAE,
    ETLFile, Institucion, Sede, FactMatricula, FactMatriculaEtnica, PaeAsignacion, Visita, Notification
)


class ETLFileSerializer(serializers.ModelSerializer):
    """Serializer para el modelo ETLFile."""
    
    success_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = ETLFile
        fields = [
            'id', 'filename', 'file_type', 'file_size', 'status',
            'rows_processed', 'rows_failed', 'error_message',
            'uploaded_at', 'processed_at', 'success_rate'
        ]
        read_only_fields = ['id', 'uploaded_at', 'processed_at']
    
    def get_success_rate(self, obj):
        return obj.success_rate


class ETLRunSerializer(serializers.ModelSerializer):
    """Serializer para el modelo ETLRun."""
    
    class Meta:
        model = ETLRun
        fields = ['id', 'started_at', 'finished_at', 'status', 'meta']
        read_only_fields = ['id', 'started_at']


class DimMunicipioSerializer(serializers.ModelSerializer):
    """Serializer para el modelo DimMunicipio."""
    
    class Meta:
        model = DimMunicipio
        fields = [
            'codigo_municipio', 'nombre', 'codigo_departamento',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class DimEtniaSerializer(serializers.ModelSerializer):
    """Serializer para el modelo DimEtnia."""
    
    class Meta:
        model = DimEtnia
        fields = ['id', 'nombre']


class DimGradoSerializer(serializers.ModelSerializer):
    """Serializer para el modelo DimGrado."""
    
    class Meta:
        model = DimGrado
        fields = ['id', 'nombre']


class DimJornadaSerializer(serializers.ModelSerializer):
    """Serializer para el modelo DimJornada."""
    
    class Meta:
        model = DimJornada
        fields = ['id', 'nombre']


class DimNivelSerializer(serializers.ModelSerializer):
    """Serializer para el modelo DimNivel."""
    
    class Meta:
        model = DimNivel
        fields = ['id', 'nombre']


class DimModalidadPAESerializer(serializers.ModelSerializer):
    """Serializer para el modelo DimModalidadPAE."""
    
    class Meta:
        model = DimModalidadPAE
        fields = ['id', 'nombre']


class InstitucionSerializer(serializers.ModelSerializer):
    """Serializer para el modelo Institucion."""
    
    class Meta:
        model = Institucion
        fields = [
            'id', 'nombre', 'dane_ie_id', 'sed_ie_id', 'uesvalle_ie_id',
            'codigo_municipio', 'direccion', 'telefono', 'email', 
            'estado', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SedeSerializer(serializers.ModelSerializer):
    """Serializer para el modelo Sede."""
    
    class Meta:
        model = Sede
        fields = [
            'id', 'institucion_id', 'nombre', 'dane_sede_id', 'sed_sede_id',
            'uesvalle_sede_id', 'codigo_municipio', 'direccion',
            'lat', 'lon', 'geom', 'estado', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FactMatriculaSerializer(serializers.ModelSerializer):
    """Serializer para el modelo FactMatricula."""
    
    class Meta:
        model = FactMatricula
        fields = [
            'sede_id', 'corte_fecha', 'nivel', 'grado', 'jornada',
            'genero', 'total_alumnos', 'fuente', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class FactMatriculaEtnicaSerializer(serializers.ModelSerializer):
    """Serializer para el modelo FactMatriculaEtnica."""
    
    class Meta:
        model = FactMatriculaEtnica
        fields = [
            'sede_id', 'corte_fecha', 'grupo_etnico', 'total_alumnos',
            'fuente', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class PaeAsignacionSerializer(serializers.ModelSerializer):
    """Serializer para el modelo PaeAsignacion."""
    
    class Meta:
        model = PaeAsignacion
        fields = [
            'sede_id', 'anio', 'periodo', 'modalidad', 'beneficiarios',
            'fuente', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class VisitaSerializer(serializers.ModelSerializer):
    """Serializer para el modelo Visita."""
    
    class Meta:
        model = Visita
        fields = [
            'id', 'sede_id', 'institucion_id', 'fechavisita', 'programa',
            'resultado', 'observacion', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ETLFileSerializer(serializers.ModelSerializer):
    """Serializer para archivos ETL."""
    
    success_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = ETLFile
        fields = [
            'id', 'filename', 'file_type', 'file_path',
            'file_size', 'status', 'rows_processed', 'rows_failed',
            'error_message', 'uploaded_at', 'processed_at', 'success_rate'
        ]
        read_only_fields = ['id', 'uploaded_at', 'processed_at']


class MapMarkerSerializer(serializers.Serializer):
    """Serializa marcadores para el mapa (sedes con coordenadas)."""
    sede_id = serializers.UUIDField()
    sede = serializers.CharField()
    institucion = serializers.CharField()
    institucion_id = serializers.UUIDField()
    dane_ie_id = serializers.CharField()
    email = serializers.EmailField(allow_null=True)
    telefono = serializers.CharField(allow_null=True)
    direccion = serializers.CharField(allow_null=True)
    estado = serializers.CharField()
    lat = serializers.DecimalField(max_digits=10, decimal_places=8)
    lon = serializers.DecimalField(max_digits=10, decimal_places=8)
    codigo_municipio = serializers.CharField()


class NotificationSerializer(serializers.ModelSerializer):
    institucion_nombre = serializers.CharField(source='institucion.nombre', read_only=True)
    institucion_dane = serializers.CharField(source='institucion.dane_ie_id', read_only=True)
    institucion_ues = serializers.CharField(source='institucion.uesvalle_ie_id', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 
            'institucion_nombre', 
            'institucion_dane', 
            'institucion_ues', 
            'old_concept', 
            'new_concept', 
            'created_at', 
            'is_read'
        ]
