# apps/etl/utils/data_transformers.py
"""
Transformadores de datos para ETL MySQL + CSV
=============================================

Implementa la lógica de transformación según el INSTRUCTIVO DETALLADO:
- MySQL es fuente de verdad (identificacion → uesvalle_ie_id)
- CSV es complementaria (COD_DANE → dane_ie_id)
- Estrategia de merge: MySQL siempre, CSV solo si coincide DANE

FASE 1: Instituciones (MySQL + CSV merge)
FASE 2: Sedes (CSV con coordenadas)
FASE 3: Visitas (MySQL con todos los atributos)
"""

import pandas as pd
import uuid
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple

from apps.etl.utils.validators import DepartmentValidator

logger = logging.getLogger(__name__)


def transformar_maestras_csv(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, str]]:
    """
    Transforma CSV maestro en DataFrames limpios para Institucion y Sede.
    
    Esta función procesa SOLO el CSV del DANE para obtener:
    - Instituciones únicas (por COD_DANE)
    - Sedes con coordenadas
    
    NOTA: Para sincronización completa con MySQL, usar MySQLCSVSyncProcessor
    
    Args:
        df: DataFrame del CSV con columnas DANE
    
    Returns:
        tuple: (df_instituciones, df_sedes, mapa_instituciones)
            - df_instituciones: DataFrame con instituciones únicas
            - df_sedes: DataFrame con sedes
            - mapa_instituciones: Dict[dane_ie_id → UUID]
    """
    logger.info("=" * 60)
    logger.info("🔄 TRANSFORMANDO MAESTRAS (CSV)")
    logger.info("=" * 60)
    
    try:
        # ⭐ PASO 0: Normaliza columnas
        df.columns = [col.strip().upper() for col in df.columns]
        
        # ⭐ PASO 1: Filtra por departamento Valle del Cauca
        logger.info("🔍 Paso 1: Filtrando por departamento...")
        
        dept_col = None
        for possible_name in ['DEPARTAMENTO', 'DEPT', 'DEPARTMENT', 'ID_DEPARTAMENTO']:
            if possible_name in df.columns:
                dept_col = possible_name
                break
        
        if not dept_col:
            raise ValueError("No se encontró columna de departamento")
        
        initial_count = len(df)
        
        # Filtra
        mask = df[dept_col].apply(lambda x: DepartmentValidator.is_valle_cauca(str(x) if x else ''))
        df_filtered = df[mask].copy()
        
        logger.info(f"✓ Filtrado: {len(df_filtered)} del Valle del Cauca, {initial_count - len(df_filtered)} descartadas")
        
        if len(df_filtered) == 0:
            raise ValueError("No hay registros del Valle del Cauca")
        
        # ⭐ PASO 2: Prepara datos de INSTITUCIONES
        logger.info("📋 Paso 2: Preparando instituciones...")
        
        # Mapeo de columnas
        col_mapping = {
            'COD_DANE': 'codigo_dane_ie',
            'NOMBRE_INSTITUCION': 'nombre_institucion',
            'CORREO_INSTITUCIONAL': 'email',
            'DIRECCION': 'direccion',
            'ESTADO': 'estado',
            'ID_MUNICIPIO': 'codigo_municipio',
            'MUNICIPIO': 'municipio',
            'TELEFONO': 'telefono',
            dept_col: 'nombre_departamento'
        }
        
        existing_mapping = {old: new for old, new in col_mapping.items() if old in df_filtered.columns}
        df_prep = df_filtered.rename(columns=existing_mapping).copy()
        
        # Deduplica instituciones por código DANE
        df_inst_unique = df_prep.drop_duplicates(subset=['codigo_dane_ie']).copy()
        
        # Construye DF de instituciones
        df_instituciones = pd.DataFrame({
            'id': [str(uuid.uuid4()) for _ in range(len(df_inst_unique))],
            'dane_ie_id': df_inst_unique['codigo_dane_ie'].astype(str).str.strip(),
            'nombre': df_inst_unique['nombre_institucion'].astype(str).str.strip(),
            'codigo_municipio': df_inst_unique['codigo_municipio'].astype(str).str.strip() if 'codigo_municipio' in df_inst_unique else None,
            'direccion': df_inst_unique['direccion'].fillna(None) if 'direccion' in df_inst_unique else None,
            'telefono': df_inst_unique['telefono'].fillna(None) if 'telefono' in df_inst_unique else None,
            'email': df_inst_unique['email'].fillna(None) if 'email' in df_inst_unique else None,
            'estado': df_inst_unique['estado'].fillna('ACTIVA') if 'estado' in df_inst_unique else 'ACTIVA',
            'metadata': df_inst_unique.apply(
                lambda row: {
                    'origen': 'csv',
                    'departamento': row.get('nombre_departamento', ''),
                    'municipio': row.get('municipio', ''),
                    'fecha_sincronizacion': datetime.now().isoformat()
                }, axis=1
            )
        })
        
        # Mapeo DANE -> UUID para vincular sedes
        mapa_inst = dict(zip(
            df_instituciones['dane_ie_id'],
            df_instituciones['id']
        ))
        
        logger.info(f"✓ Instituciones preparadas: {len(df_instituciones)}")
        
        # ⭐ PASO 3: Prepara datos de SEDES
        logger.info("📋 Paso 3: Preparando sedes...")
        
        df_sedes_raw = df_prep.copy()
        
        # Construye DF de sedes
        sedes_list = []
        for idx, row in df_sedes_raw.iterrows():
            try:
                codigo_dane_ie = str(row.get('codigo_dane_ie', '')).strip()
                institucion_id = mapa_inst.get(codigo_dane_ie)
                
                if not institucion_id:
                    logger.debug(f"Sede sin institución: DANE {codigo_dane_ie}")
                    continue
                
                # Genera DANE de sede si está vacío
                codigo_dane_sede = None
                for col in ['COD_SEDE_PRINCIPAL', 'codigo_dane_sede', 'CODIGO_DANE_SEDE']:
                    if col in row.index and pd.notna(row.get(col)):
                        codigo_dane_sede = str(row[col]).strip()
                        break
                
                if not codigo_dane_sede:
                    codigo_dane_sede = f"{codigo_dane_ie}001"
                
                # Convierte coordenadas (respetando comas decimales)
                lat = _parse_coordinate(row.get('LATITUD') or row.get('latitud'))
                lon = _parse_coordinate(row.get('LONGITUD') or row.get('longitud'))
                
                # Nombre de sede: USAR NOMBRE_INSTITUCION (no SEDE_PRINCIPAL que es boolean S/N)
                # SEDE_PRINCIPAL es una columna booleana que dice si es la sede principal
                # No es el nombre de la sede
                nombre_sede = str(row.get('nombre_institucion', '')).strip()
                
                if not nombre_sede:
                    # Fallback si no existe nombre_institucion
                    nombre_sede = f"Sede {codigo_dane_ie}"
                
                sedes_list.append({
                    'id': str(uuid.uuid4()),
                    'institucion_id': institucion_id,
                    'dane_sede_id': codigo_dane_sede,
                    'nombre': nombre_sede,
                    'codigo_municipio': str(row.get('codigo_municipio', '')).strip() if row.get('codigo_municipio') else None,
                    'direccion': str(row.get('direccion', '')).strip() if row.get('direccion') else None,
                    'lat': lat,
                    'lon': lon,
                    'estado': str(row.get('estado', 'ACTIVA')).strip(),
                    'metadata': {
                        'origen': 'csv',
                        'jornada': str(row.get('JORNADA', '')).strip() if row.get('JORNADA') else '',
                        'zona': str(row.get('ZONA', '')).strip() if row.get('ZONA') else '',
                        'nivel': str(row.get('NIVEL', '')).strip() if row.get('NIVEL') else '',
                        'naturaleza': str(row.get('NATURALEZA', '')).strip() if row.get('NATURALEZA') else '',
                        'sector': str(row.get('SECTOR', '')).strip() if row.get('SECTOR') else '',
                        'calendario': str(row.get('CALENDARIO', '')).strip() if row.get('CALENDARIO') else '',
                        'departamento': row.get('nombre_departamento', ''),
                        'fecha_sincronizacion': datetime.now().isoformat()
                    }
                })
            except Exception as e:
                logger.debug(f"Error preparando sede en fila {idx}: {str(e)}")
                continue
        
        df_sedes = pd.DataFrame(sedes_list)
        
        logger.info(f"✓ Sedes preparadas: {len(df_sedes)}")
        logger.info("=" * 60)
        
        return df_instituciones, df_sedes, mapa_inst
    
    except Exception as e:
        logger.error(f"❌ Error transformando maestras: {str(e)}")
        raise


