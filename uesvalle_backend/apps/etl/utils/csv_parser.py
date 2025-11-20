# etl/utils/csv_parser.py
import csv
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class RobustCSVParser:
    """
    Parser robusto que respeta EXACTAMENTE el delimitador `;`
    sin interpretar comas dentro de campos como separadores.
    """
    
    @staticmethod
    def parse_csv(file_path: str, delimiter=';', encoding='utf-8') -> pd.DataFrame:
        """
        Parsea CSV de forma segura sin confundir delimitadores internos.
        """
        try:
            rows = []
            headers = None
            
            with open(file_path, 'r', encoding=encoding) as f:
                # Lee línea por línea
                for line_num, line in enumerate(f, 1):
                    line = line.rstrip('\n\r')
                    
                    # Split SOLAMENTE por el delimitador
                    fields = line.split(delimiter)
                    
                    if line_num == 1:
                        headers = [h.strip() for h in fields]
                        logger.info(f"Headers: {len(headers)} columnas")
                        continue
                    
                    # Limpia espacios en cada campo
                    fields = [f.strip() for f in fields]
                    
                    # Ajusta cantidad de campos si es necesario
                    if len(fields) != len(headers):
                        logger.debug(f"Línea {line_num}: campos={len(fields)}, esperados={len(headers)}")
                        
                        # Si tiene menos, añade vacíos
                        if len(fields) < len(headers):
                            fields.extend([''] * (len(headers) - len(fields)))
                        # Si tiene más, trunca
                        elif len(fields) > len(headers):
                            fields = fields[:len(headers)]
                    
                    rows.append(fields)
            
            # Crea DataFrame
            df = pd.DataFrame(rows, columns=headers)
            
            logger.info(f"✅ Parseado correctamente: {len(df)} filas x {len(headers)} columnas")
            return df
        
        except Exception as e:
            logger.error(f"❌ Error parseando CSV: {str(e)}")
            raise
    
    @staticmethod
    def validate_coordinates(df: pd.DataFrame, lon_col='LONGITUD', lat_col='LATITUD') -> tuple:
        """
        Valida que las coordenadas se leyeron correctamente (con comas intactas).
        Retorna (válidas, inválidas, ejemplos)
        """
        valid_count = 0
        invalid_count = 0
        samples = []
        
        if lon_col not in df.columns or lat_col not in df.columns:
            logger.warning(f"Columnas de coordenadas {lon_col}, {lat_col} no encontradas")
            return 0, 0, []

        for idx, row in df.iterrows():
            lon_str = str(row.get(lon_col, ''))
            lat_str = str(row.get(lat_col, ''))
            
            # Verifica que tengan comas (formato regional)
            if ',' in lon_str and ',' in lat_str:
                valid_count += 1
                if len(samples) < 3:
                    samples.append(f"Fila {idx}: ({lon_str}, {lat_str})")
            else:
                invalid_count += 1
        
        logger.info(f"Validación de coordenadas: {valid_count} válidas, {invalid_count} inválidas")
        if samples:
            logger.info(f"Ejemplos: {samples}")
        
        return valid_count, invalid_count, samples
