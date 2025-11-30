# apps/etl/utils/validators.py
import logging

logger = logging.getLogger(__name__)

class DepartmentValidator:
    """
    Validador para asegurar que solo se procesen instituciones
    del departamento del Valle del Cauca.
    """
    
    # Nombres exactos del Valle del Cauca (NO incluir "CAUCA" solo)
    VALLE_CAUCA_NAMES = {
        'VALLE DEL CAUCA',
        'VALLEDELCAUCA',
        'VALLE-DEL-CAUCA',
        'DEPARTAMENTO VALLE DEL CAUCA',
        'DEPARTAMENTO DEL VALLE DEL CAUCA'
    }
    
    # Código DANE del Valle del Cauca
    VALLE_CAUCA_CODES = {'76', '05076'}
    
    # Códigos a RECHAZAR (otros departamentos)
    # Basado en códigos DANE de departamentos de Colombia
    REJECTED_CODES = {
        '05',   # Antioquia
        '08',   # Atlántico
        '11',   # Bogotá D.C.
        '13',   # Bolívar
        '15',   # Boyacá
        '17',   # Caldas
        '18',   # Caquetá
        '19',   # Cauca (⭐ Este es el problema común)
        '20',   # Cesar
        '23',   # Córdoba
        '25',   # Cundinamarca
        '27',   # Guaviare
        '41',   # Huila
        '44',   # La Guajira
        '47',   # Magdalena
        '50',   # Meta
        '52',   # Nariño
        '54',   # Norte de Santander
        '63',   # Quindío
        '66',   # Risaralda
        '68',   # Santander
        '70',   # Sucre
        '73',   # Tolima
        '91',   # Amazonas
        '94',   # Arauca
        '97',   # Putumayo
        '99',   # Vaupés
        '00',   # Archipiélago de San Andrés
    }
    
    @staticmethod
    def is_valle_cauca(department_name: str, department_code: str = None) -> bool:
        """
        Verifica si una institución pertenece al Valle del Cauca.
        
        ⭐ IMPORTANTE: Rechaza proactivamente otros departamentos
        
        Args:
            department_name: Nombre del departamento (ej: "VALLE DEL CAUCA")
            department_code: Código DANE del departamento (ej: "76")
        
        Returns:
            bool: True si es Valle del Cauca, False si no
        """
        
        # ⭐ PRIMERO: Rechaza si el código es de otro departamento
        if department_code:
            code_str = str(department_code).strip()
            
            # Si el código está en la lista de rechazados, rechaza
            if code_str in DepartmentValidator.REJECTED_CODES:
                logger.debug(f"✗ Rechazado por código: {code_str} (departamento no es Valle del Cauca)")
                return False
            
            # Si el código es exactamente 76 o 05076, acepta
            if code_str in DepartmentValidator.VALLE_CAUCA_CODES:
                logger.debug(f"✓ Aceptado por código: {code_str}")
                return True
        
        # Normaliza nombre para comparación
        if department_name:
            dept_normalized = department_name.strip().upper()
            # Elimina caracteres especiales
            dept_normalized = dept_normalized.replace(' ', '').replace('-', '')
            
            # ⭐ RECHAZA si queda vacío después de normalizar
            if not dept_normalized:
                logger.debug(f"✗ Rechazado: Nombre vacío después de normalizar")
                return False
            
            # ⭐ RECHAZA "CAUCA" solo (es Cauca, no Valle del Cauca)
            if dept_normalized == 'CAUCA':
                logger.debug(f"✗ Rechazado: 'CAUCA' solo (ese es el departamento de Cauca, no Valle del Cauca)")
                return False
            
            # ⭐ RECHAZA otros departamentos conocidos
            if dept_normalized in ['ANTIOQUIA', 'ATLANTICO', 'BOLIVAR', 'BOYACA', 'CALDAS', 'CAQUETA',
                                   'CESAR', 'CORDOBA', 'CUNDINAMARCA', 'GUAVIARE', 'HUILA', 'LAGUAJIRA',
                                   'MAGDALENA', 'META', 'NARINO', 'NORTESANTANDER', 'QUINDIO', 'RISARALDA',
                                   'SANTANDER', 'SUCRE', 'TOLIMA', 'AMAZONAS', 'ARAUCA', 'PUTUMAYO', 'VAUPES']:
                logger.debug(f"✗ Rechazado: {department_name} (otro departamento)")
                return False
            
            # ⭐ ACEPTA si contiene "VALLEDELCAUCA"
            for valid_name in DepartmentValidator.VALLE_CAUCA_NAMES:
                valid_normalized = valid_name.replace(' ', '').replace('-', '')
                if valid_normalized in dept_normalized or dept_normalized in valid_normalized:
                    logger.debug(f"✓ Aceptado por nombre: {department_name}")
                    return True
        
        logger.debug(f"✗ Rechazado: Nombre='{department_name}', Código='{department_code}'")
        return False
    
    @staticmethod
    def filter_dataframe(df, department_column: str) -> tuple:
        """
        Filtra un DataFrame para mantener solo registros del Valle del Cauca.
        
        Args:
            df: DataFrame de pandas
            department_column: Nombre de la columna con el departamento
        
        Returns:
            tuple: (df_filtered, rows_removed, rows_kept)
        """
        if department_column not in df.columns:
            logger.warning(f"Columna de departamento no encontrada: {department_column}")
            return df, 0, len(df)
        
        initial_count = len(df)
        
        # Filtra por departamento
        mask = df[department_column].apply(
            lambda x: DepartmentValidator.is_valle_cauca(str(x) if x else '')
        )
        
        df_filtered = df[mask].copy()
        rows_removed = initial_count - len(df_filtered)
        rows_kept = len(df_filtered)
        
        logger.info(f"Filtrado por departamento: {rows_kept} conservadas, {rows_removed} removidas")
        
        return df_filtered, rows_removed, rows_kept


