"""FR13 – Guarda un registro del historial cada vez que se guarda un ParkingLot."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .availability_history import record_snapshot
from .models import ParkingLot


@receiver(post_save, sender=ParkingLot)
def snapshot_on_lot_save(sender, instance, raw=False, **kwargs):
    # raw=True: se está cargando un fixture; no inventamos historial.
    if raw:
        return
    record_snapshot(instance)
