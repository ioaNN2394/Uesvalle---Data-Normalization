# Generated migration to create etl_file table

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('etl', '0001_initial'),
    ]

    operations = [
        # Create etl_file table
        migrations.CreateModel(
            name='ETLFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filename', models.CharField(max_length=255, verbose_name='Nombre del archivo')),
                ('file_type', models.CharField(
                    choices=[('excel', 'Excel (.xlsx, .xls)'), ('csv', 'CSV'), ('json', 'JSON')],
                    max_length=20,
                    verbose_name='Tipo de archivo'
                )),
                ('file_path', models.CharField(max_length=500, verbose_name='Ruta del archivo')),
                ('file_size', models.BigIntegerField(blank=True, null=True, verbose_name='Tamaño en bytes')),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pendiente'),
                        ('processing', 'Procesando'),
                        ('success', 'Exitoso'),
                        ('failed', 'Fallido'),
                    ],
                    default='pending',
                    max_length=30,
                    verbose_name='Estado'
                )),
                ('rows_processed', models.IntegerField(default=0, verbose_name='Filas procesadas')),
                ('rows_failed', models.IntegerField(default=0, verbose_name='Filas fallidas')),
                ('error_message', models.TextField(blank=True, null=True, verbose_name='Mensaje de error')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, verbose_name='Cargado en')),
                ('processed_at', models.DateTimeField(blank=True, null=True, verbose_name='Procesado en')),
                ('etl_run', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='files',
                    to='etl.etlrun',
                    verbose_name='Job ETL'
                )),
            ],
            options={
                'verbose_name': 'Archivo ETL',
                'verbose_name_plural': 'Archivos ETL',
                'db_table': 'uesvalle"."etl_file',
                'ordering': ['-uploaded_at'],
                'managed': True,
            },
        ),
    ]
