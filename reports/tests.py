from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from core.models import ParkingLot
from reports.models import ParkingReport

class ParkingReportsHistoryTests(TestCase):
    """
    FR31 – Parking reports history:
    Pruebas unitarias para el almacenamiento y consulta del historial
    de reportes enviados por los usuarios.
    """

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="alejo_test",
            email="alejo@eafit.edu.co",
            password="Password123*"
        )
        self.user2 = User.objects.create_user(
            username="camilo_test",
            email="camilo@eafit.edu.co",
            password="Password123*"
        )
        self.lot, _ = ParkingLot.objects.get_or_create(
            slug="parqueadero-report-test",
            defaults={
                "name": "Parqueadero Report Test",
                "total_capacity": 100,
                "capacity_cars": 60,
                "capacity_motorcycles": 30,
                "capacity_accessibility": 10,
                "occupied_cars": 10,
                "occupied_motorcycles": 5,
                "occupied_accessibility": 1,
            }
        )
        self.client = Client()

    def test_authenticated_user_report_attaches_user_and_stores_history(self):
        """Verifica que al enviar un reporte autenticado, se asocie el usuario al historial (FR31)."""
        self.client.login(username="alejo_test", password="Password123*")
        response = self.client.post(
            reverse("report_available", kwargs={"lot_id": self.lot.id}),
            {"vehicle_type": "car"}
        )
        self.assertEqual(response.status_code, 302)

        report = ParkingReport.objects.filter(lot=self.lot, report_type="available").first()
        self.assertIsNotNone(report)
        self.assertEqual(report.user, self.user1)
        self.assertEqual(report.vehicle_type, "car")
        self.assertEqual(report.status, "pending")
        self.assertIsNotNone(report.created_at)

    def test_user_reports_history_view_requires_login(self):
        """Verifica que la vista de historial de reportes requiera autenticación."""
        response = self.client.get(reverse("reports_history"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_user_reports_history_shows_only_own_reports(self):
        """Verifica que un usuario solo vea su propio historial de reportes en /reports/history/ (FR31)."""
        # Reporte de user1
        ParkingReport.objects.create(
            lot=self.lot,
            user=self.user1,
            report_type="available",
            vehicle_type="car",
            status="valid"
        )
        # Reporte de user2
        ParkingReport.objects.create(
            lot=self.lot,
            user=self.user2,
            report_type="occupied",
            vehicle_type="motorcycle",
            status="pending"
        )

        self.client.login(username="alejo_test", password="Password123*")
        response = self.client.get(reverse("reports_history"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reports/history.html")

        reports_in_context = list(response.context["reports"])
        self.assertEqual(len(reports_in_context), 1)
        self.assertEqual(reports_in_context[0].user, self.user1)
        self.assertEqual(reports_in_context[0].report_type, "available")

    def test_reports_history_renders_all_fields(self):
        """Verifica que la vista /reports/history/ renderice todos los campos del reporte (FR31)."""
        ParkingReport.objects.create(
            lot=self.lot,
            user=self.user1,
            report_type="incorrect",
            vehicle_type="general",
            description="La talanquera norte no reconoce el carné",
            status="pending"
        )
        self.client.login(username="alejo_test", password="Password123*")
        response = self.client.get(reverse("reports_history"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Historial de mis reportes")
        self.assertContains(response, "La talanquera norte no reconoce el carné")
        self.assertContains(response, "Pendiente")
