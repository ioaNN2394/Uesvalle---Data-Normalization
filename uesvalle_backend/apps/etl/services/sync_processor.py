"""
Sincronizador MySQL + CSV para ETL de Instituciones Educativas
==============================================================

Implementa el INSTRUCTIVO DETALLADO: ETL CON SINCRONIZACIÓN MySQL + CSV

Arquitectura de datos:
- Fuente de verdad: MySQL (tiene identificacion que es uesvalle_ie_id)
- Fuente complementaria: CSV del DANE (tiene COD_DANE)

Estrategia de merge:
  1. SI MySQL tiene codigodane Y coincide con CSV COD_DANE → Normaliza + enriquece con CSV
  2. SI MySQL tiene codigodane pero NO existe en CSV → Guarda solo datos MySQL (normalizado)
  3. SI MySQL NO tiene codigodane → Guarda solo datos MySQL (normalizado)
  4. MySQL se guarda SIEMPRE, CSV solo si hay coincidencia de DANE

Orden de ejecución (CRÍTICO - no cambiar):
  1️⃣ CARGAR MUNICIPIOS
  2️⃣ CARGAR INSTITUCIONES (MySQL + CSV merge)
  3️⃣ CARGAR SEDES (CSV con FK a instituciones)
  4️⃣ CARGAR VISITAS (MySQL con FK a instituciones y sedes)
"""

import logging
import uuid
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date

import pandas as pd
from django.db import transaction
from django.utils import timezone

from ..models import Institucion, Sede, Visita, DimMunicipio
from ..utils.validators import DepartmentValidator, VisitaValidator

logger = logging.getLogger('etl.sync_processor')


