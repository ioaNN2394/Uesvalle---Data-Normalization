# apps/etl/utils/data_transformers.py
import pandas as pd
import uuid
import logging
from apps.etl.utils.validators import DepartmentValidator

logger = logging.getLogger(__name__)

def transformar_maestras_csv(df: pd.DataFrame) -> tuple:
    """
    Transforma CSV maestro en DataFrames limpios para Institucion y Sede.
    
    Retorna:
        (df_instituciones, df_sedes, mapa_instituciones)
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
        
        # Deduplica instituciones
        df_inst_unique = df_prep.drop_duplicates(subset=['codigo_dane_ie']).copy()
        
        # Construye DF de instituciones
        df_instituciones = pd.DataFrame({
            'id': [str(uuid.uuid4()) for _ in range(len(df_inst_unique))],
            'dane_ie_id': df_inst_unique['codigo_dane_ie'],
            'nombre': df_inst_unique['nombre_institucion'],
            'codigo_municipio': df_inst_unique['codigo_municipio'],
            'direccion': df_inst_unique['direccion'].fillna(None),
            'telefono': df_inst_unique['telefono'].fillna(None),
            'email': df_inst_unique['email'].fillna(None),
            'estado': df_inst_unique['estado'].fillna('A'),
            'metadata': df_inst_unique.apply(
                lambda row: {
                    'origen': 'master_csv',
                    'departamento': row['nombre_departamento'],
                    'municipio': row['municipio']
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
                codigo_dane_ie = str(row['codigo_dane_ie']).strip()
                institucion_id = mapa_inst.get(codigo_dane_ie)
                
                if not institucion_id:
                    continue
                
                # Genera DANE de sede si está vacío
                codigo_dane_sede = str(row.get('codigo_dane_sede', '')).strip()
                if not codigo_dane_sede:
                    codigo_dane_sede = f"{codigo_dane_ie}001"
                
                # Convierte coordenadas
                try:
                    lat = float(str(row.get('latitud', '')).replace(',', '.')) if row.get('latitud') else None
                    lon = float(str(row.get('longitud', '')).replace(',', '.')) if row.get('longitud') else None
                except:
                    lat, lon = None, None
                
                sedes_list.append({
                    'id': str(uuid.uuid4()),
                    'institucion_id': institucion_id,
                    'dane_sede_id': codigo_dane_sede,
                    'nombre': str(row.get('nombre_sede', '')).strip() or f"Sede {row['nombre_institucion']}",
                    'codigo_municipio': str(row.get('codigo_municipio', '')).strip(),
                    'direccion': str(row.get('direccion', '')).strip() if row.get('direccion') else None,
                    'lat': lat,
                    'lon': lon,
                    'estado': str(row.get('estado', 'A')).strip(),
                    'metadata': {
                        'origen': 'master_csv',
                        'jornada': str(row.get('jornada', '')).strip(),
                        'zona': str(row.get('zona', '')).strip(),
                        'departamento': row['nombre_departamento']
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


def transformar_visitas_mysql(df: pd.DataFrame, dict_sedes: dict) -> pd.DataFrame:
    """
    Transforma datos de visitas de MySQL para inserción.
    """
    logger.info("🔄 Transformando visitas de MySQL...")
    
    try:
        # Normaliza columnas a lowercase
        df.columns = [col.lower() for col in df.columns]
        
        # Busca columna de DANE
        col_dane = next((c for c in df.columns if 'dane' in c.lower() and 'sede' in c.lower()), None)
        
        if not col_dane:
            logger.warning("No se encontró columna de DANE sede")
            return pd.DataFrame()
        
        # Mapea DANEs a UUIDs
        df['sede_id'] = df[col_dane].astype(str).map(dict_sedes)
        
        # Filtra huérfanas
        df_validas = df[df['sede_id'].notna()].copy()
        
        logger.info(f"✓ Visitas transformadas: {len(df_validas)} válidas de {len(df)} totales")
        
        return df_validas
    
    except Exception as e:
        logger.error(f"❌ Error transformando visitas: {str(e)}")
        return pd.DataFrame()
