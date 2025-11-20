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
