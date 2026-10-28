"""
Pruebas de FR19 (importar disponibilidad desde una API REST externa) y
FR33 (estadísticas de ocupación). En un archivo aparte de core/tests.py
para no chocar con los cambios de los demás en ese archivo.
"""

from datetime import timedelta
from io import StringIO
from unittest import mock

import requests
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from reports.models import ParkingReport

from .external_api import ExternalAPIError, apply_entries, extract_entries, import_from_url
from .models import ParkingLot
from .occupancy_stats import build_statistics


def make_lot(name, slug, cars=0, motos=0, pmr=0, occ_cars=0, occ_motos=0, occ_pmr=0):
    return ParkingLot.objects.create(
        name=name, slug=slug, total_capacity=cars + motos + pmr,
        capacity_cars=cars, capacity_motorcycles=motos, capacity_accessibility=pmr,
        occupied_cars=occ_cars, occupied_motorcycles=occ_motos, occupied_accessibility=occ_pmr,
    )


def fake_response(payload=None, status=200, json_error=False):
    response = mock.Mock()
    response.status_code = status
    if status >= 400:
        error = requests.HTTPError(response=response)
        response.raise_for_status.side_effect = error
    else:
        response.raise_for_status.return_value = None
    if json_error:
        response.json.side_effect = ValueError("no json")
    else:
        response.json.return_value = payload
    return response


class ExternalAPIImportTest(TestCase):
    """FR19 – REST API integration."""

    def setUp(self):
        ParkingLot.objects.all().delete()
        self.norte = make_lot("Norte", "norte", cars=100, motos=20, pmr=5)
        self.sur = make_lot("Sur", "sur", cars=50, motos=10, pmr=2)

    def test_applies_occupancy_from_api(self):
        payload = {"parkings": [
            {"slug": "norte", "occupied_cars": 80, "occupied_motorcycles": 5, "occupied_accessibility": 1},
            {"slug": "sur", "occupied_cars": 10},
        ]}
        with mock.patch("core.external_api.requests.get", return_value=fake_response(payload)) as get:
            result = import_from_url("https://api.ejemplo.com/parqueaderos")

        get.assert_called_once()
        self.assertEqual(result.updated, ["Norte", "Sur"])
        self.norte.refresh_from_db()
        self.sur.refresh_from_db()
        self.assertEqual((self.norte.occupied_cars, self.norte.occupied_motorcycles, self.norte.occupied_accessibility), (80, 5, 1))
        self.assertEqual(self.sur.occupied_cars, 10)
        self.assertEqual(self.sur.occupied_motorcycles, 0)  # no venía en el JSON: no se toca

    def test_accepts_plain_list_and_lots_key(self):
        self.assertEqual(extract_entries([{"slug": "x"}]), [{"slug": "x"}])
        self.assertEqual(extract_entries({"lots": [{"slug": "x"}]}), [{"slug": "x"}])
        with self.assertRaises(ExternalAPIError):
            extract_entries({"otra_cosa": 1})

    def test_values_above_capacity_are_clamped(self):
        result = apply_entries([{"slug": "sur", "occupied_cars": 999}])
        self.sur.refresh_from_db()
        self.assertEqual(self.sur.occupied_cars, 50)
        self.assertEqual(result.adjusted, [("Sur", "occupied_cars", 999, 50)])

    def test_unknown_lot_and_invalid_values_are_skipped(self):
        result = apply_entries([
            {"slug": "no-existe", "occupied_cars": 3},
            {"slug": "norte", "occupied_cars": -4},
            {"slug": "sur", "occupied_cars": "muchos"},
            {"occupied_cars": 2},
        ])
        self.assertEqual(result.updated, [])
        self.assertEqual(len(result.skipped), 4)
        self.norte.refresh_from_db()
        self.assertEqual(self.norte.occupied_cars, 0)

    def test_network_and_format_errors_are_friendly(self):
        cases = [
            mock.Mock(side_effect=requests.Timeout()),
            mock.Mock(side_effect=requests.ConnectionError()),
            mock.Mock(return_value=fake_response(status=500)),
            mock.Mock(return_value=fake_response(json_error=True)),
        ]
        for fake_get in cases:
            with self.subTest(fake_get=fake_get), mock.patch("core.external_api.requests.get", fake_get):
                with self.assertRaises(ExternalAPIError):
                    import_from_url("https://api.ejemplo.com/parqueaderos")

    def test_management_command(self):
        payload = [{"slug": "norte", "occupied_cars": 42}]
        out = StringIO()
        with mock.patch("core.external_api.requests.get", return_value=fake_response(payload)):
            call_command("import_availability", url="https://api.ejemplo.com/x", stdout=out)
        self.norte.refresh_from_db()
        self.assertEqual(self.norte.occupied_cars, 42)
        self.assertIn("1 parqueadero(s) actualizado(s)", out.getvalue())

    @override_settings(EXTERNAL_PARKING_API_URL="")
    def test_management_command_without_url_fails(self):
        with self.assertRaises(CommandError):
            call_command("import_availability", stdout=StringIO())


