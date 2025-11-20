import pandas as pd
import json
import uuid
import logging
import re

logger = logging.getLogger(__name__)

def limpiar_codigo(val):
    """Convierte valores (float/int/str) a string limpio sin decimales."""
    if pd.isna(val) or str(val).strip() == '' or str(val).lower() == 'nan':
        return None
    # Convertir a string, quitar .0 (ej: 123.0 -> 123) y espacios
    return str(val).replace('.0', '').strip()

def transformar_maestras_csv(df_csv):
    """
    Transforma el CSV específico de Sedes SISE en Instituciones y Sedes.
    Columnas esperadas: COD_DANE, NOMBRE_INSTITUCION, COD_SEDE_PRINCIPAL, SEDE_PRINCIPAL, etc.
    """
    print("--- [TRANSFORMER] Procesando CSV Maestro (Esquema SISE) ---")
    
    # 1. Normalizar encabezados del DataFrame (Quitar espacios, BOM y poner mayúsculas)
    df_csv.columns = [str(c).replace('\ufeff', '').strip().upper() for c in df_csv.columns]
    
    # 2. Crear columnas limpias de IDs
    # COD_DANE -> ID de la Sede
    # COD_SEDE_PRINCIPAL -> ID de la Institución (Padre)
    
    if 'COD_DANE' not in df_csv.columns or 'COD_SEDE_PRINCIPAL' not in df_csv.columns:
        # Fallback por si el CSV usa ';' y pandas no lo detectó bien y metió todo en una columna
        msg = f"❌ Columnas no encontradas. Columnas actuales: {list(df_csv.columns)}"
        print(msg)
        raise ValueError(msg)

    df_csv['ID_SEDE_CLEAN'] = df_csv['COD_DANE'].apply(limpiar_codigo)
    df_csv['ID_INST_CLEAN'] = df_csv['COD_SEDE_PRINCIPAL'].apply(limpiar_codigo)

    # Validación: Si ID_INST_CLEAN es nulo, usaremos ID_SEDE_CLEAN (Caso donde la sede es su propia principal)
    df_csv['ID_INST_CLEAN'] = df_csv['ID_INST_CLEAN'].fillna(df_csv['ID_SEDE_CLEAN'])

    # -------------------------------------------------------------------------
    # A. PROCESAR INSTITUCIONES (Padres)
    # -------------------------------------------------------------------------
    # Agrupamos por el código de la institución (COD_SEDE_PRINCIPAL)
    df_inst_grouped = df_csv.drop_duplicates(subset=['ID_INST_CLEAN'])
    
    data_inst = []
    # Columnas exactas que espera tu Orchestrator._insert_instituciones
    cols_output_inst = ['id', 'nombre', 'dane_ie_id', 'uesvalle_ie_id', 'direccion', 'email', 'estado', 'metadata']

    for _, row in df_inst_grouped.iterrows():
        dane_ie = row['ID_INST_CLEAN']
        if not dane_ie: continue # Saltar filas vacías

        # Mapeo de columnas del CSV -> DB Institucion
        data_inst.append({
            'id': str(uuid.uuid4()),
            'nombre': str(row.get('NOMBRE_INSTITUCION', 'IE SIN NOMBRE')).strip(),
            'dane_ie_id': dane_ie,
            'uesvalle_ie_id': None,
            'direccion': str(row.get('DIRECCION', '')),
            'email': str(row.get('CORREO_INSTITUCIONAL', '')),
            'estado': str(row.get('ESTADO', 'ACTIVO')),
            'metadata': json.dumps({
                'sector': str(row.get('SECTOR', '')),
                'calendario': str(row.get('CALENDARIO', '')),
                'naturaleza': str(row.get('NATURALEZA', '')),
                'origen': 'master_csv'
            })
        })

    df_target_inst = pd.DataFrame(data_inst, columns=cols_output_inst)

    # Validar que no esté vacío
    if df_target_inst.empty:
        print("❌ ERROR: No se generaron instituciones. Revisa que 'COD_SEDE_PRINCIPAL' tenga datos.")
        return df_target_inst, pd.DataFrame(), {}

    # Crear Mapa: DANE_IE -> UUID (Para asignárselo a las sedes)
    mapa_inst_uuid = dict(zip(df_target_inst['dane_ie_id'], df_target_inst['id']))

    # -------------------------------------------------------------------------
    # B. PROCESAR SEDES (Hijos)
    # -------------------------------------------------------------------------
    data_sedes = []
    cols_output_sede = ['id', 'institucion_id', 'nombre', 'dane_sede_id', 'direccion', 'lat', 'lon', 'estado', 'metadata']

    for _, row in df_csv.iterrows():
        dane_sede = row['ID_SEDE_CLEAN']
        dane_padre = row['ID_INST_CLEAN']
        
        if not dane_sede: continue

        # Buscar UUID del padre
        padre_uuid = mapa_inst_uuid.get(dane_padre)
        
        if padre_uuid:
            # Nombre de la sede: Usamos SEDE_PRINCIPAL. Si está vacío, usamos NOMBRE_INSTITUCION
            nombre_sede = str(row.get('SEDE_PRINCIPAL', '')).strip()
            if not nombre_sede or nombre_sede == 'nan':
                nombre_sede = str(row.get('NOMBRE_INSTITUCION', 'Sede')).strip()

            data_sedes.append({
                'id': str(uuid.uuid4()),
                'institucion_id': padre_uuid,
                'nombre': nombre_sede,
                'dane_sede_id': dane_sede,
                'direccion': str(row.get('DIRECCION', '')),
                # Asegurar que Lat/Lon sean numéricos o None
                'lat': pd.to_numeric(row.get('LATITUD'), errors='coerce'),
                'lon': pd.to_numeric(row.get('LONGITUD'), errors='coerce'),
                'estado': str(row.get('ESTADO', 'ACTIVO')),
                'metadata': json.dumps({
                    'zona': str(row.get('ZONA', '')),
                    'jornada': str(row.get('JORNADA', '')),
                    'nivel': str(row.get('NIVEL', '')),
                    'telefono': str(row.get('TELEFONO', '')),
                    'tipo_telefono': str(row.get('TIPO_TELEFONO', '')),
                    'municipio': str(row.get('MUNICIPIO', '')),
                    'id_municipio': str(row.get('ID_MUNICIPIO', ''))
                })
            })

    df_target_sede = pd.DataFrame(data_sedes, columns=cols_output_sede)

    print(f"✓ [TRANSFORMER] Procesado: {len(df_target_inst)} IEs y {len(df_target_sede)} Sedes.")
    return df_target_inst, df_target_sede, mapa_inst_uuid