def transformar_visitas_mysql(
    df: pd.DataFrame, 
    dict_sedes: Dict[str, str],
    dict_instituciones_by_dane: Optional[Dict[str, str]] = None,
    dict_instituciones_by_uesvalle: Optional[Dict[str, str]] = None
) -> pd.DataFrame:
    """
    Transforma datos de visitas de MySQL para inserción.
    
    Implementa FASE 4 del instructivo:
    - institucion_id es OBLIGATORIO
    - sede_id es OPCIONAL (puede ser NULL)
    - Validar conceptovisita (F/D/FCR)
    - Convertir codigotipoobjeto y codigofuncionario a INT
    - Validar fechavisita
    
    Args:
        df: DataFrame de visitas MySQL
        dict_sedes: Mapeo dane_sede_id → UUID
        dict_instituciones_by_dane: Mapeo dane_ie_id → UUID (opcional)
        dict_instituciones_by_uesvalle: Mapeo uesvalle_ie_id → UUID (opcional)
    
    Returns:
        DataFrame de visitas listas para inserción
    """
    logger.info("🔄 Transformando visitas de MySQL...")
    
    try:
        # Normaliza columnas a lowercase
        df.columns = [col.lower() for col in df.columns]
        
        visitas_list = []
        visitas_descartadas = 0
        visitas_sin_sede = 0
        visitas_con_sede = 0
        
        for idx, row in df.iterrows():
            try:
                # ⭐ PASO 1: Buscar institución (OBLIGATORIO)
                institucion_uuid = None
                
                # Primero por codigodane
                codigodane = _get_mysql_value(row, ['codigodane', 'codigo_dane', 'dane'])
                if codigodane and dict_instituciones_by_dane:
                    institucion_uuid = dict_instituciones_by_dane.get(codigodane.upper())
                
                # Si no, por identificacion (uesvalle_ie_id)
                if not institucion_uuid:
                    identificacion = _get_mysql_value(row, ['identificacion', 'uesvalle_ie_id'])
                    if identificacion and dict_instituciones_by_uesvalle:
                        institucion_uuid = dict_instituciones_by_uesvalle.get(identificacion)
                
                # Si no hay institución, descartar visita
                if not institucion_uuid:
                    logger.debug(f"⚠️ Visita fila {idx}: Institución no encontrada")
                    visitas_descartadas += 1
                    continue
                
                # ⭐ PASO 2: Buscar sede (OPCIONAL)
                sede_uuid = None
                codigo_dane_sede = _get_mysql_value(row, ['codigodanesede', 'codigo_dane_sede', 'dane_sede'])
                if codigo_dane_sede:
                    sede_uuid = dict_sedes.get(codigo_dane_sede.upper())
                
                if sede_uuid:
                    visitas_con_sede += 1
                else:
                    visitas_sin_sede += 1
                
                # ⭐ PASO 3: Validar fechavisita (OBLIGATORIO)
                fechavisita = _parse_date(_get_mysql_value(row, ['fechavisita', 'fecha_visita', 'fecha']))
                if not fechavisita:
                    logger.debug(f"⚠️ Visita fila {idx}: fechavisita no válida")
                    visitas_descartadas += 1
                    continue
                
                # ⭐ PASO 4: Validar y transformar campos
                
                # conceptovisita: debe ser F, D, FCR
                conceptovisita = _get_mysql_value(row, ['conceptovisita', 'concepto_visita'])
                if conceptovisita:
                    conceptovisita = conceptovisita.upper().strip()
                    if conceptovisita not in ['F', 'D', 'FCR']:
                        logger.debug(f"conceptovisita '{conceptovisita}' inválido, dejando NULL")
                        conceptovisita = None
                
                # codigotipoobjeto: convertir a INT
                codigotipoobjeto = _parse_int(_get_mysql_value(row, ['codigotipoobjeto', 'codigo_tipo_objeto']))
                
                # codigofuncionario: convertir a INT
                codigofuncionario = _parse_int(_get_mysql_value(row, ['codigofuncionario', 'codigo_funcionario']))
                
                # ⭐ PASO 5: Preparar registro de visita
                # Mapeo EXACTO según esquema MySQL:
                # MySQL.nombreactividad → Supabase.nombreactividad
                # MySQL.codigotipoobjeto → Supabase.codigotipoobjeto (convertir a INT)
                # MySQL.nombretipoobjeto → Supabase.nombretipoobjeto
                # MySQL.conceptovisita → Supabase.conceptovisita (validar F/D/FCR)
                # MySQL.requerimientos → Supabase.requerimientos
                # MySQL.motivovisita → Supabase.motivovisita
                # MySQL.nombrefuncionario → Supabase.nombrefuncionario
                # MySQL.apellidofuncionario → Supabase.apellidofuncionario
                # MySQL.codigofuncionario → Supabase.codigofuncionario (convertir a INT)
                # MySQL.observacion → Supabase.observacion
                # MySQL.nombreactividad → Supabase.programa (usamos nombreactividad como programa)
                # MySQL.conceptovisita → Supabase.resultado (puede ser F/D/FCR)
                
                visita = {
                    'institucion_id': institucion_uuid,
                    'sede_id': sede_uuid,
                    'fechavisita': fechavisita,
                    'nombreactividad': _normalize_string(_get_mysql_value(row, ['nombreactividad'])),
                    'codigotipoobjeto': codigotipoobjeto,
                    'nombretipoobjeto': _normalize_string(_get_mysql_value(row, ['nombretipoobjeto'])),
                    'conceptovisita': conceptovisita,
                    'requerimientos': _normalize_string(_get_mysql_value(row, ['requerimientos'])),
                    'motivovisita': _normalize_string(_get_mysql_value(row, ['motivovisita'])),
                    'nombrefuncionario': _normalize_string(_get_mysql_value(row, ['nombrefuncionario'])),
                    'apellidofuncionario': _normalize_string(_get_mysql_value(row, ['apellidofuncionario'])),
                    'codigofuncionario': codigofuncionario,
                    # Usar nombreactividad como programa (para el índice único)
                    'programa': _normalize_string(_get_mysql_value(row, ['nombreactividad'])),
                    # Usar conceptovisita como resultado
                    'resultado': conceptovisita,
                    'observacion': _normalize_string(_get_mysql_value(row, ['observacion'])),
                    'metadata': _build_metadata(row)
                }
                
                visitas_list.append(visita)
                
            except Exception as e:
                logger.debug(f"Error procesando visita fila {idx}: {str(e)}")
                visitas_descartadas += 1
                continue
        
        df_visitas = pd.DataFrame(visitas_list) if visitas_list else pd.DataFrame()
        
        logger.info(f"✓ Visitas transformadas: {len(df_visitas)} válidas, {visitas_descartadas} descartadas")
        logger.info(f"  - Con sede: {visitas_con_sede}")
        logger.info(f"  - Sin sede: {visitas_sin_sede}")
        
        return df_visitas
    
    except Exception as e:
        logger.error(f"❌ Error transformando visitas: {str(e)}")
        return pd.DataFrame()


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def _get_mysql_value(row: pd.Series, columns: List[str]) -> Optional[str]:
    """Obtiene valor de la primera columna que exista y tenga valor."""
    for col in columns:
        if col in row.index:
            val = row[col]
            if pd.notna(val):
                result = str(val).strip()
                if result.lower() not in ['nan', 'none', '']:
                    return result
    return None


