# Generated manually to fix managed settings

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("etl", "0004_create_etl_run_table"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="dimmunicipio",
            options={
                "ordering": ["nombre"],
                "verbose_name": "Municipio",
                "verbose_name_plural": "Municipios",
                "managed": True,
            },
        ),
        migrations.AlterModelOptions(
            name="institucion",
            options={
                "ordering": ["nombre"],
                "verbose_name": "Institución",
                "verbose_name_plural": "Instituciones",
                "managed": True,
            },
        ),
        migrations.AlterModelOptions(
            name="sede",
            options={
                "ordering": ["nombre"],
                "verbose_name": "Sede",
                "verbose_name_plural": "Sedes",
                "managed": True,
            },
        ),
    ]
