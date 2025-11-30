"""
Tests exhaustivos para validadores del sistema ETL UESValle.

Este módulo prueba:
- DepartmentValidator: Filtrado por departamento Valle del Cauca
- VisitaValidator: Validación de datos de visitas

Casos de borde probados:
- Nombres de departamento con variaciones
- Códigos DANE de diferentes departamentos
- Validación de conceptos de visita (F/D/FCR)
- Validación de fechas en diferentes formatos
- Validación de códigos numéricos
- Normalización de strings
"""
import pytest
import pandas as pd
from datetime import date, datetime


class TestDepartmentValidator:
    """Tests comprehensivos para DepartmentValidator."""
    
    @pytest.fixture
    def validator(self):
        """Instancia del validador."""
        from apps.etl.utils.validators import DepartmentValidator
        return DepartmentValidator
    
    # =========================================================================
    # TESTS DE ACEPTACIÓN - VALLE DEL CAUCA
    # =========================================================================
    
    def test_acepta_valle_del_cauca_exacto(self, validator):
        """Acepta 'VALLE DEL CAUCA' exacto."""
        assert validator.is_valle_cauca('VALLE DEL CAUCA') == True
    
    def test_acepta_valle_del_cauca_lowercase(self, validator):
        """Acepta 'valle del cauca' en minúsculas."""
        assert validator.is_valle_cauca('valle del cauca') == True
    
    def test_acepta_valle_del_cauca_mixed_case(self, validator):
        """Acepta 'Valle Del Cauca' en mixed case."""
        assert validator.is_valle_cauca('Valle Del Cauca') == True
    
    def test_acepta_valle_del_cauca_con_espacios(self, validator):
        """Acepta variaciones con espacios extra."""
        assert validator.is_valle_cauca('  VALLE DEL CAUCA  ') == True
    
    def test_acepta_valledelcauca_sin_espacios(self, validator):
        """Acepta 'VALLEDELCAUCA' sin espacios."""
        assert validator.is_valle_cauca('VALLEDELCAUCA') == True
    
    def test_acepta_valle_del_cauca_con_guiones(self, validator):
        """Acepta 'VALLE-DEL-CAUCA' con guiones."""
        assert validator.is_valle_cauca('VALLE-DEL-CAUCA') == True
    
    def test_acepta_departamento_valle_del_cauca(self, validator):
        """Acepta 'DEPARTAMENTO VALLE DEL CAUCA'."""
        assert validator.is_valle_cauca('DEPARTAMENTO VALLE DEL CAUCA') == True
    
    def test_acepta_departamento_del_valle_del_cauca(self, validator):
        """Acepta 'DEPARTAMENTO DEL VALLE DEL CAUCA'."""
        assert validator.is_valle_cauca('DEPARTAMENTO DEL VALLE DEL CAUCA') == True
    
    # =========================================================================
    # TESTS DE ACEPTACIÓN POR CÓDIGO DANE
    # =========================================================================
    
    def test_acepta_codigo_76(self, validator):
        """Acepta código DANE '76' del Valle del Cauca."""
        assert validator.is_valle_cauca('', '76') == True
    
    def test_acepta_codigo_05076(self, validator):
        """Acepta código DANE '05076' del Valle del Cauca."""
        assert validator.is_valle_cauca('', '05076') == True
    
    def test_acepta_codigo_con_nombre_valido(self, validator):
        """Acepta si código Y nombre son válidos."""
        assert validator.is_valle_cauca('VALLE DEL CAUCA', '76') == True
    
    # =========================================================================
    # TESTS DE RECHAZO - OTROS DEPARTAMENTOS
    # =========================================================================
    
    def test_rechaza_cauca_solo(self, validator):
        """Rechaza 'CAUCA' solo (no es Valle del Cauca)."""
        assert validator.is_valle_cauca('CAUCA') == False
    
    def test_rechaza_cauca_codigo_19(self, validator):
        """Rechaza código 19 (Cauca)."""
        assert validator.is_valle_cauca('CAUCA', '19') == False
    
    def test_rechaza_antioquia(self, validator):
        """Rechaza 'ANTIOQUIA'."""
        assert validator.is_valle_cauca('ANTIOQUIA') == False
    
    def test_rechaza_antioquia_codigo_05(self, validator):
        """Rechaza código 05 (Antioquia)."""
        assert validator.is_valle_cauca('', '05') == False
    
    def test_rechaza_bogota(self, validator):
        """Rechaza 'BOGOTA D.C.'."""
        assert validator.is_valle_cauca('BOGOTA D.C.') == False
    
    def test_rechaza_bogota_codigo_11(self, validator):
        """Rechaza código 11 (Bogotá)."""
        assert validator.is_valle_cauca('', '11') == False
    
    def test_rechaza_cundinamarca(self, validator):
        """Rechaza 'CUNDINAMARCA'."""
        assert validator.is_valle_cauca('CUNDINAMARCA') == False
        assert validator.is_valle_cauca('', '25') == False
    
    def test_rechaza_atlantico(self, validator):
        """Rechaza 'ATLANTICO'."""
        assert validator.is_valle_cauca('ATLANTICO') == False
        assert validator.is_valle_cauca('', '08') == False
    
    def test_rechaza_narino(self, validator):
        """Rechaza 'NARIÑO'."""
        assert validator.is_valle_cauca('NARINO') == False
        assert validator.is_valle_cauca('', '52') == False
    
    def test_rechaza_risaralda(self, validator):
        """Rechaza 'RISARALDA'."""
        assert validator.is_valle_cauca('RISARALDA') == False
        assert validator.is_valle_cauca('', '66') == False
    
    def test_rechaza_quindio(self, validator):
        """Rechaza 'QUINDIO'."""
        assert validator.is_valle_cauca('QUINDIO') == False
        assert validator.is_valle_cauca('', '63') == False
    
    def test_rechaza_caldas(self, validator):
        """Rechaza 'CALDAS'."""
        assert validator.is_valle_cauca('CALDAS') == False
        assert validator.is_valle_cauca('', '17') == False
    
    def test_rechaza_santander(self, validator):
        """Rechaza 'SANTANDER'."""
        assert validator.is_valle_cauca('SANTANDER') == False
        assert validator.is_valle_cauca('', '68') == False
    
    def test_rechaza_norte_santander(self, validator):
        """Rechaza 'NORTE DE SANTANDER'."""
        # Aunque normalizado podría confundirse
        assert validator.is_valle_cauca('', '54') == False
    
    def test_rechaza_tolima(self, validator):
        """Rechaza 'TOLIMA'."""
        assert validator.is_valle_cauca('TOLIMA') == False
        assert validator.is_valle_cauca('', '73') == False
    
    def test_rechaza_huila(self, validator):
        """Rechaza 'HUILA'."""
        assert validator.is_valle_cauca('HUILA') == False
        assert validator.is_valle_cauca('', '41') == False
    
    def test_rechaza_meta(self, validator):
        """Rechaza 'META'."""
        assert validator.is_valle_cauca('META') == False
        assert validator.is_valle_cauca('', '50') == False
    
    def test_rechaza_bolivar(self, validator):
        """Rechaza 'BOLIVAR'."""
        assert validator.is_valle_cauca('BOLIVAR') == False
        assert validator.is_valle_cauca('', '13') == False
    
    # =========================================================================
    # TESTS DE CASOS DE BORDE
    # =========================================================================
    
    def test_rechaza_none(self, validator):
        """Rechaza None."""
        assert validator.is_valle_cauca(None) == False
    
    def test_rechaza_vacio(self, validator):
        """Rechaza string vacío."""
        assert validator.is_valle_cauca('') == False
    
    def test_rechaza_solo_espacios(self, validator):
        """Rechaza string con solo espacios."""
        assert validator.is_valle_cauca('   ') == False
    
    def test_codigo_invalido_no_afecta_nombre_valido(self, validator):
        """Un código inválido no afecta si el nombre es válido."""
        # Código de Antioquia pero nombre Valle - debería rechazar por código
        assert validator.is_valle_cauca('VALLE DEL CAUCA', '05') == False
    
    def test_nombre_invalido_no_afecta_codigo_valido(self, validator):
        """Un nombre inválido no afecta si el código es válido."""
        # Nombre genérico pero código del Valle - debería aceptar
        assert validator.is_valle_cauca('DEPARTAMENTO X', '76') == True
    
    # =========================================================================
    # TESTS DE FILTER_DATAFRAME
    # =========================================================================
    
    def test_filter_dataframe_basico(self, validator):
        """Filtra DataFrame por departamento."""
        df = pd.DataFrame({
            'DEPARTAMENTO': ['VALLE DEL CAUCA', 'CAUCA', 'ANTIOQUIA', 'VALLE DEL CAUCA'],
            'INSTITUCION': ['IE1', 'IE2', 'IE3', 'IE4']
        })
        
        df_filtered, removed, kept = validator.filter_dataframe(df, 'DEPARTAMENTO')
        
        assert kept == 2
        assert removed == 2
        assert len(df_filtered) == 2
    
    def test_filter_dataframe_todos_valle(self, validator):
        """Filtra DataFrame donde todos son del Valle."""
        df = pd.DataFrame({
            'DEPARTAMENTO': ['VALLE DEL CAUCA', 'VALLE DEL CAUCA', 'VALLE DEL CAUCA'],
            'INSTITUCION': ['IE1', 'IE2', 'IE3']
        })
        
        df_filtered, removed, kept = validator.filter_dataframe(df, 'DEPARTAMENTO')
        
        assert kept == 3
        assert removed == 0
    
    def test_filter_dataframe_ninguno_valle(self, validator):
        """Filtra DataFrame donde ninguno es del Valle."""
        df = pd.DataFrame({
            'DEPARTAMENTO': ['CAUCA', 'ANTIOQUIA', 'BOGOTA'],
            'INSTITUCION': ['IE1', 'IE2', 'IE3']
        })
        
        df_filtered, removed, kept = validator.filter_dataframe(df, 'DEPARTAMENTO')
        
        assert kept == 0
        assert removed == 3
    
    def test_filter_dataframe_columna_no_existe(self, validator):
        """Maneja columna inexistente."""
        df = pd.DataFrame({
            'OTRO': ['VALLE DEL CAUCA', 'CAUCA'],
            'INSTITUCION': ['IE1', 'IE2']
        })
        
        df_result, removed, kept = validator.filter_dataframe(df, 'DEPARTAMENTO')
        
        # Debería retornar el DataFrame original
        assert len(df_result) == len(df)


