# Generated migration for adding lat/lon to Institucion

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('etl', '0003_add_visita_mysql_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='institucion',
            name='lat',
            field=models.DecimalField(
                blank=True,
                decimal_places=7,
                help_text='Coordenada de latitud - viene del CSV enriquecido',
                max_digits=10,
                null=True,
                verbose_name='Latitud'
            ),
        ),
        migrations.AddField(
            model_name='institucion',
            name='lon',
            field=models.DecimalField(
                blank=True,
                decimal_places=7,
                help_text='Coordenada de longitud - viene del CSV enriquecido',
                max_digits=10,
                null=True,
                verbose_name='Longitud'
            ),
        ),
    ]
