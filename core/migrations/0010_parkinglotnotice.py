import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_alter_parkinglot_id_alter_parkingspot_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='ParkingLotNotice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField(
                    help_text="Ej: 'Entrada Norte cerrada por obras hasta el viernes'.",
                    verbose_name='Mensaje del aviso',
                )),
                ('active', models.BooleanField(
                    default=True,
                    help_text='Desmárcalo para ocultarlo sin borrar el historial.',
                    verbose_name='Activo (visible en el sitio)',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('lot', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notices', to='core.parkinglot',
                )),
            ],
            options={
                'verbose_name': 'Aviso de parqueadero',
                'verbose_name_plural': 'Avisos de parqueadero',
                'ordering': ['-created_at'],
            },
        ),
    ]