class ExternalAPIDashboardTest(TestCase):
    """FR19 desde el dashboard del administrador."""

    def setUp(self):
        ParkingLot.objects.all().delete()
        self.lot = make_lot("Norte", "norte", cars=100)
        User = get_user_model()
        self.admin = User.objects.create_user("admin", password="clave-segura-123", is_staff=True)
        self.student = User.objects.create_user("estudiante", password="clave-segura-123")

    def test_staff_can_import(self):
        self.client.login(username="admin", password="clave-segura-123")
        payload = {"parkings": [{"slug": "norte", "occupied_cars": 70}]}
        with mock.patch("core.external_api.requests.get", return_value=fake_response(payload)):
            response = self.client.post(reverse("import_external_availability"), {"url": "https://api.ejemplo.com/p"}, follow=True)
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.occupied_cars, 70)
        self.assertContains(response, "1 parqueadero(s) actualizado(s)")

    def test_invalid_url_is_rejected(self):
        self.client.login(username="admin", password="clave-segura-123")
        with mock.patch("core.external_api.requests.get") as get:
            response = self.client.post(reverse("import_external_availability"), {"url": "file:///etc/passwd"}, follow=True)
        get.assert_not_called()
        self.assertContains(response, "URL válida")

    def test_non_staff_cannot_import(self):
        self.client.login(username="estudiante", password="clave-segura-123")
        with mock.patch("core.external_api.requests.get") as get:
            self.client.post(reverse("import_external_availability"), {"url": "https://api.ejemplo.com/p"})
        get.assert_not_called()
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.occupied_cars, 0)

    def test_dashboard_shows_import_form(self):
        self.client.login(username="admin", password="clave-segura-123")
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Importar disponibilidad desde una API externa")

    @override_settings(DEBUG=True)
    def test_simulator_returns_expected_format(self):
        data = self.client.get(reverse("external_api_simulator")).json()
        entry = data["parkings"][0]
        self.assertEqual(entry["slug"], "norte")
        self.assertTrue(0 <= entry["occupied_cars"] <= 100)
        # Lo que devuelve el simulador se puede importar tal cual.
        result = apply_entries(extract_entries(data))
        self.assertEqual(result.updated, ["Norte"])

    @override_settings(DEBUG=False)
    def test_simulator_disabled_in_production(self):
        self.assertEqual(self.client.get(reverse("external_api_simulator")).status_code, 404)


class OccupancyStatisticsTest(TestCase):
    """FR33 – Parking occupancy statistics."""

    def setUp(self):
        ParkingLot.objects.all().delete()
        self.free = make_lot("Libre", "libre", cars=80, motos=20, occ_cars=10)
        self.full = make_lot("Lleno", "lleno", cars=40, pmr=10, occ_cars=40, occ_pmr=10)

    def test_campus_totals(self):
        stats = build_statistics(ParkingLot.objects.all())
        self.assertEqual(stats["totals"]["capacity"], 150)
        self.assertEqual(stats["totals"]["occupied"], 60)
        self.assertEqual(stats["totals"]["available"], 90)
        self.assertEqual(stats["totals"]["percentage"], 40.0)

    def test_ranking_and_highlights(self):
        stats = build_statistics(ParkingLot.objects.all())
        self.assertEqual([row["lot"].name for row in stats["ranking"]], ["Lleno", "Libre"])
        self.assertEqual(stats["most_occupied"], self.full)
        self.assertEqual(stats["least_occupied"], self.free)

    def test_by_vehicle_type(self):
        by_type = {row["key"]: row for row in build_statistics(ParkingLot.objects.all())["vehicle_types"]}
        self.assertEqual((by_type["car"]["occupied"], by_type["car"]["capacity"]), (50, 120))
        self.assertEqual(by_type["motorcycle"]["percentage"], 0.0)
        self.assertEqual(by_type["accessibility"]["percentage"], 100.0)

    def test_recent_activity_counts_last_24h_without_invalid(self):
        ParkingReport.objects.create(lot=self.free, report_type="occupied", vehicle_type="car")
        ParkingReport.objects.create(lot=self.free, report_type="available", vehicle_type="car")
        ParkingReport.objects.create(lot=self.full, report_type="occupied", vehicle_type="car", status="invalid")
        old = ParkingReport.objects.create(lot=self.full, report_type="occupied", vehicle_type="car")
        ParkingReport.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=2))

        activity = build_statistics(ParkingLot.objects.all())["activity"]
        self.assertEqual((activity["arrivals"], activity["departures"], activity["total"]), (1, 1, 2))
        self.assertEqual(activity["rows"][0]["lot"], self.free)

    def test_page_is_public_and_linked_from_home(self):
        response = self.client.get(reverse("occupancy_stats"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Estadísticas de ocupación")
        self.assertContains(response, "Ocupación por parqueadero")
        self.assertContains(response, "Se actualizan solos cada 30 segundos")
        self.assertContains(response, 'id="stats-content"')
        self.assertContains(response, reverse("occupancy_stats"), html=False)
        self.assertContains(self.client.get(reverse("home")), reverse("occupancy_stats"))

    def test_page_without_lots(self):
        ParkingLot.objects.all().delete()
        response = self.client.get(reverse("occupancy_stats"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Todavía no hay parqueaderos")