def transformar_visitas_mysql(df_mysql, mapa_sedes_uuid):
    """
    Transforma datos de MySQL a estructura de Visita PostgreSQL.
    """
    print("--- [TRANSFORMER] Procesando Visitas MySQL ---")
    
    # 1. Limpieza preventiva de tipos para evitar errores .str
    cols_limpiar = ['codigodane', 'codigodanesede', 'telefonoestablecimiento', 'celular']
    for col in cols_limpiar:
        if col in df_mysql.columns:
            # Asegurar conversión a string paso a paso para evitar "Can only use .str accessor..."
            s = df_mysql[col].fillna('')
            s = s.astype(str)
            df_mysql[col] = s.str.replace(r'\.0$', '', regex=True).str.strip()

    # 2. Identificar columnas metadata
    cols_fijas = ['fechavisita', 'conceptovisita', 'observacion', 'codigodanesede', 'codigodane']
    cols_meta = [c for c in df_mysql.columns if c not in cols_fijas]

    data = []
    
    for _, row in df_mysql.iterrows():
        # Buscar Sede UUID usando codigodanesede (prioridad) o codigodane (fallback)
        dane = row.get('codigodanesede', '')
        if not dane: dane = row.get('codigodane', '')
        
        sede_uuid = mapa_sedes_uuid.get(dane)
        
        # Solo procesamos si existe la sede en Postgres (Integridad Referencial)
        if sede_uuid:
            # Empaquetar metadata
            meta_dict = {}
            for col in cols_meta:
                val = row.get(col)
                if pd.notnull(val) and val != '':
                    # Convertir fechas a string para que JSON no falle
                    if isinstance(val, (pd.Timestamp, pd.Period)):
                        val = str(val)
                    meta_dict[col] = val
            
            data.append({
                'sede_id': sede_uuid,
                'fecha': row.get('fechavisita'),
                'resultado': row.get('conceptovisita'),
                'observaciones': row.get('observacion'),
                'metadata': json.dumps(meta_dict)
            })

    return pd.DataFrame(data)
