from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_alter_parkinglot_id_alter_parkingspot_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='parkingspot',
            name='rotation',
            field=models.IntegerField(
                default=0,
                help_text='Gira el rectángulo de la casilla, en grados (0-359). Útil para celdas en diagonal o perpendiculares al pasillo.',
                verbose_name='Rotación (grados)',
            ),
        ),
        migrations.AddField(
            model_name='parkingspot',
            name='width',
            field=models.PositiveIntegerField(
                default=42,
                help_text='Ancho del rectángulo de la casilla en píxeles.',
                verbose_name='Ancho (px)',
            ),
        ),
        migrations.AddField(
            model_name='parkingspot',
            name='height',
            field=models.PositiveIntegerField(
                default=26,
                help_text='Alto del rectángulo de la casilla en píxeles.',
                verbose_name='Alto (px)',
            ),
        ),
    ]
