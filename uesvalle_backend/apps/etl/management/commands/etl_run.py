"""
Comando de management para ejecutar el pipeline ETL completo.
Uso: python manage.py etl_run --excel-a=ruta/a.xlsx --excel-b=ruta/b.xlsx
"""
import os
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from apps.etl.services import ETLOrchestrator


class Command(BaseCommand):
    help = 'Ejecuta el pipeline ETL completo (MySQL + Excel → Supabase)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--excel-a',
            type=str,
            help='Ruta al archivo Excel A (opcional)'
        )
        
        parser.add_argument(
            '--excel-b',
            type=str,
            help='Ruta al archivo Excel B (opcional)'
        )
        
        parser.add_argument(
            '--mysql-only',
            action='store_true',
            help='Ejecutar ETL solo con datos de MySQL'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Modo de prueba - no guarda datos'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('=== INICIANDO PIPELINE ETL UESVALLE ===')
        )
        
        # Validar argumentos
        excel_a_path = options.get('excel_a')
        excel_b_path = options.get('excel_b')
        mysql_only = options.get('mysql_only')
        dry_run = options.get('dry_run')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('MODO DRY RUN - No se guardarán cambios')
            )
        
        # Validar archivos Excel si se proporcionan
        if excel_a_path and not os.path.exists(excel_a_path):
            raise CommandError(f'Archivo Excel A no encontrado: {excel_a_path}')
        
        if excel_b_path and not os.path.exists(excel_b_path):
            raise CommandError(f'Archivo Excel B no encontrado: {excel_b_path}')
        
        if not mysql_only and not excel_a_path and not excel_b_path:
            self.stdout.write(
                self.style.WARNING(
                    'No se especificaron archivos Excel. '
                    'Se procesarán solo datos de MySQL.'
                )
            )
        
        try:
            # Crear orquestador ETL
            orchestrator = ETLOrchestrator()
            
            # Mostrar información de fuentes
            self.stdout.write('\n--- FUENTES DE DATOS ---')
            self.stdout.write(f'MySQL: ✓ Habilitado')
            
            if excel_a_path:
                self.stdout.write(f'Excel A: ✓ {excel_a_path}')
            else:
                self.stdout.write(f'Excel A: ✗ No especificado')
            
            if excel_b_path:
                self.stdout.write(f'Excel B: ✓ {excel_b_path}')
            else:
                self.stdout.write(f'Excel B: ✗ No especificado')
            
            # Ejecutar ETL
            self.stdout.write('\n--- EJECUTANDO ETL ---')
            start_time = timezone.now()
            
            if dry_run:
                self.stdout.write('Simulando ejecución ETL...')
                self.stdout.write(self.style.SUCCESS('✓ ETL simulado completado'))
                etl_run = None
            else:
                etl_run = orchestrator.run_etl_pipeline(
                    excel_a_path=excel_a_path,
                    excel_b_path=excel_b_path
                )
            
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            # Mostrar resultados
            self.stdout.write('\n--- RESULTADOS ---')
            
            if etl_run:
                self.stdout.write(f'ETL Run ID: {etl_run.id}')
                self.stdout.write(f'Estado: {etl_run.status}')
                self.stdout.write(f'Duración: {duration:.2f} segundos')
                
                if etl_run.meta:
                    meta = etl_run.meta
                    self.stdout.write('\nRegistros procesados:')
                    
                    if 'municipios_loaded' in meta:
                        self.stdout.write(f'  Municipios: {meta["municipios_loaded"]}')
                    
                    if 'instituciones_loaded' in meta:
                        self.stdout.write(f'  Instituciones: {meta["instituciones_loaded"]}')
                    
                    if 'sources' in meta:
                        sources = meta['sources']
                        self.stdout.write('\nPor fuente:')
                        self.stdout.write(f'  MySQL: {sources.get("mysql", 0)} registros')
                        self.stdout.write(f'  Excel A: {sources.get("excel_a", 0)} registros')
                        self.stdout.write(f'  Excel B: {sources.get("excel_b", 0)} registros')
                
                if etl_run.status == 'success':
                    self.stdout.write(
                        self.style.SUCCESS('\n✓ ETL COMPLETADO EXITOSAMENTE')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'\n✗ ETL FALLÓ: {etl_run.meta.get("error", "Error desconocido")}')
                    )
            else:
                self.stdout.write(f'Duración: {duration:.2f} segundos')
                self.stdout.write(
                    self.style.SUCCESS('\n✓ SIMULACIÓN COMPLETADA')
                )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n✗ ERROR EJECUTANDO ETL: {str(e)}')
            )
            raise CommandError(f'Error en ETL: {str(e)}')
        
        self.stdout.write('\n=== ETL PIPELINE FINALIZADO ===')