def _parse_coordinate(value: Any) -> Optional[float]:
    """Parsea coordenada a float, manejando comas decimales."""
    if value is None or pd.isna(value):
        return None
    try:
        # Convertir a string y reemplazar coma por punto
        str_val = str(value).replace(',', '.').strip()
        if str_val.lower() in ['nan', 'none', '']:
            return None
        return float(str_val)
    except (ValueError, AttributeError):
        return None


def _parse_date(value: Optional[str]) -> Optional[date]:
    """
    Parsea fecha a formato DATE.
    
    Formatos soportados:
      - YYYY-MM-DD
      - DD/MM/YYYY
      - DD-MM-YYYY
    """
    if not value:
        return None
    try:
        parsed = pd.to_datetime(value, errors='coerce')
        if pd.isna(parsed):
            return None
        return parsed.date()
    except:
        return None


def _parse_int(value: Optional[str]) -> Optional[int]:
    """Parsea valor a INT."""
    if not value:
        return None
    try:
        # Eliminar decimales .0
        cleaned = str(value).replace('.0', '').strip()
        if cleaned.lower() in ['nan', 'none', '']:
            return None
        return int(float(cleaned))
    except (ValueError, TypeError):
        return None


def _normalize_string(value: Optional[str]) -> Optional[str]:
    """Normaliza string: trim, sin caracteres especiales problemáticos."""
    if not value:
        return None
    return value.strip()


