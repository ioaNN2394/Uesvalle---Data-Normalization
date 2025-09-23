"""
Comando mejorado para ejecutar el pipeline ETL completo según documentación oficial.
- Soporte para múltiples archivos Excel con pd.concat()
- Opciones avanzadas: --dry-run, --source, --excel-dir, --verbose
- Validación de conectividad MySQL y Supabase
- Upsert usando INSERT ... ON CONFLICT (PostgreSQL)

Uso:
    python manage.py etl_run --dry-run --verbose
    python manage.py etl_run --source mysql --dry-run  
    python manage.py etl_run --source excel --excel-dir "C:\datos\excels" --dry-run
    python manage.py etl_run --source both --verbose
"""
import os
import sys
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import connections
from apps.etl.services import ETLOrchestrator, ExcelExtractor, MySQLExtractor
from apps.etl.models import ETLRun


class Command(BaseCommand):
    help = 'Ejecuta el pipeline ETL completo (MySQL + Excel → Supabase) con opciones avanzadas'
    
    def add_arguments(self, parser):
        # Opciones principales según documentación
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecutar sin guardar datos (solo validación y análisis)'
        )
        
        parser.add_argument(
            '--source',
            choices=['mysql', 'excel', 'both'],
            default='both',
            help='Fuente de datos a procesar: mysql, excel o both (default: both)'
        )
        
        parser.add_argument(
            '--excel-dir',
            type=str,
            help='Directorio con múltiples archivos Excel para procesar'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Salida detallada con información de debugging'
        )
        
        # Opciones de conectividad
        parser.add_argument(
            '--skip-connectivity-test',
            action='store_true',
            help='Omitir tests de conectividad inicial'
        )
        
        # Opciones específicas para desarrollo
        parser.add_argument(
            '--sample-size',
            type=int,
            help='Procesar solo N registros por tabla (para testing)'
        )
        
        # Opciones legacy (mantener compatibilidad)
        parser.add_argument(
            '--excel-a',
            type=str,
            help='LEGACY: Ruta al archivo Excel A (usar --excel-dir en su lugar)'
        )
        
        parser.add_argument(
            '--excel-b',
            type=str,
            help='LEGACY: Ruta al archivo Excel B (usar --excel-dir en su lugar)'
        )
        
        parser.add_argument(
            '--mysql-only',
            action='store_true',
            help='LEGACY: Usar --source mysql en su lugar'
        )
    
    def handle(self, *args, **options):
        """Ejecutar ETL con opciones mejoradas"""
        
        # Extraer opciones
        dry_run = options.get('dry_run', False)
        source = options.get('source', 'both')
        excel_dir = options.get('excel_dir')
        verbose = options.get('verbose', False) or (options.get('verbosity', 1) >= 2)
        skip_connectivity = options.get('skip_connectivity_test', False)
        sample_size = options.get('sample_size')
        
        # Manejo de opciones legacy
        excel_a_path = options.get('excel_a')
        excel_b_path = options.get('excel_b')
        mysql_only = options.get('mysql_only', False)
        
        if mysql_only:
            source = 'mysql'
            self.stdout.write(
                self.style.WARNING('Usando --mysql-only (LEGACY). Recomendado: --source mysql')
            )
        
        if excel_a_path or excel_b_path:
            self.stdout.write(
                self.style.WARNING('Usando --excel-a/--excel-b (LEGACY). Recomendado: --excel-dir')
            )
        
        # Header informativo
        self.stdout.write(
            self.style.SUCCESS('🚀 PIPELINE ETL UESVALLE - VERSIÓN MEJORADA')
        )
        self.stdout.write(f"⏰ Fecha/Hora: {timezone.now()}")
        self.stdout.write(f"🔧 Modo: {'DRY-RUN' if dry_run else 'EJECUCIÓN REAL'}")
        self.stdout.write(f"📊 Fuente: {source.upper()}")
        self.stdout.write(f"📂 Excel Dir: {excel_dir or 'No especificado'}")
        self.stdout.write(f"🔍 Verbose: {'Sí' if verbose else 'No'}")
        
        if sample_size:
            self.stdout.write(f"🔬 Sample Size: {sample_size} registros por tabla")
        
        try:
            # Crear registro de ejecución ETL
            etl_run = ETLRun.objects.create(
                status='running',
                meta={
                    'dry_run': dry_run,
                    'source': source,
                    'excel_dir': excel_dir,
                    'verbose': verbose,
                    'sample_size': sample_size,
                    'legacy_files': {
                        'excel_a': excel_a_path,
                        'excel_b': excel_b_path
                    }
                }
            )
            
            self.stdout.write(f"📝 ETL Run ID: {etl_run.id}")
            
            # Tests de conectividad
            if not skip_connectivity:
                self.stdout.write("\n🔍 VERIFICANDO CONECTIVIDAD...")
                
                if source in ['mysql', 'both']:
                    mysql_ok = self._test_mysql_connection(verbose)
                    if not mysql_ok and not dry_run:
                        raise CommandError("❌ Conexión MySQL fallida. Use --dry-run para continuar sin MySQL.")
                
                supabase_ok = self._test_supabase_connection(verbose)
                if not supabase_ok:
                    raise CommandError("❌ Conexión Supabase fallida")
            
            # Inicializar orchestrator
            self.stdout.write("\n⚙️ INICIALIZANDO ETL...")
            orchestrator = ETLOrchestrator(verbose=verbose)
            
            # Preparar configuración de ejecución
            execution_config = {
                'dry_run': dry_run,
                'source_filter': source,
                'sample_size': sample_size,
                'verbose': verbose
            }
            
            # Manejar archivos Excel
            if source in ['excel', 'both']:
                if excel_dir:
                    execution_config['excel_directory'] = excel_dir
                elif excel_a_path or excel_b_path:
                    # Modo legacy - crear directorio temporal
                    execution_config['legacy_excel_files'] = {
                        'excel_a': excel_a_path,
                        'excel_b': excel_b_path
                    }
                else:
                    self.stdout.write(
                        self.style.WARNING("⚠️ Fuente Excel especificada pero no se proporcionaron archivos")
                    )
            
            # Ejecutar pipeline ETL
            self.stdout.write("\n🚀 EJECUTANDO PIPELINE ETL...")
            
            result = orchestrator.execute_full_pipeline(**execution_config)
            
            # Actualizar resultado en BD
            etl_run.mark_as_success({
                'processed': result.get('total_processed', 0),
                'inserted': result.get('total_inserted', 0),
                'updated': result.get('total_updated', 0),
                'errors': result.get('errors', []),
                'summary': result.get('summary', {})
            })
            
            # Mostrar resumen exitoso
            self.stdout.write(
                self.style.SUCCESS(f"\n✅ ETL COMPLETADO EXITOSAMENTE")
            )
            self._show_execution_summary(result)
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING("\n💡 Modo DRY-RUN: ningún dato fue guardado en Supabase")
                )
                self.stdout.write("   Para ejecutar realmente: quitar --dry-run")
            
        except Exception as e:
            # Marcar ejecución como fallida
            if 'etl_run' in locals():
                etl_run.mark_as_failed(str(e))
            
            self.stdout.write(
                self.style.ERROR(f"\n❌ ERROR EN ETL: {e}")
            )
            
            if verbose:
                import traceback
                self.stdout.write("\n🔍 STACK TRACE COMPLETO:")
                self.stdout.write(traceback.format_exc())
            
            # Sugerencias de solución
            self._show_error_suggestions(e, source, excel_dir)
            
            raise CommandError(f"Pipeline ETL falló: {e}")

    def _show_execution_summary(self, result):
        """Mostrar resumen de ejecución"""
        self.stdout.write("\n📊 RESUMEN DE EJECUCIÓN:")
        self.stdout.write(f"   📈 Registros procesados: {result.get('total_processed', 0):,}")
        self.stdout.write(f"   ➕ Registros insertados: {result.get('total_inserted', 0):,}")
        self.stdout.write(f"   🔄 Registros actualizados: {result.get('total_updated', 0):,}")
        
        if result.get('errors'):
            self.stdout.write(f"   ⚠️ Errores/Advertencias: {len(result['errors'])}")
        
        if result.get('summary'):
            self.stdout.write("\n📋 DETALLE POR TABLA:")
            for table, stats in result['summary'].items():
                self.stdout.write(f"   • {table}: {stats}")
        
        # Recomendaciones
        total_processed = result.get('total_processed', 0)
        if total_processed == 0:
            self.stdout.write(
                self.style.WARNING("\n⚠️ No se procesaron registros. Verificar:")
            )
            self.stdout.write("   • Conectividad con fuentes de datos")
            self.stdout.write("   • Existencia de archivos Excel")
            self.stdout.write("   • Permisos de lectura")
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\n🎉 Pipeline ejecutado exitosamente: {total_processed:,} registros")
            )

    def _test_mysql_connection(self, verbose=False):
        """Test conectividad MySQL"""
        try:
            if verbose:
                self.stdout.write("  🔍 Probando MySQL...")
                
            connection = connections['source_mysql']
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()[0]
                
            if result == 1:
                if verbose:
                    self.stdout.write("  ✅ MySQL: Conectado")
                return True
            else:
                if verbose:
                    self.stdout.write("  ❌ MySQL: Respuesta inesperada")
                return False
                
        except Exception as e:
            if verbose:
                self.stdout.write(f"  ❌ MySQL: {e}")
            return False

    def _test_supabase_connection(self, verbose=False):
        """Test conectividad Supabase"""
        try:
            if verbose:
                self.stdout.write("  🔍 Probando Supabase...")
                
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()[0]
                
            if result == 1:
                if verbose:
                    self.stdout.write("  ✅ Supabase: Conectado")
                return True
            else:
                if verbose:
                    self.stdout.write("  ❌ Supabase: Respuesta inesperada")
                return False
                
        except Exception as e:
            if verbose:
                self.stdout.write(f"  ❌ Supabase: {e}")
            return False

    def _show_error_suggestions(self, error, source, excel_dir):
        """Mostrar sugerencias para resolver errores"""
        error_str = str(error).lower()
        
        self.stdout.write("\n🔧 SUGERENCIAS DE SOLUCIÓN:")
        
        if 'mysql' in error_str or 'connection' in error_str:
            self.stdout.write("   📋 Error de MySQL:")
            self.stdout.write("      • Verificar que MySQL esté ejecutándose")
            self.stdout.write("      • Revisar credenciales en archivo .env")
            self.stdout.write("      • Instalar: pip install mysqlclient")
            self.stdout.write("      • Probar: python test_mysql_connection.py")
            
        elif 'excel' in error_str or 'file' in error_str:
            self.stdout.write("   📄 Error de archivos Excel:")
            self.stdout.write("      • Verificar que los archivos existan")
            self.stdout.write("      • Comprobar permisos de lectura")
            self.stdout.write("      • Instalar: pip install openpyxl")
            if excel_dir:
                self.stdout.write(f"      • Directorio especificado: {excel_dir}")
                
        elif 'supabase' in error_str or 'postgres' in error_str:
            self.stdout.write("   🐘 Error de Supabase/PostgreSQL:")
            self.stdout.write("      • Verificar credenciales de Supabase")
            self.stdout.write("      • Revisar configuración de red")
            self.stdout.write("      • Comprobar esquema 'uesvalle' existe")
            
        else:
            self.stdout.write("   🔍 Error general:")
            self.stdout.write("      • Ejecutar con --verbose para más detalles")
            self.stdout.write("      • Probar con --dry-run primero")
            self.stdout.write("      • Revisar logs en logs/etl.log")
        
        self.stdout.write("\n📚 COMANDOS ÚTILES:")
        self.stdout.write("   • python quick_test.py")
        self.stdout.write("   • python test_mysql_connection.py") 
        self.stdout.write("   • python manage.py etl_run --dry-run --verbose")