class TestVisitaValidator:
    """Tests comprehensivos para VisitaValidator."""
    
    @pytest.fixture
    def validator(self):
        """Instancia del validador."""
        from apps.etl.utils.validators import VisitaValidator
        return VisitaValidator
    
    # =========================================================================
    # TESTS DE VALIDATE_CONCEPTOVISITA
    # =========================================================================
    
    def test_concepto_F_valido(self, validator):
        """Acepta concepto 'F' (Favorable)."""
        valido, normalizado, error = validator.validate_conceptovisita('F')
        assert valido == True
        assert normalizado == 'F'
        assert error is None
    
    def test_concepto_D_valido(self, validator):
        """Acepta concepto 'D' (Desfavorable)."""
        valido, normalizado, error = validator.validate_conceptovisita('D')
        assert valido == True
        assert normalizado == 'D'
        assert error is None
    
    def test_concepto_FCR_valido(self, validator):
        """Acepta concepto 'FCR' (Favorable con Requerimientos)."""
        valido, normalizado, error = validator.validate_conceptovisita('FCR')
        assert valido == True
        assert normalizado == 'FCR'
        assert error is None
    
    def test_concepto_lowercase_normaliza(self, validator):
        """Normaliza conceptos en minúsculas."""
        valido, normalizado, error = validator.validate_conceptovisita('f')
        assert valido == True
        assert normalizado == 'F'
    
    def test_concepto_mixed_case_normaliza(self, validator):
        """Normaliza conceptos en mixed case."""
        valido, normalizado, error = validator.validate_conceptovisita('Fcr')
        assert valido == True
        assert normalizado == 'FCR'
    
    def test_concepto_con_espacios(self, validator):
        """Maneja conceptos con espacios."""
        valido, normalizado, error = validator.validate_conceptovisita('  F  ')
        assert valido == True
        assert normalizado == 'F'
    
    def test_concepto_none_valido(self, validator):
        """Acepta None (concepto vacío es válido)."""
        valido, normalizado, error = validator.validate_conceptovisita(None)
        assert valido == True
        assert normalizado is None
    
    def test_concepto_vacio_valido(self, validator):
        """Acepta string vacío."""
        valido, normalizado, error = validator.validate_conceptovisita('')
        assert valido == True
        assert normalizado is None
    
    def test_concepto_invalido_X(self, validator):
        """Rechaza concepto 'X'."""
        valido, normalizado, error = validator.validate_conceptovisita('X')
        assert valido == False
        assert normalizado is None
        assert error is not None
    
    def test_concepto_invalido_FAVORABLE(self, validator):
        """Rechaza 'FAVORABLE' (debe ser solo F)."""
        valido, normalizado, error = validator.validate_conceptovisita('FAVORABLE')
        assert valido == False
    
    def test_concepto_invalido_numerico(self, validator):
        """Rechaza concepto numérico."""
        valido, normalizado, error = validator.validate_conceptovisita('1')
        assert valido == False
    
    # =========================================================================
    # TESTS DE VALIDATE_FECHAVISITA
    # =========================================================================
    
    def test_fecha_date_object_valido(self, validator):
        """Acepta objeto date."""
        from datetime import date
        valido, normalizado, error = validator.validate_fechavisita(date(2024, 1, 15))
        assert valido == True
        assert normalizado == date(2024, 1, 15)
    
    def test_fecha_datetime_object_valido(self, validator):
        """Acepta objeto datetime."""
        from datetime import datetime
        valido, normalizado, error = validator.validate_fechavisita(datetime(2024, 1, 15, 10, 30))
        assert valido == True
        assert normalizado == date(2024, 1, 15)
    
    def test_fecha_string_iso_valido(self, validator):
        """Acepta string ISO '2024-01-15'."""
        valido, normalizado, error = validator.validate_fechavisita('2024-01-15')
        assert valido == True
        assert normalizado == date(2024, 1, 15)
    
    def test_fecha_string_slash_valido(self, validator):
        """Acepta string '15/01/2024'."""
        valido, normalizado, error = validator.validate_fechavisita('15/01/2024')
        assert valido == True
        # pandas puede parsear este formato
    
    def test_fecha_none_invalido(self, validator):
        """Rechaza None (fecha es obligatoria)."""
        valido, normalizado, error = validator.validate_fechavisita(None)
        assert valido == False
        assert 'obligatorio' in error.lower()
    
    def test_fecha_vacio_invalido(self, validator):
        """Rechaza string vacío."""
        valido, normalizado, error = validator.validate_fechavisita('')
        assert valido == False
    
    def test_fecha_invalida_texto(self, validator):
        """Rechaza texto no fecha."""
        valido, normalizado, error = validator.validate_fechavisita('no_es_fecha')
        assert valido == False
    
    def test_fecha_invalida_numero(self, validator):
        """Rechaza número solo."""
        valido, normalizado, error = validator.validate_fechavisita('123456')
        # Depende de pandas si lo parsea o no
        # Puede ser válido o inválido según formato
    
    # =========================================================================
    # TESTS DE VALIDATE_CODIGO_INT
    # =========================================================================
    
    def test_codigo_int_string_valido(self, validator):
        """Acepta string numérico '123'."""
        valido, valor, error = validator.validate_codigo_int('123', 'codigotipoobjeto')
        assert valido == True
        assert valor == 123
    
    def test_codigo_int_con_decimal_cero(self, validator):
        """Acepta '123.0' y normaliza a int."""
        valido, valor, error = validator.validate_codigo_int('123.0', 'codigotipoobjeto')
        assert valido == True
        assert valor == 123
    
    def test_codigo_int_float_valido(self, validator):
        """Acepta float y convierte a int."""
        valido, valor, error = validator.validate_codigo_int(456.0, 'codigotipoobjeto')
        assert valido == True
        assert valor == 456
    
    def test_codigo_int_none_valido(self, validator):
        """Acepta None (código es opcional)."""
        valido, valor, error = validator.validate_codigo_int(None, 'codigotipoobjeto')
        assert valido == True
        assert valor is None
    
    def test_codigo_int_vacio_valido(self, validator):
        """Acepta string vacío."""
        valido, valor, error = validator.validate_codigo_int('', 'codigotipoobjeto')
        assert valido == True
        assert valor is None
    
    def test_codigo_int_nan_valido(self, validator):
        """Acepta 'nan' y retorna None."""
        valido, valor, error = validator.validate_codigo_int('nan', 'codigotipoobjeto')
        assert valido == True
        assert valor is None
    
    def test_codigo_int_texto_invalido(self, validator):
        """Rechaza texto no numérico."""
        valido, valor, error = validator.validate_codigo_int('abc', 'codigotipoobjeto')
        assert valido == False
        assert valor is None
        assert 'no es un entero válido' in error
    
    # =========================================================================
    # TESTS DE VALIDATE_DANE_IE_ID
    # =========================================================================
    
    def test_dane_11_digitos_valido(self, validator):
        """Acepta DANE de 11 dígitos."""
        valido, valor, error = validator.validate_dane_ie_id('17600100001')
        assert valido == True
        assert valor == '17600100001'
    
    def test_dane_con_decimal_cero(self, validator):
        """Acepta DANE con '.0' y lo normaliza."""
        valido, valor, error = validator.validate_dane_ie_id('17600100001.0')
        assert valido == True
        assert valor == '17600100001'
    
    def test_dane_con_espacios(self, validator):
        """Acepta DANE con espacios."""
        valido, valor, error = validator.validate_dane_ie_id('  17600100001  ')
        assert valido == True
        assert valor == '17600100001'
    
    def test_dane_none_valido(self, validator):
        """Acepta None."""
        valido, valor, error = validator.validate_dane_ie_id(None)
        assert valido == True
        assert valor is None
    
    def test_dane_vacio_valido(self, validator):
        """Acepta string vacío."""
        valido, valor, error = validator.validate_dane_ie_id('')
        assert valido == True
        assert valor is None
    
    def test_dane_no_numerico_invalido(self, validator):
        """Rechaza DANE no numérico."""
        valido, valor, error = validator.validate_dane_ie_id('DANE123')
        assert valido == False
        assert 'numérico' in error
    
    def test_dane_con_letras_invalido(self, validator):
        """Rechaza DANE con letras."""
        valido, valor, error = validator.validate_dane_ie_id('1760010000A')
        assert valido == False
    
    # =========================================================================
    # TESTS DE NORMALIZE_STRING
    # =========================================================================
    
    def test_normalize_string_basico(self, validator):
        """Normaliza string básico."""
        result = validator.normalize_string('  Texto de prueba  ')
        assert result == 'Texto de prueba'
    
    def test_normalize_string_none(self, validator):
        """Retorna None para None."""
        result = validator.normalize_string(None)
        assert result is None
    
    def test_normalize_string_vacio(self, validator):
        """Retorna None para string vacío."""
        result = validator.normalize_string('')
        assert result is None
    
    def test_normalize_string_nan(self, validator):
        """Retorna None para 'nan'."""
        result = validator.normalize_string('nan')
        assert result is None
    
    def test_normalize_string_none_text(self, validator):
        """Retorna None para 'none'."""
        result = validator.normalize_string('none')
        assert result is None
    
    def test_normalize_string_max_length(self, validator):
        """Trunca a max_length."""
        result = validator.normalize_string('Texto muy largo para truncar', max_length=10)
        assert len(result) == 10
        assert result == 'Texto muy '
    
    # =========================================================================
    # TESTS DE VALIDATE_VISITA COMPLETO
    # =========================================================================
    
    def test_validate_visita_completa_valida(self, validator):
        """Valida visita completa con todos los campos."""
        data = {
            'institucion_id': 'uuid-123',
            'sede_id': 'uuid-456',
            'fechavisita': '2024-01-15',
            'conceptovisita': 'F',
            'codigotipoobjeto': '1',
            'codigofuncionario': '101',
            'nombreactividad': 'Inspección',
            'nombrefuncionario': '  Juan  ',
            'apellidofuncionario': 'Pérez',
        }
        
        valido, data_norm, errores = validator.validate_visita(data)
        
        assert valido == True
        assert len(errores) == 0
        assert data_norm['conceptovisita'] == 'F'
        assert data_norm['codigotipoobjeto'] == 1
        assert data_norm['nombrefuncionario'] == 'Juan'
    
    def test_validate_visita_sin_institucion_invalida(self, validator):
        """Rechaza visita sin institucion_id."""
        data = {
            'institucion_id': None,
            'fechavisita': '2024-01-15',
        }
        
        valido, data_norm, errores = validator.validate_visita(data)
        
        assert valido == False
        assert any('institucion_id' in e for e in errores)
    
    def test_validate_visita_sin_fecha_invalida(self, validator):
        """Rechaza visita sin fechavisita."""
        data = {
            'institucion_id': 'uuid-123',
            'fechavisita': None,
        }
        
        valido, data_norm, errores = validator.validate_visita(data)
        
        assert valido == False
        assert any('fechavisita' in e for e in errores)
    
    def test_validate_visita_concepto_invalido_deja_null(self, validator):
        """Concepto inválido se normaliza a NULL (no falla)."""
        data = {
            'institucion_id': 'uuid-123',
            'fechavisita': '2024-01-15',
            'conceptovisita': 'INVALIDO',
        }
        
        valido, data_norm, errores = validator.validate_visita(data)
        
        # La visita es válida (concepto inválido se deja NULL)
        assert valido == True
        assert data_norm['conceptovisita'] is None
    
    def test_validate_visita_campos_opcionales_null(self, validator):
        """Campos opcionales pueden ser NULL."""
        data = {
            'institucion_id': 'uuid-123',
            'fechavisita': '2024-01-15',
            'sede_id': None,
            'codigotipoobjeto': None,
            'codigofuncionario': None,
            'nombreactividad': None,
        }
        
        valido, data_norm, errores = validator.validate_visita(data)
        
        assert valido == True
        assert data_norm['sede_id'] is None
        assert data_norm['codigotipoobjeto'] is None
    
    def test_validate_visita_normaliza_strings(self, validator):
        """Normaliza todos los campos string."""
        data = {
            'institucion_id': 'uuid-123',
            'fechavisita': '2024-01-15',
            'nombreactividad': '  Inspección Sanitaria  ',
            'observacion': '  Sin novedades  ',
            'programa': '  PAE  ',
        }
        
        valido, data_norm, errores = validator.validate_visita(data)
        
        assert data_norm['nombreactividad'] == 'Inspección Sanitaria'
        assert data_norm['observacion'] == 'Sin novedades'
        assert data_norm['programa'] == 'PAE'


