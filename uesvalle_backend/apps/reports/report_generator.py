"""
Generador de reportes con soporte para Excel y PDF usando streaming.
- Usa SQL nativo con cursores para evitar ORM overhead
- Escribe datos en chunks directamente a archivos (no carga todo en RAM)
- Soporta múltiples formatos: Excel (.xlsx) y PDF
"""

import io
import os
from datetime import datetime
from typing import Optional, Dict, List, Any, Generator
from decimal import Decimal

import xlsxwriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from django.db import connection
from django.conf import settings


class ReportFilter:
    """Clase para encapsular los filtros del reporte."""
    
    def __init__(
        self,
        municipios: Optional[List[str]] = None,
        conceptos_visita: Optional[List[str]] = None,
        anios: Optional[List[int]] = None,
        instituciones: Optional[List[str]] = None,
        estados: Optional[List[str]] = None,
        tiene_pae: Optional[bool] = None,
    ):
        self.municipios = municipios or []
        self.conceptos_visita = conceptos_visita or []
        self.anios = anios or []
        self.instituciones = instituciones or []
        self.estados = estados or []
        self.tiene_pae = tiene_pae
        
    def has_filters(self) -> bool:
        """Verifica si hay al menos un filtro aplicado."""
        return bool(
            self.municipios or 
            self.conceptos_visita or 
            self.anios or 
            self.instituciones or 
            self.estados or 
            self.tiene_pae is not None
        )
    
    def get_where_clauses(self) -> tuple[List[str], List[Any]]:
        """
        Retorna (clauses, params) para construir la consulta SQL.
        
        Returns:
            tuple: (lista de cláusulas WHERE, lista de parámetros)
        """
        clauses = []
        params = []
        
        if self.municipios:
            placeholders = ','.join(['%s'] * len(self.municipios))
            clauses.append(f"i.codigo_municipio IN ({placeholders})")
            params.extend(self.municipios)
        
        if self.conceptos_visita:
            placeholders = ','.join(['%s'] * len(self.conceptos_visita))
            clauses.append(f"v.conceptovisita IN ({placeholders})")
            params.extend(self.conceptos_visita)
        
        if self.anios:
            placeholders = ','.join(['%s'] * len(self.anios))
            clauses.append(f"YEAR(v.fechavisita) IN ({placeholders})")
            params.extend(self.anios)
        
        if self.instituciones:
            placeholders = ','.join(['%s'] * len(self.instituciones))
            clauses.append(f"i.id IN ({placeholders})")
            params.extend(self.instituciones)
        
        if self.estados:
            placeholders = ','.join(['%s'] * len(self.estados))
            clauses.append(f"i.estado IN ({placeholders})")
            params.extend(self.estados)
        
        if self.tiene_pae is not None:
            if self.tiene_pae:
                clauses.append("v.metadata->>'tienepae' = 'S'")
            else:
                clauses.append("(v.metadata->>'tienepae' IS NULL OR v.metadata->>'tienepae' != 'S')")
        
        return clauses, params