class VisitaValidator:
    """
    Validador para datos de visitas según FASE 6 del instructivo.
    
    Validaciones:
      - institucion_id: OBLIGATORIO (FK)
      - sede_id: OPCIONAL (puede ser NULL)
      - fechavisita: Formato DATE válido, OBLIGATORIO
      - conceptovisita: Si existe, debe ser F/D/FCR
      - codigotipoobjeto: Si existe, debe ser INT válido
      - codigofuncionario: Si existe, debe ser INT válido
      - nombreactividad, nombrefuncionario, apellidofuncionario: Strings normalizados
    """
    
    # Valores válidos para conceptovisita
    CONCEPTO_VALIDOS = {'F', 'D', 'FCR'}
    
    @staticmethod
    def validate_conceptovisita(value: str) -> tuple:
        """
        Valida que conceptovisita sea F, D o FCR.
        
        Args:
            value: Valor a validar
        
        Returns:
            tuple: (es_valido: bool, valor_normalizado: str o None, mensaje_error: str o None)
        """
        if not value:
            return True, None, None  # NULL es válido
        
        normalized = str(value).upper().strip()
        
        if normalized in VisitaValidator.CONCEPTO_VALIDOS:
            return True, normalized, None
        
        return False, None, f"Valor '{value}' no válido. Debe ser F, D o FCR"
    
    @staticmethod
    def validate_fechavisita(value) -> tuple:
        """
        Valida que fechavisita sea una fecha válida.
        
        Args:
            value: Valor de fecha (string, datetime, date)
        
        Returns:
            tuple: (es_valido: bool, fecha_normalizada: date o None, mensaje_error: str o None)
        """
        if not value:
            return False, None, "fechavisita es obligatorio"
        
        try:
            import pandas as pd
            from datetime import date, datetime
            
            if isinstance(value, datetime):
                return True, value.date(), None
            
            if isinstance(value, date):
                return True, value, None
            
            # Intentar parsear string
            parsed = pd.to_datetime(value, errors='coerce')
            if pd.isna(parsed):
                return False, None, f"Formato de fecha no reconocido: {value}"
            
            return True, parsed.date(), None
            
        except Exception as e:
            return False, None, f"Error parseando fecha: {str(e)}"
    
    @staticmethod
    def validate_codigo_int(value, campo_nombre: str) -> tuple:
        """
        Valida que un código sea convertible a INT.
        
        Args:
            value: Valor a validar
            campo_nombre: Nombre del campo para mensajes de error
        
        Returns:
            tuple: (es_valido: bool, valor_int: int o None, mensaje_error: str o None)
        """
        if not value:
            return True, None, None  # NULL es válido
        
        try:
            # Eliminar decimales .0 comunes
            cleaned = str(value).replace('.0', '').strip()
            if cleaned.lower() in ['nan', 'none', '']:
                return True, None, None
            
            int_val = int(float(cleaned))
            return True, int_val, None
            
        except (ValueError, TypeError) as e:
            return False, None, f"{campo_nombre} '{value}' no es un entero válido"
    
    @staticmethod
    def validate_dane_ie_id(value: str) -> tuple:
        """
        Valida código DANE de institución (11 dígitos numéricos).
        
        Args:
            value: Código DANE a validar
        
        Returns:
            tuple: (es_valido: bool, valor_normalizado: str o None, mensaje_error: str o None)
        """
        if not value:
            return True, None, None  # NULL es válido
        
        cleaned = str(value).strip().replace('.0', '')
        
        if not cleaned:
            return True, None, None
        
        # Verificar que sea numérico
        if not cleaned.isdigit():
            return False, None, f"DANE '{value}' debe ser numérico"
        
        # Verificar longitud (generalmente 11 dígitos)
        if len(cleaned) < 10 or len(cleaned) > 12:
            logger.warning(f"DANE '{cleaned}' tiene longitud inusual: {len(cleaned)} dígitos")
        
        return True, cleaned, None
    
    @staticmethod
    def normalize_string(value: str, max_length: int = None) -> str:
        """
        Normaliza string: trim, elimina caracteres problemáticos.
        
        Args:
            value: String a normalizar
            max_length: Longitud máxima (opcional)
        
        Returns:
            str: String normalizado o None si estaba vacío
        """
        if not value:
            return None
        
        normalized = str(value).strip()
        
        if not normalized or normalized.lower() in ['nan', 'none']:
            return None
        
        if max_length and len(normalized) > max_length:
            normalized = normalized[:max_length]
        
        return normalized
    
    @classmethod
    def validate_visita(cls, data: dict) -> tuple:
        """
        Valida un registro de visita completo.
        
        Args:
            data: Diccionario con datos de la visita
        
        Returns:
            tuple: (es_valido: bool, data_normalizado: dict, errores: list)
        """
        errores = []
        data_norm = data.copy()
        
        # 1. Validar institucion_id (OBLIGATORIO)
        if not data.get('institucion_id'):
            errores.append("institucion_id es obligatorio")
        
        # 2. Validar fechavisita (OBLIGATORIO)
        valid, fecha_norm, error = cls.validate_fechavisita(data.get('fechavisita'))
        if not valid:
            errores.append(error)
        else:
            data_norm['fechavisita'] = fecha_norm
        
        # 3. Validar conceptovisita (OPCIONAL, pero si existe debe ser F/D/FCR)
        valid, concepto_norm, error = cls.validate_conceptovisita(data.get('conceptovisita'))
        if not valid:
            logger.warning(f"⚠️ {error} - dejando NULL")
            data_norm['conceptovisita'] = None
        else:
            data_norm['conceptovisita'] = concepto_norm
        
        # 4. Validar codigotipoobjeto (OPCIONAL, debe ser INT)
        valid, codigo_norm, error = cls.validate_codigo_int(
            data.get('codigotipoobjeto'), 'codigotipoobjeto'
        )
        if not valid:
            logger.debug(f"⚠️ {error} - dejando NULL")
            data_norm['codigotipoobjeto'] = None
        else:
            data_norm['codigotipoobjeto'] = codigo_norm
        
        # 5. Validar codigofuncionario (OPCIONAL, debe ser INT)
        valid, codigo_norm, error = cls.validate_codigo_int(
            data.get('codigofuncionario'), 'codigofuncionario'
        )
        if not valid:
            logger.debug(f"⚠️ {error} - dejando NULL")
            data_norm['codigofuncionario'] = None
        else:
            data_norm['codigofuncionario'] = codigo_norm
        
        # 6. Normalizar strings
        for campo in ['nombreactividad', 'nombretipoobjeto', 'requerimientos', 
                      'motivovisita', 'nombrefuncionario', 'apellidofuncionario',
                      'programa', 'resultado', 'observacion']:
            data_norm[campo] = cls.normalize_string(data.get(campo))
        
        # Determinar si es válido (errores críticos = institucion_id y fechavisita)
        es_valido = len(errores) == 0
        
        return es_valido, data_norm, errores