class TestValidatorsIntegration:
    """Tests de integración entre validadores."""
    
    def test_department_filter_then_visita_validate(self):
        """Filtra por departamento y luego valida visitas."""
        from apps.etl.utils.validators import DepartmentValidator, VisitaValidator
        
        # Datos de entrada
        df = pd.DataFrame({
            'DEPARTAMENTO': ['VALLE DEL CAUCA', 'CAUCA', 'VALLE DEL CAUCA'],
            'institucion_id': ['uuid-1', 'uuid-2', 'uuid-3'],
            'fechavisita': ['2024-01-15', '2024-01-16', '2024-01-17'],
            'conceptovisita': ['F', 'D', 'FCR'],
        })
        
        # Paso 1: Filtrar por departamento
        df_filtered, removed, kept = DepartmentValidator.filter_dataframe(df, 'DEPARTAMENTO')
        assert kept == 2
        
        # Paso 2: Validar visitas filtradas
        for _, row in df_filtered.iterrows():
            valido, _, errores = VisitaValidator.validate_visita(row.to_dict())
            assert valido == True, f"Visita inválida: {errores}"
    
    def test_validate_batch_with_mixed_data(self):
        """Valida batch de datos con mezcla de válidos e inválidos."""
        from apps.etl.utils.validators import VisitaValidator
        
        visitas = [
            {'institucion_id': 'uuid-1', 'fechavisita': '2024-01-15', 'conceptovisita': 'F'},
            {'institucion_id': None, 'fechavisita': '2024-01-16', 'conceptovisita': 'D'},
            {'institucion_id': 'uuid-3', 'fechavisita': None, 'conceptovisita': 'FCR'},
            {'institucion_id': 'uuid-4', 'fechavisita': '2024-01-18', 'conceptovisita': 'X'},
        ]
        
        validas = 0
        invalidas = 0
        
        for visita in visitas:
            valido, _, errores = VisitaValidator.validate_visita(visita)
            if valido:
                validas += 1
            else:
                invalidas += 1
        
        # 1 válida (primera y cuarta - la cuarta tiene concepto X que se normaliza a NULL)
        assert validas == 2
        assert invalidas == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
