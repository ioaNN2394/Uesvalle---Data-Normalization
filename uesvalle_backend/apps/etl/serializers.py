"""
Serializadores para la API REST del módulo ETL.
Maneja la serialización de modelos y validación de datos.
"""
from rest_framework import serializers
from django.utils import timezone
from .models import (
    ETLRun, DimMunicipio, DimSede, FactInstitucion, 
    ChangeLog, StgInstitucionMySQL, DataQualityCheck, ETLError, ETLMetrics,
    Institucion, Sede, FactMatricula, FactMatriculaEtnica, PaeAsignacion, Visita
)


class ETLRunSerializer(serializers.ModelSerializer):
    """Serializer para el modelo ETLRun."""
    
    duration = serializers.ReadOnlyField()
    duration_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = ETLRun
        fields = [
            'id', 'started_at', 'finished_at', 'status', 'meta',
            'duration', 'duration_formatted'
        ]
        read_only_fields = ['id', 'started_at', 'duration', 'duration_formatted']
    
    def get_duration_formatted(self, obj):
        """Retorna duración formateada en formato legible."""
        if obj.duration is None:
            return None
        
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


class DimMunicipioSerializer(serializers.ModelSerializer):
    """Serializer para el modelo DimMunicipio."""
    
    class Meta:
        model = DimMunicipio
        fields = [
            'codigo_municipio', 'nombre', 'codigo_departamento', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['codigo_municipio', 'created_at', 'updated_at']


class DimSedeSerializer(serializers.ModelSerializer):
    """Serializer para el modelo DimSede."""
    
    class Meta:
        model = DimSede
        fields = [
            'id', 'codigo', 'nombre', 'institucion_codigo',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FactInstitucionSerializer(serializers.ModelSerializer):
    """Serializer para el modelo FactInstitucion."""
    
    municipio_nombre = serializers.ReadOnlyField()
    municipio_info = DimMunicipioSerializer(source='municipio', read_only=True)
    
    class Meta:
        model = FactInstitucion
        fields = [
            'id', 'codigo_dane', 'nombre', 'municipio', 'municipio_nombre', 
            'municipio_info', 'estado', 'sector', 'zona', 'direccion', 
            'telefono', 'email', 'latitud', 'longitud', 'updated_hash', 
            'source_system', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'updated_hash', 'municipio_nombre', 'municipio_info',
            'created_at', 'updated_at'
        ]


class FactInstitucionListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listas de instituciones."""
    
    municipio_nombre = serializers.ReadOnlyField()
    
    class Meta:
        model = FactInstitucion
        fields = [
            'id', 'codigo_dane', 'nombre', 'municipio_nombre', 
            'estado', 'sector', 'zona', 'latitud', 'longitud'
        ]


class InstitucionSerializer(serializers.ModelSerializer):
    """Serializer para el modelo Institucion (tabla uesvalle.institucion)."""
    municipio_nombre = serializers.CharField(source='codigo_municipio.nombre', read_only=True)
    departamento = serializers.CharField(source='codigo_municipio.codigo_departamento', read_only=True)

    class Meta:
        model = Institucion
        fields = [
            'id', 'nombre', 'dane_ie_id', 'sed_ie_id', 'uesvalle_ie_id',
            'codigo_municipio', 'municipio_nombre', 'departamento',
            'direccion', 'telefono', 'email', 'estado', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FactInstitucionMapSerializer(serializers.ModelSerializer):
    """Serializer específico para el mapa - solo datos esenciales."""
    
    municipio_nombre = serializers.ReadOnlyField()
    
    class Meta:
        model = FactInstitucion
        fields = [
            'codigo_dane', 'nombre', 'municipio_nombre', 
            'estado', 'latitud', 'longitud'
        ]


class ChangeLogSerializer(serializers.ModelSerializer):
    """Serializer para el modelo ChangeLog."""
    
    etl_run_info = ETLRunSerializer(source='etl_run', read_only=True)
    
    class Meta:
        model = ChangeLog
        fields = [
            'id', 'etl_run', 'etl_run_info', 'table_name', 'record_id',
            'action', 'old_values', 'new_values', 'timestamp'
        ]
        read_only_fields = ['id', 'etl_run_info', 'timestamp']


class ETLTriggerSerializer(serializers.Serializer):
    """Serializer para disparar ETL via API."""
    
    excel_a_path = serializers.CharField(
        required=False, 
        allow_blank=True,
        help_text="Ruta al archivo Excel A"
    )
    excel_b_path = serializers.CharField(
        required=False, 
        allow_blank=True,
        help_text="Ruta al archivo Excel B"
    )
    mysql_only = serializers.BooleanField(
        default=False,
        help_text="Ejecutar ETL solo con datos de MySQL"
    )
    
    def validate(self, data):
        """Validación personalizada."""
        excel_a = data.get('excel_a_path')
        excel_b = data.get('excel_b_path')
        mysql_only = data.get('mysql_only', False)
        
        if not mysql_only and not excel_a and not excel_b:
            raise serializers.ValidationError(
                "Debe especificar al menos un archivo Excel o usar mysql_only=True"
            )
        
        return data


class ETLStatusSerializer(serializers.Serializer):
    """Serializer para el estado general del ETL."""
    
    last_run = ETLRunSerializer(read_only=True)
    total_runs = serializers.IntegerField(read_only=True)
    successful_runs = serializers.IntegerField(read_only=True)
    failed_runs = serializers.IntegerField(read_only=True)
    running_runs = serializers.IntegerField(read_only=True)
    
    # Estadísticas de datos
    total_instituciones = serializers.IntegerField(read_only=True)
    total_municipios = serializers.IntegerField(read_only=True)
    
    # Por estado de institución
    instituciones_activas = serializers.IntegerField(read_only=True)
    instituciones_inactivas = serializers.IntegerField(read_only=True)
    
    # Por fuente de datos
    instituciones_mysql = serializers.IntegerField(read_only=True)
    instituciones_excel_a = serializers.IntegerField(read_only=True)
    instituciones_excel_b = serializers.IntegerField(read_only=True)


class InstitucionFilterSerializer(serializers.Serializer):
    """Serializer para filtros de búsqueda de instituciones."""
    
    municipio = serializers.CharField(required=False)
    estado = serializers.CharField(required=False)
    sector = serializers.CharField(required=False)
    zona = serializers.CharField(required=False)
    search = serializers.CharField(
        required=False,
        help_text="Buscar en nombre de institución"
    )
    has_coordinates = serializers.BooleanField(
        required=False,
        help_text="Filtrar solo instituciones con coordenadas"
    )


class ETLTriggerSerializer(serializers.Serializer):
    """Serializer para triggers del ETL."""
    
    excel_a_path = serializers.CharField(required=False, allow_blank=True)
    excel_b_path = serializers.CharField(required=False, allow_blank=True)
    mysql_only = serializers.BooleanField(default=False)
    dry_run = serializers.BooleanField(default=False)


class ETLStatusSerializer(serializers.Serializer):
    """Serializer para el estado del ETL."""
    
    last_run = ETLRunSerializer(required=False, allow_null=True)
    total_runs = serializers.IntegerField()
    successful_runs = serializers.IntegerField()
    failed_runs = serializers.IntegerField()
    running_runs = serializers.IntegerField()
    total_instituciones = serializers.IntegerField()
    total_municipios = serializers.IntegerField()
    instituciones_con_dane = serializers.IntegerField()
    instituciones_con_sed = serializers.IntegerField()
    instituciones_con_uesvalle = serializers.IntegerField()