@dataclass
class ETLMetrics:
    """
    Métricas de procesamiento ETL según FASE 8 del instructivo.
    
    Genera logging detallado y resumen final con estadísticas de:
      - Instituciones (MySQL + CSV merge)
      - Sedes (CSV vinculadas)
      - Visitas (MySQL vinculadas)
    """
    
    # Timestamps
    inicio: datetime = field(default_factory=datetime.now)
    fin: Optional[datetime] = None
    
    # Instituciones
    inst_leidas_mysql: int = 0
    inst_leidas_csv: int = 0
    inst_con_coincidencia_dane: int = 0
    inst_sin_coincidencia_dane: int = 0
    inst_creadas: int = 0
    inst_actualizadas: int = 0
    inst_descartadas: int = 0
    inst_errores: List[str] = field(default_factory=list)
    
    # Sedes
    sedes_leidas_csv: int = 0
    sedes_vinculadas: int = 0
    sedes_descartadas_sin_inst: int = 0
    sedes_creadas: int = 0
    sedes_actualizadas: int = 0
    sedes_errores: List[str] = field(default_factory=list)
    
    # Visitas
    visitas_leidas_mysql: int = 0
    visitas_con_institucion: int = 0
    visitas_con_sede: int = 0
    visitas_sin_sede: int = 0
    visitas_creadas: int = 0
    visitas_actualizadas: int = 0
    visitas_descartadas: int = 0
    visitas_errores: List[str] = field(default_factory=list)
    
    def finalizar(self) -> None:
        """Marca el fin del procesamiento."""
        self.fin = datetime.now()
    
    def duracion_segundos(self) -> float:
        """Calcula duración en segundos."""
        if self.fin:
            return (self.fin - self.inicio).total_seconds()
        return (datetime.now() - self.inicio).total_seconds()
    
    def log_institucion_creada(self, nombre: str, dane_ie_id: str, uesvalle_ie_id: str) -> None:
        """Log cuando se crea institución."""
        logger.info(f"✓ Institución creada: {nombre} (DANE: {dane_ie_id}, uesvalle_ie_id: {uesvalle_ie_id})")
        self.inst_creadas += 1
    
    def log_institucion_actualizada(self, nombre: str, dane_ie_id: str) -> None:
        """Log cuando se actualiza institución."""
        logger.debug(f"↻ Institución actualizada: {nombre} (DANE: {dane_ie_id})")
        self.inst_actualizadas += 1
    
    def log_institucion_descartada(self, razon: str, identificacion: str) -> None:
        """Log cuando se descarta institución."""
        msg = f"✗ Institución descartada: {identificacion} - {razon}"
        logger.warning(msg)
        self.inst_descartadas += 1
        self.inst_errores.append(msg)
    
    def log_sede_creada(self, nombre: str, dane_sede_id: str, institucion_nombre: str) -> None:
        """Log cuando se crea sede."""
        logger.info(f"✓ Sede creada: {nombre} (DANE: {dane_sede_id}) → {institucion_nombre}")
        self.sedes_creadas += 1
    
    def log_sede_descartada(self, razon: str, dane_sede_id: str) -> None:
        """Log cuando se descarta sede."""
        msg = f"✗ Sede descartada: {dane_sede_id} - {razon}"
        logger.warning(msg)
        self.sedes_descartadas_sin_inst += 1
        self.sedes_errores.append(msg)
    
    def log_visita_creada(self, institucion_nombre: str, fecha: str, con_sede: bool) -> None:
        """Log cuando se crea visita."""
        sede_status = "con sede" if con_sede else "SIN sede"
        logger.debug(f"✓ Visita creada: {institucion_nombre} ({fecha}) [{sede_status}]")
        self.visitas_creadas += 1
        if con_sede:
            self.visitas_con_sede += 1
        else:
            self.visitas_sin_sede += 1
    
    def log_visita_descartada(self, razon: str, identificacion: str) -> None:
        """Log cuando se descarta visita."""
        msg = f"✗ Visita descartada: {identificacion} - {razon}"
        logger.warning(msg)
        self.visitas_descartadas += 1
        self.visitas_errores.append(msg)
    
    def resumen(self) -> str:
        """Genera resumen de métricas según FASE 8 del instructivo."""
        self.finalizar()
        duracion = self.duracion_segundos()
        
        # Calcular tasas de éxito
        tasa_inst = (self.inst_creadas + self.inst_actualizadas) / max(self.inst_leidas_mysql, 1) * 100
        tasa_sedes = self.sedes_creadas / max(self.sedes_leidas_csv, 1) * 100
        tasa_visitas = (self.visitas_creadas + self.visitas_actualizadas) / max(self.visitas_leidas_mysql, 1) * 100
        
        errores_totales = len(self.inst_errores) + len(self.sedes_errores) + len(self.visitas_errores)
        
        resumen = f"""
{'='*60}
                    RESUMEN ETL MySQL + CSV
{'='*60}

⏱️  TIEMPO DE EJECUCIÓN: {duracion:.2f} segundos

📊 INSTITUCIONES (MySQL → Destino):
   • Leídas MySQL:     {self.inst_leidas_mysql:>6}
   • Leídas CSV:       {self.inst_leidas_csv:>6}
   • Con match DANE:   {self.inst_con_coincidencia_dane:>6}
   • Sin match DANE:   {self.inst_sin_coincidencia_dane:>6}
   • Creadas:          {self.inst_creadas:>6}
   • Actualizadas:     {self.inst_actualizadas:>6}
   • Descartadas:      {self.inst_descartadas:>6}
   • Tasa de éxito:    {tasa_inst:>5.1f}%

🏫 SEDES (CSV → Destino):
   • Leídas CSV:            {self.sedes_leidas_csv:>6}
   • Vinculadas a inst:     {self.sedes_vinculadas:>6}
   • Creadas:               {self.sedes_creadas:>6}
   • Actualizadas:          {self.sedes_actualizadas:>6}
   • Sin institución:       {self.sedes_descartadas_sin_inst:>6}
   • Tasa de éxito:         {tasa_sedes:>5.1f}%

📋 VISITAS (MySQL → Destino):
   • Leídas MySQL:          {self.visitas_leidas_mysql:>6}
   • Con institución:       {self.visitas_con_institucion:>6}
   • Con sede:              {self.visitas_con_sede:>6}
   • Sin sede (OK):         {self.visitas_sin_sede:>6}
   • Creadas:               {self.visitas_creadas:>6}
   • Actualizadas:          {self.visitas_actualizadas:>6}
   • Descartadas:           {self.visitas_descartadas:>6}
   • Tasa de éxito:         {tasa_visitas:>5.1f}%

{'='*60}
{'✅ ETL COMPLETADO EXITOSAMENTE' if errores_totales == 0 else f'⚠️  ETL COMPLETADO CON {errores_totales} ADVERTENCIAS'}
{'='*60}
"""
        return resumen.strip()
    
    def resumen_errores(self) -> str:
        """Genera resumen detallado de errores."""
        if not (self.inst_errores or self.sedes_errores or self.visitas_errores):
            return "✓ Sin errores registrados"
        
        lines = ["❌ ERRORES ENCONTRADOS:", ""]
        
        if self.inst_errores:
            lines.append(f"  Instituciones ({len(self.inst_errores)}):")
            for err in self.inst_errores[:10]:  # Máximo 10
                lines.append(f"    • {err}")
            if len(self.inst_errores) > 10:
                lines.append(f"    ... y {len(self.inst_errores) - 10} más")
        
        if self.sedes_errores:
            lines.append(f"  Sedes ({len(self.sedes_errores)}):")
            for err in self.sedes_errores[:10]:
                lines.append(f"    • {err}")
            if len(self.sedes_errores) > 10:
                lines.append(f"    ... y {len(self.sedes_errores) - 10} más")
        
        if self.visitas_errores:
            lines.append(f"  Visitas ({len(self.visitas_errores)}):")
            for err in self.visitas_errores[:10]:
                lines.append(f"    • {err}")
            if len(self.visitas_errores) > 10:
                lines.append(f"    ... y {len(self.visitas_errores) - 10} más")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Exporta métricas a diccionario para respuesta API."""
        return {
            'duracion_segundos': self.duracion_segundos(),
            'instituciones': {
                'leidas_mysql': self.inst_leidas_mysql,
                'leidas_csv': self.inst_leidas_csv,
                'con_match_dane': self.inst_con_coincidencia_dane,
                'sin_match_dane': self.inst_sin_coincidencia_dane,
                'creadas': self.inst_creadas,
                'actualizadas': self.inst_actualizadas,
                'descartadas': self.inst_descartadas,
            },
            'sedes': {
                'leidas_csv': self.sedes_leidas_csv,
                'vinculadas': self.sedes_vinculadas,
                'creadas': self.sedes_creadas,
                'actualizadas': self.sedes_actualizadas,
                'sin_institucion': self.sedes_descartadas_sin_inst,
            },
            'visitas': {
                'leidas_mysql': self.visitas_leidas_mysql,
                'con_institucion': self.visitas_con_institucion,
                'con_sede': self.visitas_con_sede,
                'sin_sede': self.visitas_sin_sede,
                'creadas': self.visitas_creadas,
                'actualizadas': self.visitas_actualizadas,
                'descartadas': self.visitas_descartadas,
            },
            'errores': {
                'instituciones': len(self.inst_errores),
                'sedes': len(self.sedes_errores),
                'visitas': len(self.visitas_errores),
            }
        }


class MySQLCSVSyncProcessor:
    """
    Procesador principal para sincronización MySQL + CSV.
    
    Uso:
        processor = MySQLCSVSyncProcessor()
        processor.load_mysql_data(df_mysql)
        processor.load_csv_data(df_csv)
        metrics = processor.execute_sync()
    """
    
    def __init__(self):
        self.df_mysql: Optional[pd.DataFrame] = None
        self.df_csv: Optional[pd.DataFrame] = None
        self.csv_by_dane: Dict[str, pd.Series] = {}  # Mapeo COD_DANE → fila CSV
        self.metrics = ETLMetrics()
        
        # Diccionarios de mapeo cargados dinámicamente
        self.dict_instituciones_by_dane: Dict[str, str] = {}      # dane_ie_id → UUID
        self.dict_instituciones_by_uesvalle: Dict[str, str] = {}  # uesvalle_ie_id → UUID
        self.dict_sedes_by_institucion: Dict[str, List[str]] = {} # institucion_id → [sede_ids]
        self.dict_sedes_by_dane: Dict[str, str] = {}              # dane_sede_id → UUID
    
    def load_mysql_data(self, df: pd.DataFrame) -> None:
        """
        Carga datos de MySQL (visitas/instituciones).
        
        Columnas esperadas de MySQL:
          - identificacion (uesvalle_ie_id)
          - codigodane (opcional)
          - fechavisita, nombreactividad, conceptovisita, etc.
        """
        logger.info("📥 Cargando datos de MySQL...")
        
        # Normalizar columnas a lowercase
        df.columns = [col.strip().lower() for col in df.columns]
        
        self.df_mysql = df.copy()
        self.metrics.inst_leidas_mysql = len(df['identificacion'].dropna().unique()) if 'identificacion' in df.columns else 0
        self.metrics.visitas_leidas_mysql = len(df)
        
        logger.info(f"✓ MySQL: {self.metrics.inst_leidas_mysql} instituciones únicas, {self.metrics.visitas_leidas_mysql} visitas")
    
    def load_csv_data(self, df: pd.DataFrame) -> None:
        """
        Carga datos de CSV DANE.
        
        Columnas esperadas:
          - COD_DANE (11 dígitos)
          - NOMBRE_INSTITUCION
          - SEDE_PRINCIPAL, COD_SEDE_PRINCIPAL
          - LATITUD, LONGITUD
          - MUNICIPIO, ID_MUNICIPIO
        """
        logger.info("📥 Cargando datos de CSV DANE...")
        
        # Normalizar columnas a uppercase
        df.columns = [col.strip().upper() for col in df.columns]
        
        # Filtrar solo Valle del Cauca
        dept_col = None
        for col in ['DEPARTAMENTO', 'ID_DEPARTAMENTO']:
            if col in df.columns:
                dept_col = col
                break
        
        if dept_col:
            initial_count = len(df)
            mask = df[dept_col].apply(lambda x: DepartmentValidator.is_valle_cauca(str(x) if pd.notna(x) else ''))
            df = df[mask].copy()
            logger.info(f"✓ Filtrado Valle del Cauca: {len(df)}/{initial_count} registros")
        
        self.df_csv = df.copy()
        
        # Crear mapeo COD_DANE → fila para búsqueda rápida (OPTIMIZADO: sin iterrows())
        if 'COD_DANE' in df.columns:
            # Vectorizado: mucho más rápido que iterrows()
            df_clean = df.copy()
            df_clean['COD_DANE_CLEAN'] = (
                df_clean['COD_DANE'].astype(str).str.strip().str.upper()
            )
            # Filtrar valores inválidos
            df_valid = df_clean[
                (df_clean['COD_DANE_CLEAN'].notna()) & 
                (df_clean['COD_DANE_CLEAN'] != 'NAN') &
                (df_clean['COD_DANE_CLEAN'] != '')
            ]
            # Crear diccionario
            self.csv_by_dane = dict(zip(
                df_valid['COD_DANE_CLEAN'],
                df_valid.drop(columns=['COD_DANE_CLEAN']).to_dict('records')
            ))
            # Alternativa si necesitas Series en lugar de dict:
            # self.csv_by_dane = {k: v for k, v in zip(df_valid['COD_DANE_CLEAN'], df_valid.itertuples(index=False))}
            # Mejor opción para acceso por columna:
            self.csv_by_dane = {
                dane: df_valid[df_valid['COD_DANE_CLEAN'] == dane].iloc[0] 
                for dane in df_valid['COD_DANE_CLEAN'].unique()
            }
        
        self.metrics.inst_leidas_csv = len(self.csv_by_dane)
        self.metrics.sedes_leidas_csv = len(df)
        
        logger.info(f"✓ CSV: {self.metrics.inst_leidas_csv} instituciones únicas por DANE, {self.metrics.sedes_leidas_csv} sedes")
    
    def execute_sync(self) -> ETLMetrics:
        """
        Ejecuta sincronización completa en orden correcto.
        
        Orden (CRÍTICO):
          1️⃣ INSTITUCIONES (MySQL + CSV merge)
          2️⃣ SEDES (CSV vinculadas a instituciones)
          3️⃣ VISITAS (MySQL vinculadas a instituciones/sedes)
        """
        logger.info("=" * 60)
        logger.info("🔄 INICIANDO SINCRONIZACIÓN MySQL + CSV")
        logger.info("=" * 60)
        
        try:
            # FASE 1: Cargar instituciones
            logger.info("\n1️⃣  FASE 1: CARGANDO INSTITUCIONES...")
            self._sync_instituciones()
            
            # Recargar diccionarios
            self._load_dictionaries()
            
            # FASE 2: Cargar sedes
            logger.info("\n2️⃣  FASE 2: CARGANDO SEDES...")
            self._sync_sedes()
            
            # Recargar diccionarios de sedes
            self._load_dictionaries()
            
            # FASE 3: Cargar visitas
            logger.info("\n3️⃣  FASE 3: CARGANDO VISITAS...")
            self._sync_visitas()
            
            logger.info("\n" + "=" * 60)
            logger.info(self.metrics.resumen())
            logger.info("=" * 60)
            
            return self.metrics
            
        except Exception as e:
            logger.error(f"❌ Error crítico en sincronización: {e}", exc_info=True)
            raise
    
    def _load_dictionaries(self) -> None:
        """Carga/recarga diccionarios de mapeo desde BD."""
        # Instituciones por DANE (puede haber múltiples con mismo DANE)
        self.dict_instituciones_by_dane = {}
        for inst in Institucion.objects.filter(dane_ie_id__isnull=False):
            if inst.dane_ie_id not in self.dict_instituciones_by_dane:
                self.dict_instituciones_by_dane[inst.dane_ie_id] = []
            self.dict_instituciones_by_dane[inst.dane_ie_id].append(str(inst.id))
        
        # Instituciones por uesvalle_ie_id (puede haber múltiples con mismo ID)
        self.dict_instituciones_by_uesvalle = {}
        for inst in Institucion.objects.filter(uesvalle_ie_id__isnull=False):
            if inst.uesvalle_ie_id not in self.dict_instituciones_by_uesvalle:
                self.dict_instituciones_by_uesvalle[inst.uesvalle_ie_id] = []
            self.dict_instituciones_by_uesvalle[inst.uesvalle_ie_id].append(str(inst.id))
        
        # Mapeo por clave compuesta (uesvalle_ie_id + nombre normalizado) -> UUID
        # Esta es la clave real para identificar instituciones únicas
        self.dict_instituciones_by_key = {}
        for inst in Institucion.objects.filter(uesvalle_ie_id__isnull=False):
            key = self._make_inst_key(inst.uesvalle_ie_id, inst.nombre)
            self.dict_instituciones_by_key[key] = str(inst.id)
        
        # Sedes por DANE
        self.dict_sedes_by_dane = {
            sede.dane_sede_id: str(sede.id)
            for sede in Sede.objects.filter(dane_sede_id__isnull=False)
        }
        
        # Sedes por institución
        self.dict_sedes_by_institucion = {}
        for sede in Sede.objects.filter(institucion_id__isnull=False):
            inst_id = str(sede.institucion_id)
            if inst_id not in self.dict_sedes_by_institucion:
                self.dict_sedes_by_institucion[inst_id] = []
            self.dict_sedes_by_institucion[inst_id].append(str(sede.id))
        
        logger.info(f"📚 Diccionarios cargados: {len(self.dict_instituciones_by_key)} IEs (clave compuesta), "
                   f"{len(self.dict_sedes_by_dane)} Sedes")
    
    def _make_inst_key(self, uesvalle_id: str, nombre: str) -> str:
        """
        Crea una clave única para identificar instituciones.
        Combina uesvalle_ie_id + nombre normalizado.
        """
        uesvalle_id = str(uesvalle_id).strip().upper() if uesvalle_id else ''
        nombre = str(nombre).strip().upper() if nombre else ''
        return f"{uesvalle_id}|{nombre}"
    
    # =========================================================================
    # FASE 1: SINCRONIZACIÓN DE INSTITUCIONES
    # =========================================================================
    
    def _sync_instituciones(self) -> None:
        """
        Sincroniza instituciones MySQL + CSV según instructivo.
        
        Estrategia CORREGIDA:
          - Cada fila de MySQL con identificacion + nombre único = 1 institución
          - NO deduplicar solo por identificacion (hay instituciones con mismo código pero diferente nombre)
          - MySQL.identificacion SIEMPRE → uesvalle_ie_id
          - SI MySQL tiene codigodane Y existe en CSV → Enriquece
        """
        if self.df_mysql is None:
            logger.warning("⚠️ No hay datos de MySQL cargados")
            return
        
        col_identificacion = 'identificacion'
        col_codigodane = 'codigodane'
        
        if col_identificacion not in self.df_mysql.columns:
            logger.error(f"❌ Columna '{col_identificacion}' no encontrada en MySQL")
            return
        
        # Buscar columna de nombre (puede variar)
        col_nombre = None
        for possible_name in ['nombreestablecimiento', 'nombreinstitucion', 'nombre_institucion', 'nombre', 'razonsocial']:
            if possible_name in self.df_mysql.columns:
                col_nombre = possible_name
                break
        
        if not col_nombre:
            logger.warning("⚠️ No se encontró columna de nombre, usando solo identificacion")
            col_nombre = col_identificacion
        
        # CLAVE: Deduplicar por identificacion + nombre (clave compuesta)
        # Esto permite tener "POLICARPA BACHILLER" y "POLICARPA PRIMARIA" con mismo código
        subset_cols = [col_identificacion]
        if col_nombre != col_identificacion:
            subset_cols.append(col_nombre)
        
        instituciones_mysql = self.df_mysql.drop_duplicates(subset=subset_cols)
        
        logger.info(f"📋 Procesando {len(instituciones_mysql)} instituciones únicas de MySQL ")
        logger.info(f"   (deduplicadas por: {subset_cols})")
        logger.info(f"   Total filas MySQL: {len(self.df_mysql)}")
        
        for idx, row in instituciones_mysql.iterrows():
            try:
                uesvalle_id = str(row.get(col_identificacion, '')).strip()
                codigodane = str(row.get(col_codigodane, '')).strip() if col_codigodane in row.index else ''
                
                # Limpiar codigodane (puede ser 'nan', vacío, etc.)
                if codigodane.lower() in ['nan', 'none', '']:
                    codigodane = None
                
                if not uesvalle_id or uesvalle_id.lower() in ['nan', 'none']:
                    logger.debug(f"Fila {idx}: Sin identificacion, saltando")
                    self.metrics.inst_descartadas += 1
                    continue
                
                # Preparar datos base de MySQL
                inst_data = self._prepare_institucion_from_mysql(row, uesvalle_id, codigodane)
                
                # Enriquecer con CSV si hay coincidencia de DANE
                csv_row = None
                if codigodane:
                    csv_row = self.csv_by_dane.get(codigodane.upper())
                    if csv_row is not None:
                        inst_data = self._enrich_with_csv(inst_data, csv_row)
                        self.metrics.inst_con_coincidencia_dane += 1
                        logger.debug(f"✓ Institución enriquecida con CSV: {inst_data['nombre']}")
                    else:
                        self.metrics.inst_sin_coincidencia_dane += 1
                else:
                    self.metrics.inst_sin_coincidencia_dane += 1
                
                # Guardar institución usando clave compuesta
                created = self._save_institucion(inst_data)
                
                if created:
                    self.metrics.inst_creadas += 1
                else:
                    self.metrics.inst_actualizadas += 1
                    
            except Exception as e:
                error_msg = f"Error procesando institución fila {idx}: {str(e)}"
                logger.warning(f"❌ {error_msg}")
                self.metrics.inst_errores.append(error_msg)
                self.metrics.inst_descartadas += 1
        
        logger.info(f"✓ Instituciones: {self.metrics.inst_creadas} creadas, "
                   f"{self.metrics.inst_actualizadas} actualizadas, "
                   f"{self.metrics.inst_descartadas} descartadas")
    
    def _prepare_institucion_from_mysql(self, row: pd.Series, uesvalle_id: str, codigodane: Optional[str]) -> Dict[str, Any]:
        """Prepara datos de institución desde MySQL."""
        # Buscar nombre de institución (puede estar en diferentes columnas)
        # IMPORTANTE: nombreestablecimiento es la columna principal en MySQL
        nombre = None
        for col in ['nombreestablecimiento', 'nombreinstitucion', 'nombre_institucion', 'nombre', 'razonsocial']:
            if col in row.index and pd.notna(row.get(col)):
                nombre = str(row[col]).strip()
                break
        
        if not nombre:
            nombre = f"Institución {uesvalle_id}"
        
        # Buscar código de municipio
        codigo_municipio = None
        for col in ['codigomunicipio', 'codigo_municipio', 'municipio_codigo']:
            if col in row.index and pd.notna(row.get(col)):
                codigo_municipio = str(row[col]).strip()
                break
        
        return {
            'uesvalle_ie_id': uesvalle_id,
            'dane_ie_id': codigodane,
            'nombre': nombre,
            'codigo_municipio': codigo_municipio,
            'direccion': self._get_value(row, ['direccion', 'dir']),
            'telefono': self._get_value(row, ['telefono', 'tel']),
            'email': self._get_value(row, ['email', 'correo']),
            'estado': self._get_value(row, ['estado']) or 'ACTIVA',
            'metadata': {
                'origen': 'mysql',
                'campos_mysql': list(row.index),
                'fecha_sincronizacion': datetime.now().isoformat()
            }
        }
    
    def _enrich_with_csv(self, inst_data: Dict[str, Any], csv_row: pd.Series) -> Dict[str, Any]:
        """
        Enriquece datos de institución con CSV.
        
        Prioridad:
          - Mantener datos MySQL (nombre, estado, email, telefono)
          - Enriquecer SOLO campos que MySQL no tiene:
            - direccion, municipio, coordenadas, jornada, zona
        """
        # Campos que se enriquecen solo si MySQL no los tiene
        if not inst_data.get('direccion'):
            inst_data['direccion'] = self._get_csv_value(csv_row, 'DIRECCION')
        
        if not inst_data.get('codigo_municipio'):
            inst_data['codigo_municipio'] = self._get_csv_value(csv_row, 'ID_MUNICIPIO')
        
        # Actualizar metadata
        inst_data['metadata']['origen'] = 'mysql+csv'
        inst_data['metadata']['campos_csv'] = ['DIRECCION', 'ID_MUNICIPIO', 'MUNICIPIO', 'ZONA', 'JORNADA']
        inst_data['metadata']['municipio_nombre'] = self._get_csv_value(csv_row, 'MUNICIPIO')
        inst_data['metadata']['zona'] = self._get_csv_value(csv_row, 'ZONA')
        inst_data['metadata']['jornada'] = self._get_csv_value(csv_row, 'JORNADA')
        
        return inst_data
    
    def _save_institucion(self, data: Dict[str, Any]) -> bool:
        """
        Guarda institución usando clave compuesta (uesvalle_ie_id + nombre).
        
        IMPORTANTE: Hay instituciones con el mismo código (uesvalle_ie_id o dane_ie_id)
        pero diferente nombre (ej: PRIMARIA vs BACHILLER). Por eso usamos
        uesvalle_ie_id + nombre como clave compuesta.
        
        Returns:
            bool: True si fue creada, False si fue actualizada
        """
        try:
            # Normalizar nombre para búsqueda
            nombre_normalizado = str(data['nombre']).strip()
            uesvalle_id = str(data['uesvalle_ie_id']).strip()
            
            # Buscar institución existente por clave compuesta (uesvalle_ie_id + nombre)
            existing = Institucion.objects.filter(
                uesvalle_ie_id=uesvalle_id,
                nombre__iexact=nombre_normalizado
            ).first()
            
            if existing:
                # Actualizar institución existente
                existing.dane_ie_id = data.get('dane_ie_id') or existing.dane_ie_id
                existing.codigo_municipio = data.get('codigo_municipio') or existing.codigo_municipio
                existing.direccion = data.get('direccion') or existing.direccion
                existing.telefono = data.get('telefono') or existing.telefono
                existing.email = data.get('email') or existing.email
                existing.estado = data.get('estado', 'ACTIVA')
                existing.metadata = data.get('metadata', {})
                existing.save()
                
                logger.debug(f"✓ Institución actualizada: {nombre_normalizado} (UESValle: {uesvalle_id})")
                return False
            else:
                # Crear nueva institución
                Institucion.objects.create(
                    nombre=nombre_normalizado,
                    uesvalle_ie_id=uesvalle_id,
                    dane_ie_id=data.get('dane_ie_id'),
                    codigo_municipio=data.get('codigo_municipio'),
                    direccion=data.get('direccion'),
                    telefono=data.get('telefono'),
                    email=data.get('email'),
                    estado=data.get('estado', 'ACTIVA'),
                    metadata=data.get('metadata', {})
                )
                
                logger.debug(f"✓ Institución creada: {nombre_normalizado} (UESValle: {uesvalle_id})")
                return True
            
        except Exception as e:
            logger.error(f"❌ Error guardando institución {data.get('nombre')}: {e}")
            raise
    
    # =========================================================================
    # FASE 2: SINCRONIZACIÓN DE SEDES
    # =========================================================================
    
    def _sync_sedes(self) -> None:
        """
        Sincroniza sedes desde CSV vinculándolas a instituciones.
        
        Estrategia:
          - Sedes SOLO vienen del CSV (tienen coordenadas)
          - Cada sede debe vincularse a una institución existente
          - Si institución no existe → DESCARTAR sede
        """
        if self.df_csv is None:
            logger.warning("⚠️ No hay datos de CSV cargados para sedes")
            return
        
        logger.info(f"📋 Procesando {len(self.df_csv)} sedes del CSV...")
        
        for idx, row in self.df_csv.iterrows():
            try:
                cod_dane = self._get_csv_value(row, 'COD_DANE')
                
                if not cod_dane:
                    logger.debug(f"Fila {idx}: Sin COD_DANE, saltando sede")
                    self.metrics.sedes_descartadas_sin_inst += 1
                    continue
                
                # Buscar institución por DANE
                institucion_uuid = self.dict_instituciones_by_dane.get(cod_dane.upper())
                
                if not institucion_uuid:
                    logger.debug(f"⚠️ Institución no encontrada para sede DANE {cod_dane}")
                    self.metrics.sedes_descartadas_sin_inst += 1
                    continue
                
                # Preparar datos de sede
                sede_data = self._prepare_sede_from_csv(row, cod_dane, institucion_uuid)
                
                # Guardar sede
                self._save_sede(sede_data)
                self.metrics.sedes_creadas += 1
                self.metrics.sedes_vinculadas += 1
                
            except Exception as e:
                error_msg = f"Error procesando sede fila {idx}: {str(e)}"
                logger.warning(f"❌ {error_msg}")
                self.metrics.sedes_errores.append(error_msg)
        
        logger.info(f"✓ Sedes: {self.metrics.sedes_creadas} creadas, "
                   f"{self.metrics.sedes_descartadas_sin_inst} descartadas (sin institución)")
    
    def _prepare_sede_from_csv(self, row: pd.Series, cod_dane_ie: str, institucion_uuid: str) -> Dict[str, Any]:
        """Prepara datos de sede desde CSV."""
        # Generar dane_sede_id
        cod_sede = self._get_csv_value(row, 'COD_SEDE_PRINCIPAL')
        if not cod_sede:
            cod_sede = f"{cod_dane_ie}001"
        
        # Convertir coordenadas
        lat = self._parse_coordinate(self._get_csv_value(row, 'LATITUD'))
        lon = self._parse_coordinate(self._get_csv_value(row, 'LONGITUD'))
        
        # NOMBRE CORRECTO: usar NOMBRE_INSTITUCION, no SEDE_PRINCIPAL (que es boolean S/N)
        nombre_sede = self._get_csv_value(row, 'NOMBRE_INSTITUCION') or f"Sede {cod_dane_ie}"
        
        return {
            'institucion_id': institucion_uuid,
            'dane_sede_id': cod_sede,
            'nombre': nombre_sede,
            'codigo_municipio': self._get_csv_value(row, 'ID_MUNICIPIO'),
            'direccion': self._get_csv_value(row, 'DIRECCION'),
            'lat': lat,
            'lon': lon,
            'estado': self._get_csv_value(row, 'ESTADO') or 'ACTIVA',
            'metadata': {
                'origen': 'csv',
                'jornada': self._get_csv_value(row, 'JORNADA'),
                'zona': self._get_csv_value(row, 'ZONA'),
                'nivel': self._get_csv_value(row, 'NIVEL'),
                'naturaleza': self._get_csv_value(row, 'NATURALEZA'),
                'sector': self._get_csv_value(row, 'SECTOR'),
                'calendario': self._get_csv_value(row, 'CALENDARIO'),
                'fecha_sincronizacion': datetime.now().isoformat()
            }
        }
    
    def _save_sede(self, data: Dict[str, Any]) -> bool:
        """Guarda sede usando update_or_create."""
        try:
            obj, created = Sede.objects.update_or_create(
                dane_sede_id=data['dane_sede_id'],
                defaults={
                    'institucion_id': data['institucion_id'],
                    'nombre': data['nombre'],
                    'codigo_municipio': data.get('codigo_municipio'),
                    'direccion': data.get('direccion'),
                    'lat': data.get('lat'),
                    'lon': data.get('lon'),
                    'estado': data.get('estado', 'ACTIVA'),
                    'metadata': data.get('metadata', {})
                }
            )
            
            action = "creada" if created else "actualizada"
            logger.debug(f"✓ Sede {action}: {data['nombre']} (DANE: {data['dane_sede_id']})")
            return created
            
        except Exception as e:
            logger.error(f"❌ Error guardando sede {data.get('nombre')}: {e}")
            raise
    
    # =========================================================================
    # FASE 3: SINCRONIZACIÓN DE VISITAS
    # =========================================================================
    
    def _sync_visitas(self) -> None:
        """
        Sincroniza visitas desde MySQL vinculándolas a instituciones y sedes.
        
        Estrategia:
          - institucion_id es OBLIGATORIO (no guardar si no existe)
          - sede_id es OPCIONAL (puede ser NULL)
          - Buscar institución por: 1) codigodane, 2) identificacion (uesvalle_ie_id)
        """
        if self.df_mysql is None:
            logger.warning("⚠️ No hay datos de MySQL cargados para visitas")
            return
        
        logger.info(f"📋 Procesando {len(self.df_mysql)} visitas de MySQL...")
        
        visitas_batch = []
        
        for idx, row in self.df_mysql.iterrows():
            try:
                # Obtener institucion_id
                institucion_uuid = self._find_institucion_for_visita(row)
                
                if not institucion_uuid:
                    logger.debug(f"⚠️ Visita fila {idx}: Institución no encontrada, descartando")
                    self.metrics.visitas_descartadas += 1
                    self.metrics.visitas_errores.append(f"Fila {idx}: Institución no encontrada")
                    continue
                
                self.metrics.visitas_con_institucion += 1
                
                # Obtener sede_id (opcional)
                sede_uuid = self._find_sede_for_visita(institucion_uuid, row)
                
                if sede_uuid:
                    self.metrics.visitas_con_sede += 1
                else:
                    self.metrics.visitas_sin_sede += 1
                
                # Preparar datos de visita
                visita_data = self._prepare_visita_from_mysql(row, institucion_uuid, sede_uuid)
                
                if visita_data:
                    visitas_batch.append(visita_data)
                    
                    # Guardar en batches de 500
                    if len(visitas_batch) >= 500:
                        self._save_visitas_batch(visitas_batch)
                        visitas_batch = []
                
            except Exception as e:
                error_msg = f"Error procesando visita fila {idx}: {str(e)}"
                logger.warning(f"❌ {error_msg}")
                self.metrics.visitas_errores.append(error_msg)
                self.metrics.visitas_descartadas += 1
        
        # Guardar últimas visitas
        if visitas_batch:
            self._save_visitas_batch(visitas_batch)
        
        logger.info(f"✓ Visitas: {self.metrics.visitas_creadas} creadas, "
                   f"{self.metrics.visitas_actualizadas} actualizadas, "
                   f"{self.metrics.visitas_descartadas} descartadas")
        logger.info(f"  - Con sede: {self.metrics.visitas_con_sede}")
        logger.info(f"  - Sin sede: {self.metrics.visitas_sin_sede}")
    
    def _find_institucion_for_visita(self, row: pd.Series) -> Optional[str]:
        """
        Encuentra UUID de institución para una visita.
        
        IMPORTANTE: Usamos la clave compuesta (identificacion + nombre) para encontrar
        la institución correcta, ya que puede haber instituciones con el mismo código
        pero diferente nombre.
        
        Orden de búsqueda:
          1. Clave compuesta: identificacion + nombre → institución exacta
          2. Fallback: Solo identificacion → primer resultado (si hay múltiples)
        """
        # Obtener identificacion y nombre de la fila MySQL
        identificacion = self._get_value(row, ['identificacion', 'uesvalle_ie_id', 'id_institucion'])
        nombre = self._get_value(row, ['nombreestablecimiento', 'nombreinstitucion', 'nombre_institucion', 'nombre', 'razonsocial'])
        
        if not identificacion or identificacion.upper() in ['NAN', 'NONE', '']:
            return None
        
        # 1. Buscar por clave compuesta (identificacion + nombre)
        if nombre:
            key = self._make_inst_key(identificacion, nombre)
            uuid_found = self.dict_instituciones_by_key.get(key)
            if uuid_found:
                return uuid_found
        
        # 2. Fallback: buscar solo por identificacion (retorna el primero si hay múltiples)
        uuids_by_uesvalle = self.dict_instituciones_by_uesvalle.get(identificacion.strip())
        if uuids_by_uesvalle and len(uuids_by_uesvalle) > 0:
            if len(uuids_by_uesvalle) > 1:
                logger.warning(f"⚠️ Múltiples instituciones con identificacion={identificacion}, usando la primera")
            return uuids_by_uesvalle[0]
        
        # 3. Fallback: intentar por codigodane
        codigodane = self._get_value(row, ['codigodane', 'codigo_dane', 'dane'])
        if codigodane and codigodane.upper() not in ['NAN', 'NONE', '']:
            uuids_by_dane = self.dict_instituciones_by_dane.get(codigodane.upper())
            if uuids_by_dane and len(uuids_by_dane) > 0:
                return uuids_by_dane[0]
        
        return None
    
    def _find_sede_for_visita(self, institucion_uuid: str, row: pd.Series) -> Optional[str]:
        """
        Encuentra UUID de sede para una visita.
        
        Estrategia:
          - Si hay codigodanesede en MySQL → buscar directamente
          - Si no, buscar sedes de la institución:
            - 1 sede → usar esa
            - múltiples sedes → usar la primera (o la principal)
            - 0 sedes → NULL
        """
        # Intentar por codigodanesede directo
        codigo_dane_sede = self._get_value(row, ['codigodanesede', 'codigo_dane_sede', 'dane_sede'])
        if codigo_dane_sede and codigo_dane_sede.upper() not in ['NAN', 'NONE', '']:
            uuid_found = self.dict_sedes_by_dane.get(codigo_dane_sede.upper())
            if uuid_found:
                return uuid_found
        
        # Buscar sedes de la institución
        sedes = self.dict_sedes_by_institucion.get(institucion_uuid, [])
        
        if len(sedes) == 1:
            return sedes[0]
        elif len(sedes) > 1:
            # Usar la primera (TODO: implementar lógica para sede principal)
            return sedes[0]
        
        return None
    
    def _prepare_visita_from_mysql(self, row: pd.Series, institucion_uuid: str, sede_uuid: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Prepara datos de visita desde MySQL.
        
        Validaciones críticas:
          - fechavisita OBLIGATORIO (descartar si no existe)
          - conceptovisita debe ser F/D/FCR (dejar NULL si inválido)
          - codigotipoobjeto debe ser INT (dejar NULL si no se puede convertir)
        """
        # Obtener y validar fechavisita (OBLIGATORIO)
        fechavisita = self._parse_date(self._get_value(row, ['fechavisita', 'fecha_visita', 'fecha']))
        
        if not fechavisita:
            logger.debug(f"Visita descartada: fechavisita no válida")
            self.metrics.visitas_descartadas += 1
            return None
        
        # Validar y limpiar conceptovisita
        conceptovisita = self._get_value(row, ['conceptovisita', 'concepto_visita', 'concepto'])
        if conceptovisita:
            conceptovisita = conceptovisita.upper().strip()
            if conceptovisita not in ['F', 'D', 'FCR']:
                logger.debug(f"conceptovisita '{conceptovisita}' inválido, dejando NULL")
                conceptovisita = None
        
        # Convertir codigotipoobjeto a INT
        codigotipoobjeto = self._parse_int(self._get_value(row, ['codigotipoobjeto', 'codigo_tipo_objeto']))
        
        # Convertir codigofuncionario a INT
        codigofuncionario = self._parse_int(self._get_value(row, ['codigofuncionario', 'codigo_funcionario']))
        
        # Programa para índice único
        programa = self._get_value(row, ['programa', 'nombre_programa'])
        
        # Campos extras que van en metadata
        cols_destino = ['fechavisita', 'conceptovisita', 'nombreactividad', 'codigotipoobjeto', 
                       'nombretipoobjeto', 'requerimientos', 'motivovisita', 'nombrefuncionario',
                       'apellidofuncionario', 'codigofuncionario', 'programa', 'resultado', 'observacion',
                       'identificacion', 'codigodane', 'codigodanesede']
        
        metadata = {'origen': 'mysql', 'fecha_sincronizacion': datetime.now().isoformat()}
        for col in row.index:
            if col.lower() not in [c.lower() for c in cols_destino]:
                val = row[col]
                if pd.notna(val):
                    if isinstance(val, (datetime, date)):
                        val = str(val)
                    metadata[col] = val
        
        return {
            'institucion_id': institucion_uuid,
            'sede_id': sede_uuid,
            'fechavisita': fechavisita,
            'nombreactividad': self._normalize_string(self._get_value(row, ['nombreactividad', 'nombre_actividad', 'actividad'])),
            'codigotipoobjeto': codigotipoobjeto,
            'nombretipoobjeto': self._normalize_string(self._get_value(row, ['nombretipoobjeto', 'nombre_tipo_objeto'])),
            'conceptovisita': conceptovisita,
            'requerimientos': self._normalize_string(self._get_value(row, ['requerimientos'])),
            'motivovisita': self._normalize_string(self._get_value(row, ['motivovisita', 'motivo_visita', 'motivo'])),
            'nombrefuncionario': self._normalize_string(self._get_value(row, ['nombrefuncionario', 'nombre_funcionario'])),
            'apellidofuncionario': self._normalize_string(self._get_value(row, ['apellidofuncionario', 'apellido_funcionario'])),
            'codigofuncionario': codigofuncionario,
            'programa': programa,
            'resultado': self._get_value(row, ['resultado']),
            'observacion': self._normalize_string(self._get_value(row, ['observacion', 'observaciones'])),
            'metadata': metadata
        }
    
    def _save_visitas_batch(self, batch: List[Dict[str, Any]]) -> None:
        """
        Guarda batch de visitas usando update_or_create para manejar duplicados.
        
        Índice único: (sede_id, fechavisita, programa)
        """
        for data in batch:
            try:
                # Buscar visita existente por índice único
                lookup = {
                    'sede_id': data['sede_id'],
                    'fechavisita': data['fechavisita'],
                    'programa': data.get('programa') or ''
                }
                
                defaults = {
                    'institucion_id': data['institucion_id'],
                    'nombreactividad': data.get('nombreactividad'),
                    'codigotipoobjeto': data.get('codigotipoobjeto'),
                    'nombretipoobjeto': data.get('nombretipoobjeto'),
                    'conceptovisita': data.get('conceptovisita'),
                    'requerimientos': data.get('requerimientos'),
                    'motivovisita': data.get('motivovisita'),
                    'nombrefuncionario': data.get('nombrefuncionario'),
                    'apellidofuncionario': data.get('apellidofuncionario'),
                    'codigofuncionario': data.get('codigofuncionario'),
                    'resultado': data.get('resultado'),
                    'observacion': data.get('observacion'),
                    'metadata': data.get('metadata', {})
                }
                
                obj, created = Visita.objects.update_or_create(
                    **lookup,
                    defaults=defaults
                )
                
                if created:
                    self.metrics.visitas_creadas += 1
                else:
                    self.metrics.visitas_actualizadas += 1
                    
            except Exception as e:
                logger.warning(f"❌ Error guardando visita: {e}")
                self.metrics.visitas_descartadas += 1
    
    # =========================================================================
    # UTILIDADES
    # =========================================================================
    
    def _get_value(self, row: pd.Series, columns: List[str]) -> Optional[str]:
        """Obtiene valor de la primera columna que exista."""
        for col in columns:
            if col in row.index:
                val = row[col]
                if pd.notna(val):
                    return str(val).strip()
        return None
    
    def _get_csv_value(self, row: pd.Series, column: str) -> Optional[str]:
        """Obtiene valor de CSV con normalización."""
        if column in row.index:
            val = row[column]
            if pd.notna(val):
                return str(val).strip()
        return None
    
    def _normalize_string(self, value: Optional[str]) -> Optional[str]:
        """Normaliza string: trim, sin caracteres especiales."""
        if not value:
            return None
        return value.strip()
    
    def _parse_coordinate(self, value: Optional[str]) -> Optional[float]:
        """Parsea coordenada a float."""
        if not value:
            return None
        try:
            # Reemplazar coma por punto
            return float(value.replace(',', '.'))
        except (ValueError, AttributeError):
            return None
    
    def _parse_date(self, value: Optional[str]) -> Optional[date]:
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
            return pd.to_datetime(value, errors='coerce').date()
        except:
            return None
    
    def _parse_int(self, value: Optional[str]) -> Optional[int]:
        """Parsea valor a INT."""
        if not value:
            return None
        try:
            # Eliminar decimales .0
            cleaned = str(value).replace('.0', '').strip()
            return int(float(cleaned))
        except (ValueError, TypeError):
            return None
