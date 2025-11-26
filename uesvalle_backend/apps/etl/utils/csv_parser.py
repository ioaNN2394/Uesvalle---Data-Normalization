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
    def parse_csv(file_path: str, delimiter=';', encoding=None) -> pd.DataFrame:
        """
        Parsea CSV de forma segura intentando múltiples encodings.
        """
        encodings_to_try = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        if encoding:
            encodings_to_try.insert(0, encoding)
            
        last_error = None
        
        for enc in encodings_to_try:
            try:
                logger.info(f"Intentando leer CSV con encoding: {enc}")
                rows = []
                headers = None
                
                with open(file_path, 'r', encoding=enc) as f:
                    # Lee línea por línea
                    for line_num, line in enumerate(f, 1):
                        line = line.rstrip('\n\r')
                        
                        # Split SOLAMENTE por el delimitador
                        fields = line.split(delimiter)
                        
                        if line_num == 1:
                            # ⭐ LIMPIA headers: elimina espacios, BOM y pasa a mayúsculas
                            headers = [h.strip().upper() for h in fields]
                            # Validar que parezca un CSV válido (al menos 1 columna)
                            if not headers or (len(headers) == 1 and not headers[0]):
                                raise ValueError("CSV parece vacío o mal delimitado")
                            continue
                        
                        # Limpia espacios en cada campo
                        fields = [f.strip() for f in fields]
                        
                        # Ajusta cantidad de campos si es necesario
                        if len(fields) != len(headers):
                            # Si tiene menos, añade vacíos
                            if len(fields) < len(headers):
                                fields.extend([''] * (len(headers) - len(fields)))
                            # Si tiene más, recorta
                            else:
                                fields = fields[:len(headers)]
                        
                        rows.append(fields)
                
                # Si llegamos aquí, funcionó
                logger.info(f"✓ CSV leído exitosamente con {enc}")
                df = pd.DataFrame(rows, columns=headers)
                logger.info(f"✅ Parseado correctamente: {len(df)} filas x {len(headers)} columnas")
                return df
                
            except UnicodeDecodeError as e:
                logger.warning(f"Falló encoding {enc}: {e}")
                last_error = e
                continue
            except Exception as e:
                logger.warning(f"Error con encoding {enc}: {e}")
                last_error = e
                continue
        
        # Si fallan todos
        logger.error(f"❌ Error parseando CSV: {str(last_error)}")
        raise last_error or ValueError("No se pudo leer el CSV con ningún encoding estándar")
    
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