class StreamingReportGenerator:
    """
    Generador de reportes con streaming para Excel y PDF.
    Diseñado para manejar grandes volúmenes de datos sin sobrecargar RAM.
    """
    
    # Configuración
    CHUNK_SIZE = 1000  # Traer 1000 registros a la vez de la BD
    
    def __init__(self):
        self.connection = connection
    
    def _build_query(self, filters: ReportFilter) -> tuple[str, List[Any]]:
        """
        Construye la consulta SQL base para reportes.
        
        Args:
            filters: Instancia de ReportFilter con los filtros aplicados
            
        Returns:
            tuple: (query, params)
        """
        base_query = """
        SELECT DISTINCT
            i.id,
            i.nombre as institucion_nombre,
            i.estado,
            dm.nombre as municipio_nombre,
            v.id as visita_id,
            v.fechavisita,
            v.conceptovisita,
            v.nombreactividad,
            v.motivovisita,
            v.metadata->>'tienepae' as tiene_pae
        FROM "uesvalle"."institucion" i
        LEFT JOIN "uesvalle"."visita" v ON i.id = v.institucion_id
        LEFT JOIN "uesvalle"."dim_municipio" dm ON i.codigo_municipio = dm.codigo_municipio
        """
        
        where_clauses, params = filters.get_where_clauses()
        
        if where_clauses:
            where_clause = " AND ".join(where_clauses)
            query = base_query + f" WHERE {where_clause}"
        else:
            query = base_query
        
        query += " ORDER BY i.nombre, v.fechavisita DESC"
        
        return query, params
    
    def _get_total_instituciones(self, filters: ReportFilter) -> int:
        """
        Obtiene el total de instituciones que coinciden con los filtros.
        """
        query = """
        SELECT COUNT(DISTINCT i.id)
        FROM "uesvalle"."institucion" i
        LEFT JOIN "uesvalle"."visita" v ON i.id = v.institucion_id
        LEFT JOIN "uesvalle"."dim_municipio" dm ON i.codigo_municipio = dm.codigo_municipio
        """
        
        where_clauses, params = filters.get_where_clauses()
        
        if where_clauses:
            where_clause = " AND ".join(where_clauses)
            query += f" WHERE {where_clause}"
        
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def stream_data(self, filters: ReportFilter) -> Generator[List[Dict[str, Any]], None, None]:
        """
        Generador que trae datos en chunks desde la BD sin cargar todo en RAM.
        
        Args:
            filters: Instancia de ReportFilter
            
        Yields:
            Lista de diccionarios con datos (máximo CHUNK_SIZE registros)
        """
        query, params = self._build_query(filters)
        
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            
            # Obtener nombres de columnas
            columns = [col[0] for col in cursor.description]
            
            while True:
                rows = cursor.fetchmany(self.CHUNK_SIZE)
                if not rows:
                    break
                
                chunk = [
                    {columns[i]: value for i, value in enumerate(row)}
                    for row in rows
                ]
                
                yield chunk
    
    def generate_excel(
        self,
        filters: ReportFilter,
        output_path: str,
        filename: str = "reporte.xlsx"
    ) -> str:
        """
        Genera un reporte en Excel usando xlsxwriter con memoria constante.
        
        Args:
            filters: Instancia de ReportFilter
            output_path: Ruta donde guardar el archivo
            filename: Nombre del archivo
            
        Returns:
            str: Ruta completa del archivo generado
        """
        os.makedirs(output_path, exist_ok=True)
        full_path = os.path.join(output_path, filename)
        
        # Crear workbook
        workbook = xlsxwriter.Workbook(full_path, {'constant_memory': True})
        worksheet = workbook.add_worksheet('Instituciones')
        
        # Definir formatos
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#366092',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        data_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'top'
        })
        
        date_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'num_format': 'yyyy-mm-dd'
        })
        
        # Encabezados
        headers = [
            'ID Institución',
            'Nombre Institución',
            'Municipio',
            'Estado',
            'Fecha Visita',
            'Concepto Visita',
            'Actividad',
            'Motivo',
            'Tiene PAE'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Configurar ancho de columnas
        worksheet.set_column('A:A', 36)  # ID Institución
        worksheet.set_column('B:B', 30)  # Nombre Institución
        worksheet.set_column('C:C', 20)  # Municipio
        worksheet.set_column('D:D', 15)  # Estado
        worksheet.set_column('E:E', 12)  # Fecha
        worksheet.set_column('F:F', 18)  # Concepto
        worksheet.set_column('G:G', 30)  # Actividad
        worksheet.set_column('H:H', 30)  # Motivo
        worksheet.set_column('I:I', 12)  # PAE
        
        # Escribir datos en chunks
        row = 1
        for chunk in self.stream_data(filters):
            for data in chunk:
                worksheet.write(row, 0, str(data.get('id', '')), data_format)
                worksheet.write(row, 1, str(data.get('institucion_nombre', '')), data_format)
                worksheet.write(row, 2, str(data.get('municipio_nombre', '') or ''), data_format)
                worksheet.write(row, 3, str(data.get('estado', '')), data_format)
                
                # Fecha
                fecha = data.get('fechavisita')
                if fecha:
                    worksheet.write(row, 4, fecha, date_format)
                else:
                    worksheet.write(row, 4, '', data_format)
                
                worksheet.write(row, 5, str(data.get('conceptovisita', '')), data_format)
                worksheet.write(row, 6, str(data.get('nombreactividad', '') or ''), data_format)
                worksheet.write(row, 7, str(data.get('motivovisita', '') or ''), data_format)
                
                # PAE
                tiene_pae = data.get('tiene_pae', '')
                worksheet.write(row, 8, 'Sí' if tiene_pae == 'S' else ('No' if tiene_pae else ''), data_format)
                
                row += 1
        
        # Congelar primera fila
        worksheet.freeze_panes(1, 0)
        
        # Agregar metadata al final
        worksheet.write(row + 2, 0, f"Total registros: {row - 1}")
        worksheet.write(row + 3, 0, f"Fecha generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        worksheet.write(row + 4, 0, f"Filtros aplicados: {self._format_filters(filters)}")
        
        workbook.close()
        
        return full_path
    
    def generate_pdf(
        self,
        filters: ReportFilter,
        output_path: str,
        filename: str = "reporte.pdf"
    ) -> str:
        """
        Genera un reporte en PDF usando reportlab.
        Crea una tabla con los datos sin cargar todo en RAM.
        
        Args:
            filters: Instancia de ReportFilter
            output_path: Ruta donde guardar el archivo
            filename: Nombre del archivo
            
        Returns:
            str: Ruta completa del archivo generado
        """
        os.makedirs(output_path, exist_ok=True)
        full_path = os.path.join(output_path, filename)
        
        # Crear documento
        doc = SimpleDocTemplate(
            full_path,
            pagesize=A4,
            leftMargin=0.5 * inch,
            rightMargin=0.5 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch
        )
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=14,
            textColor=colors.HexColor('#366092'),
            spaceAfter=30
        )
        
        elements = []
        
        # Título
        title = Paragraph(
            "Reporte de Instituciones Educativas",
            title_style
        )
        elements.append(title)
        
        # Información de filtros
        filters_info = self._format_filters(filters)
        filters_text = Paragraph(
            f"<b>Filtros aplicados:</b> {filters_info if filters_info else 'Ninguno (Reporte General)'}",
            styles['Normal']
        )
        elements.append(filters_text)
        elements.append(Spacer(1, 12))
        
        # Encabezados de tabla
        headers = [
            'Institución',
            'Municipio',
            'Estado',
            'Fecha Visita',
            'Concepto',
            'Tiene PAE'
        ]
        
        # Traer datos y construir tabla en chunks
        table_data = [headers]
        row_count = 0
        
        for chunk in self.stream_data(filters):
            for data in chunk:
                table_row = [
                    str(data.get('institucion_nombre', ''))[:40],  # Truncar nombre largo
                    str(data.get('municipio_nombre', '') or ''),
                    str(data.get('estado', '')),
                    str(data.get('fechavisita', '') or ''),
                    str(data.get('conceptovisita', '')),
                    'Sí' if data.get('tiene_pae') == 'S' else 'No' if data.get('tiene_pae') else ''
                ]
                table_data.append(table_row)
                row_count += 1
                
                # Si la tabla es muy grande, crear múltiples PDFs o hacer página nueva
                if len(table_data) > 25:  # 25 filas + header = nueva tabla
                    table = Table(table_data)
                    table.setStyle(self._get_table_style())
                    elements.append(table)
                    elements.append(PageBreak())
                    table_data = [headers]  # Reset headers
        
        # Agregar última tabla si hay datos
        if len(table_data) > 1:
            table = Table(table_data)
            table.setStyle(self._get_table_style())
            elements.append(table)
        
        # Información final
        elements.append(Spacer(1, 20))
        footer_text = Paragraph(
            f"<b>Total registros:</b> {row_count} | "
            f"<b>Fecha:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            styles['Normal']
        )
        elements.append(footer_text)
        
        # Construir PDF
        doc.build(elements)
        
        return full_path
    
    def _get_table_style(self) -> TableStyle:
        """Retorna el estilo para las tablas PDF."""
        return TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')])
        ])
    
    def _format_filters(self, filters: ReportFilter) -> str:
        """Formatea los filtros para mostrar en el reporte."""
        filter_parts = []
        
        if filters.municipios:
            filter_parts.append(f"Municipios: {', '.join(filters.municipios)}")
        
        if filters.conceptos_visita:
            filter_parts.append(f"Conceptos: {', '.join(filters.conceptos_visita)}")
        
        if filters.anios:
            filter_parts.append(f"Años: {', '.join(map(str, filters.anios))}")
        
        if filters.instituciones:
            filter_parts.append(f"Instituciones: {len(filters.instituciones)} seleccionadas")
        
        if filters.estados:
            filter_parts.append(f"Estados: {', '.join(filters.estados)}")
        
        if filters.tiene_pae is not None:
            pae_text = "Con PAE" if filters.tiene_pae else "Sin PAE"
            filter_parts.append(f"PAE: {pae_text}")
        
        return " | ".join(filter_parts) if filter_parts else ""
