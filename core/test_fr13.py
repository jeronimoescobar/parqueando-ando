"""FR13 – Historial de disponibilidad."""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core import availability_history
from core.external_api import apply_entries
from core.models import AvailabilitySnapshot, ParkingLot


def make_lot(**kwargs):
    defaults = dict(
        name="Lote Prueba", slug="lote-prueba", total_capacity=100,
        capacity_cars=80, capacity_motorcycles=15, capacity_accessibility=5,
    )
    defaults.update(kwargs)
    return ParkingLot.objects.create(**defaults)


class SnapshotRecordingTest(TestCase):
    def test_creating_a_lot_records_first_snapshot(self):
        lot = make_lot()
        self.assertEqual(lot.snapshots.count(), 1)

    def test_change_in_occupancy_records_new_snapshot(self):
        lot = make_lot()
        lot.occupied_cars = 10
        lot.save()
        self.assertEqual(lot.snapshots.count(), 2)
        self.assertEqual(lot.snapshots.first().occupied_cars, 10)

    def test_saving_without_changes_does_not_duplicate(self):
        lot = make_lot()
        lot.save()
        lot.save()
        self.assertEqual(lot.snapshots.count(), 1)

    def test_external_api_import_records_snapshot(self):
        lot = make_lot()
        apply_entries([{"slug": lot.slug, "occupied_cars": 40}])
        self.assertEqual(lot.snapshots.count(), 2)
        self.assertEqual(lot.snapshots.first().occupied_cars, 40)

    def test_report_via_view_records_snapshot(self):
        from django.contrib.auth.models import User
        lot = make_lot(occupied_cars=5)
        User.objects.create_user("u1", "u1@example.com", "ClaveSegura#2026")
        self.client.login(username="u1", password="ClaveSegura#2026")
        self.client.post(reverse("report_occupied", args=[lot.id]), {"vehicle_type": "car"})
        lot.refresh_from_db()
        self.assertEqual(lot.occupied_cars, 6)
        self.assertEqual(lot.snapshots.first().occupied_cars, 6)


class HistoryViewTest(TestCase):
    def setUp(self):
        self.lot = make_lot()
        now = timezone.now()
        # Datos controlados: se reemplazan las fotos automáticas.
        AvailabilitySnapshot.objects.all().delete()
        for hours_ago, cars in [(30, 90), (5, 20), (3, 60), (1, 40)]:
            AvailabilitySnapshot.objects.create(
                lot=self.lot, occupied_cars=cars, total_capacity=100,
                recorded_at=now - timedelta(hours=hours_ago),
            )

    def test_page_is_public_and_lists_lots(self):
        response = self.client.get(reverse("availability_history"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lote Prueba")

    def test_period_24h_excludes_older_records(self):
        data = availability_history.build_history(self.lot, "24h")
        self.assertEqual(data["summary"]["count"], 3)
        self.assertEqual(data["summary"]["peak"].occupancy_percentage, 60.0)
        self.assertEqual(data["summary"]["low"].occupancy_percentage, 20.0)
        self.assertEqual(data["summary"]["average"], 40.0)

    def test_period_7d_includes_older_records(self):
        data = availability_history.build_history(self.lot, "7d")
        self.assertEqual(data["summary"]["count"], 4)

    def test_invalid_period_falls_back_to_default(self):
        data = availability_history.build_history(self.lot, "cualquiera")
        self.assertEqual(data["period"], "24h")

    def test_rows_are_most_recent_first(self):
        data = availability_history.build_history(self.lot, "7d")
        times = [r.recorded_at for r in data["rows"]]
        self.assertEqual(times, sorted(times, reverse=True))

    def test_unknown_lot_slug_falls_back_to_first_lot(self):
        response = self.client.get(reverse("availability_history"), {"lot": "no-existe"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected"].pk, self.lot.pk)

    def test_empty_period_shows_friendly_message(self):
        AvailabilitySnapshot.objects.all().delete()
        response = self.client.get(reverse("availability_history"), {"lot": self.lot.slug})
        self.assertContains(response, "Todavía no hay registros")

    def test_page_without_lots_does_not_crash(self):
        ParkingLot.objects.all().delete()
        self.assertEqual(self.client.get(reverse("availability_history")).status_code, 200)