def _build_metadata(row: pd.Series) -> Dict[str, Any]:
    """
    Construye metadata con campos adicionales de MySQL.
    
    Guarda campos que no se mapean directamente a la tabla visita,
    pero son útiles para análisis y trazabilidad.
    """
    # Campos que ya se mapean directamente a columnas de visita
    mapped_cols = {
        'fechavisita', 'fecha_visita', 'fecha',
        'conceptovisita', 'concepto_visita',
        'nombreactividad', 'nombre_actividad',
        'codigotipoobjeto', 'codigo_tipo_objeto',
        'nombretipoobjeto', 'nombre_tipo_objeto',
        'requerimientos',
        'motivovisita', 'motivo_visita',
        'nombrefuncionario', 'nombre_funcionario',
        'apellidofuncionario', 'apellido_funcionario',
        'codigofuncionario', 'codigo_funcionario',
        'programa', 'nombre_programa',
        'resultado',
        'observacion', 'observaciones',
        'identificacion', 'uesvalle_ie_id',
        'codigodane', 'codigo_dane', 'dane',
        'codigodanesede', 'codigo_dane_sede', 'dane_sede',
        'institucion_id', 'sede_id'
    }
    
    # Campos importantes de MySQL que guardamos en metadata
    metadata = {
        'origen': 'mysql',
        'fecha_sincronizacion': datetime.now().isoformat(),
        # Datos del establecimiento
        'establecimiento': {
            'nombre': _safe_value(row, 'nombreestablecimiento'),
            'direccion': _safe_value(row, 'direccionestablecimiento'),
            'telefono': _safe_value(row, 'telefonoestablecimiento'),
            'celular': _safe_value(row, 'celular'),
            'codigo': _safe_value(row, 'codigoestablecimiento'),
            'identificacion': _safe_value(row, 'identificacionestablecimiento'),
            'estado': _safe_value(row, 'estadoestablecimiento'),
        },
        # Datos de ubicación
        'ubicacion': {
            'municipio_codigo': _safe_value(row, 'codigomunicipio'),
            'municipio_nombre': _safe_value(row, 'nombremunicipio'),
            'comuna_codigo': _safe_value(row, 'codigocomuna'),
            'comuna_nombre': _safe_value(row, 'nombrecomuna'),
            'corregimiento_codigo': _safe_value(row, 'codigocorregimiento'),
            'corregimiento_nombre': _safe_value(row, 'nombrecorregimiento'),
            'barrio': _safe_value(row, 'nombrebarrio'),
        },
        # Datos de cumplimiento (bloques de evaluación)
        'cumplimiento': {
            'total': _safe_float(row, 'cumplimiento'),
            'bloque1': _safe_float(row, 'bloque1'),
            'bloque2': _safe_float(row, 'bloque2'),
            'bloque3': _safe_float(row, 'bloque3'),
            'bloque4': _safe_float(row, 'bloque4'),
            'bloque5': _safe_float(row, 'bloque5'),
            'bloque6': _safe_float(row, 'bloque6'),
            'bloque7': _safe_float(row, 'bloque7'),
        },
        # Datos PAE (Programa de Alimentación Escolar)
        'pae': {
            'tiene_pae': _safe_value(row, 'tienepae'),
            'estudiantes_hombre': _safe_int(row, 'estudianteshombre'),
            'estudiantes_mujer': _safe_int(row, 'estudiantesmujer'),
            'numero_docentes': _safe_int(row, 'numerosdocente'),
            'total_trabajadores': _safe_int(row, 'totaltrabajador'),
        },
        # Datos del representante legal
        'representante': {
            'nombre': _safe_value(row, 'nombrerepresentante'),
            'apellido': _safe_value(row, 'apellidorepresentante'),
            'codigo': _safe_value(row, 'codigorepresentante'),
        },
        # Datos sanitarios
        'sanitario': {
            'inscripcion': _safe_value(row, 'inscripcionsanitaria'),
            'fecha_inscripcion': _safe_value(row, 'fechainscripcionsanitaria'),
        },
        # Otros datos
        'acta': {
            'numero_manual': _safe_value(row, 'numeromanualacta'),
            'plazo': _safe_int(row, 'plazo'),
        },
        'actividad': {
            'codigo': _safe_value(row, 'codigoactividad'),
            'id': _safe_int(row, 'idactividad'),
        },
        'aro': {
            'codigo': _safe_value(row, 'codigoaro'),
            'nombre': _safe_value(row, 'nombrearo'),
        },
        'piscinas': _safe_int(row, 'numeropiscinas'),
        'tipo_contrato': _safe_value(row, 'tipocontrato'),
        'codigo_anterior': _safe_value(row, 'codigoanterior'),
        'fecha_cargue': _safe_value(row, 'fecha_cargue'),
        'usuario': _safe_value(row, 'nombreusuario'),
    }
    
    # Limpiar valores None de los sub-diccionarios
    for key in ['establecimiento', 'ubicacion', 'cumplimiento', 'pae', 'representante', 'sanitario', 'acta', 'actividad', 'aro']:
        if key in metadata and isinstance(metadata[key], dict):
            metadata[key] = {k: v for k, v in metadata[key].items() if v is not None}
            if not metadata[key]:
                del metadata[key]
    
    # Limpiar valores None del nivel principal
    metadata = {k: v for k, v in metadata.items() if v is not None}
    
    return metadata


def _safe_value(row: pd.Series, col: str) -> Optional[str]:
    """Obtiene valor de forma segura, retorna None si no existe o es NaN."""
    if col not in row.index:
        return None
    val = row[col]
    if pd.isna(val):
        return None
    result = str(val).strip()
    if result.lower() in ['nan', 'none', '']:
        return None
    return result


def _safe_int(row: pd.Series, col: str) -> Optional[int]:
    """Obtiene valor entero de forma segura."""
    val = _safe_value(row, col)
    if val is None:
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def _safe_float(row: pd.Series, col: str) -> Optional[float]:
    """Obtiene valor float de forma segura."""
    val = _safe_value(row, col)
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

