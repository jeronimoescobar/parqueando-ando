from django.test import TestCase
from django.urls import reverse
from .models import ParkingLot
from .parking_recommendation import recommend_parking_lot


class ParkingLotModelTest(TestCase):
    def setUp(self):
        ParkingLot.objects.all().delete()

    def test_create_parking_lot(self):
        lot = ParkingLot.objects.create(
            name="Parqueadero Central",
            slug="parqueadero-central",
            total_capacity=100,
            occupied_cars=25,
        )
        self.assertEqual(str(lot), "Parqueadero Central")
        self.assertAlmostEqual(lot.occupancy_ratio, 0.25)
        self.assertEqual(lot.available_spaces, 75)


    def test_occupancy_ratio_zero_capacity(self):
        lot = ParkingLot.objects.create(
            name="Vacío",
            slug="vacio",
            total_capacity=0,
            occupied_cars=0,
        )
        self.assertEqual(lot.occupancy_ratio, 0.0)

    def test_fr6_occupancy_status(self):
        available_lot = ParkingLot.objects.create(
            name="Libre", slug="libre", total_capacity=100, occupied_cars=20
        )
        limited_lot = ParkingLot.objects.create(
            name="Limitado", slug="limitado", total_capacity=100, occupied_cars=80
        )
        full_lot = ParkingLot.objects.create(
            name="Lleno", slug="lleno", total_capacity=100, occupied_cars=100
        )
        self.assertEqual(available_lot.occupancy_status, "available")
        self.assertEqual(available_lot.occupancy_status_display, "Disponible")

        self.assertEqual(limited_lot.occupancy_status, "limited")
        self.assertEqual(limited_lot.occupancy_status_display, "Limitado")

        self.assertEqual(full_lot.occupancy_status, "full")
        self.assertEqual(full_lot.occupancy_status_display, "Lleno")

    def test_fr7_occupancy_percentage(self):
        lot = ParkingLot.objects.create(
            name="Parqueadero Percentage", slug="parqueadero-percentage",
            total_capacity=200, occupied_cars=50,
        )
        self.assertEqual(lot.occupancy_percentage, 25)

    def test_fr7_occupancy_percentage_zero_capacity(self):
        lot = ParkingLot.objects.create(
            name="Sin capacidad", slug="sin-capacidad",
            total_capacity=0, occupied_cars=0,
        )
        self.assertEqual(lot.occupancy_percentage, 0)


class ParkingRecommendationTest(TestCase):
    def test_fr9_recommends_lot_with_most_availability(self):
        busy_lot = ParkingLot.objects.create(
            name="Ocupado", slug="ocupado", total_capacity=100, occupied_cars=90,
        )
        free_lot = ParkingLot.objects.create(
            name="Libre", slug="libre-recomendado", total_capacity=100, occupied_cars=10,
        )
        recommended = recommend_parking_lot([busy_lot, free_lot])
        self.assertEqual(recommended, free_lot)

    def test_fr9_no_recommendation_when_all_full(self):
        full_lot_1 = ParkingLot.objects.create(
            name="Lleno 1", slug="lleno-1", total_capacity=50, occupied_cars=50,
        )
        full_lot_2 = ParkingLot.objects.create(
            name="Lleno 2", slug="lleno-2", total_capacity=30, occupied_cars=30,
        )
        recommended = recommend_parking_lot([full_lot_1, full_lot_2])
        self.assertIsNone(recommended)

    def test_fr9_no_recommendation_when_no_lots(self):
        self.assertIsNone(recommend_parking_lot([]))


class HomeViewTest(TestCase):
    def setUp(self):
        ParkingLot.objects.all().delete()

    def test_home_view_displays_parking_lots(self):
        lot1 = ParkingLot.objects.create(
            name="Parqueadero Sur",
            slug="parqueadero-sur",
            total_capacity=50,
            occupied_cars=10,
        )
        lot2 = ParkingLot.objects.create(
            name="Parqueadero Norte",
            slug="parqueadero-norte",
            total_capacity=80,
            occupied_cars=40,
        )
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Parqueadero Sur")
        self.assertContains(response, "Parqueadero Norte")

    def test_fr6_full_parking_lot_explicit_message(self):
        ParkingLot.objects.create(
            name="Parqueadero Principal",
            slug="parqueadero-principal",
            total_capacity=50,
            occupied_cars=50,
        )
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PARQUEADERO LLENO")

    def test_fr9_home_view_shows_recommended_lot(self):
        ParkingLot.objects.create(
            name="Parqueadero Congestionado", slug="parqueadero-congestionado",
            total_capacity=100, occupied_cars=95,
        )
        ParkingLot.objects.create(
            name="Parqueadero Recomendado", slug="parqueadero-recomendado",
            total_capacity=100, occupied_cars=5,
        )
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'Parqueadero recomendado: <span data-rec="name">Parqueadero Recomendado</span>')

    def test_fr7_home_view_shows_occupancy_percentage(self):
        ParkingLot.objects.create(
            name="Parqueadero Detalle", slug="parqueadero-detalle",
            total_capacity=100, occupied_cars=30,
        )
        response = self.client.get(reverse("home"))
        self.assertContains(response, '<span data-field="percentage">30,0</span>%')
        self.assertContains(response, '<span data-field="occupied">30</span> ocupadas')

    def test_home_view_displays_vehicle_capacity_breakdown(self):
        ParkingLot.objects.create(
            name="Parqueadero con desglose",
            slug="parqueadero-con-desglose",
            total_capacity=110,
            capacity_cars=103,
            capacity_motorcycles=4,
            capacity_accessibility=3,
        )
        response = self.client.get(reverse("home"))
        self.assertContains(response, '<span data-field="available-cars">103</span>/<span data-field="capacity-cars">103</span>')
        self.assertContains(response, '<span data-field="available-motorcycles">4</span>/<span data-field="capacity-motorcycles">4</span>')
        self.assertContains(response, '<span data-field="available-accessibility">3</span>/<span data-field="capacity-accessibility">3</span>')




# ════════════════════════════════════════════════════════════════════════
# Sprint 3 — FR2 (login), FR12 (filtros), FR35 (información general)
# ════════════════════════════════════════════════════════════════════════
from datetime import datetime
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model

from .filters import filter_parking_lots, parse_filters
from .models import FavoriteParkingLot
from .parking_info import LOTS_INFO, is_open_at


class UserLoginTest(TestCase):
    """FR2 – User login."""

    def setUp(self):
        User = get_user_model()
        self.student = User.objects.create_user(username="estudiante", password="clave-segura-123")
        self.admin = User.objects.create_user(
            username="admin", password="clave-segura-123", is_staff=True
        )

    def test_login_page_loads(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Iniciar sesión")

    def test_regular_user_goes_to_home(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": "estudiante", "password": "clave-segura-123"}
        )
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.student.id)

    def test_staff_goes_to_dashboard(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": "admin", "password": "clave-segura-123"}
        )
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)

    def test_next_parameter_is_respected(self):
        response = self.client.post(
            reverse("accounts:login") + "?next=/informacion/",
            {"username": "estudiante", "password": "clave-segura-123", "next": "/informacion/"},
        )
        self.assertRedirects(response, "/informacion/", fetch_redirect_response=False)

    def test_external_next_is_ignored(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "estudiante", "password": "clave-segura-123", "next": "https://evil.com/"},
        )
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)

    def test_wrong_password_shows_error(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": "estudiante", "password": "mala"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Usuario o contraseña incorrectos")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_home_shows_user_and_logout_when_logged_in(self):
        self.client.login(username="estudiante", password="clave-segura-123")
        response = self.client.get(reverse("home"))
        self.assertContains(response, "estudiante")
        self.assertContains(response, "Cerrar sesión")
        self.assertNotContains(response, "Panel de administración")

    def test_home_shows_login_link_when_anonymous(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("accounts:login"))
        self.assertContains(response, "Iniciar sesión")

    def test_logout_returns_home(self):
        self.client.login(username="estudiante", password="clave-segura-123")
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_anonymous_favorites_move_to_account_on_login(self):
        lot = ParkingLot.objects.create(name="Fav", slug="fav-login", total_capacity=10)
        self.client.post(reverse("toggle_favorite_api", args=[lot.id]))
        self.assertTrue(FavoriteParkingLot.objects.filter(user__isnull=True, lot=lot).exists())

        self.client.post(reverse("accounts:login"), {"username": "estudiante", "password": "clave-segura-123"})

        self.assertTrue(FavoriteParkingLot.objects.filter(user=self.student, lot=lot).exists())
        self.assertFalse(FavoriteParkingLot.objects.filter(user__isnull=True, lot=lot).exists())


class ParkingFilterTest(TestCase):
    """FR12 – Filtrar parqueaderos por disponibilidad."""

    def setUp(self):
        ParkingLot.objects.all().delete()
        self.free = ParkingLot.objects.create(
            name="Libre", slug="libre-f", total_capacity=100,
            capacity_cars=90, capacity_motorcycles=10, occupied_cars=10,
        )
        self.limited = ParkingLot.objects.create(
            name="Limitado", slug="limitado-f", total_capacity=100,
            capacity_cars=100, occupied_cars=80,
        )
        self.full = ParkingLot.objects.create(
            name="Lleno", slug="lleno-f", total_capacity=50,
            capacity_cars=45, capacity_motorcycles=5, occupied_cars=45, occupied_motorcycles=5,
        )
        self.lots = [self.free, self.limited, self.full]

    def test_filter_by_status(self):
        self.assertEqual(filter_parking_lots(self.lots, status="available"), [self.free])
        self.assertEqual(filter_parking_lots(self.lots, status="full"), [self.full])

    def test_filter_by_vehicle(self):
        # Solo "Libre" tiene cupos de moto disponibles.
        self.assertEqual(filter_parking_lots(self.lots, vehicle="motorcycle"), [self.free])

    def test_filters_combine(self):
        self.assertEqual(filter_parking_lots(self.lots, status="limited", vehicle="motorcycle"), [])

    def test_invalid_values_are_ignored(self):
        self.assertEqual(
            parse_filters({"estado": "x", "vehiculo": "avion"}),
            {"status": None, "vehicle": None},
        )

    def test_api_filters(self):
        response = self.client.get(reverse("lots_state_api"), {"estado": "available"})
        names = [lot["name"] for lot in response.json()["lots"]]
        self.assertEqual(names, ["Libre"])

    def test_home_hides_lots_that_do_not_match(self):
        response = self.client.get(reverse("home"), {"estado": "full"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["visible_lots_count"], 1)
        # Todas las tarjetas se renderizan (el JS puede volver a mostrarlas),
        # pero solo "Lleno" pasa el filtro; las demás quedan ocultas.
        items = response.context["parking_lots"]
        self.assertEqual(len(items), 3)
        self.assertEqual([i["lot"].name for i in items if i["matches_filter"]], ["Lleno"])

    def test_home_filter_bar_counts(self):
        response = self.client.get(reverse("home"))
        counts = {opt["value"]: opt["count"] for opt in response.context["status_filter_options"]}
        self.assertEqual(counts, {"": 3, "available": 1, "limited": 1, "full": 1})


class ParkingInfoTest(TestCase):
    """FR35 – Información general de los parqueaderos."""

    BOGOTA = ZoneInfo("America/Bogota")
    NORTE = next(info for info in LOTS_INFO if info["slug"] == "parqueadero-norte")
    SUR = next(info for info in LOTS_INFO if info["slug"] == "parqueadero-sur")

    def test_page_loads_with_all_sections(self):
        response = self.client.get(reverse("parking_info"))
        self.assertEqual(response.status_code, 200)
        for text in ["Horarios", "Tarifas", "¿Cómo entro?", "¿Dónde pago?",
                     "Normas básicas", "Contacto", "Parque Los Guayabos",
                     "$8.700 / día", "parqueadero@eafit.edu.co", "Bloque 20"]:
            self.assertContains(response, text)

    def test_home_links_to_info_page(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("parking_info"))

    def test_open_on_weekday_morning(self):
        tuesday_9am = datetime(2026, 9, 22, 9, 0, tzinfo=self.BOGOTA)
        self.assertTrue(is_open_at(self.NORTE["open_hours"], tuesday_9am))

    def test_closed_late_at_night(self):
        tuesday_11pm = datetime(2026, 9, 22, 23, 0, tzinfo=self.BOGOTA)
        self.assertFalse(is_open_at(self.NORTE["open_hours"], tuesday_11pm))

    def test_sunday_only_sur_is_open(self):
        sunday_noon = datetime(2026, 9, 27, 12, 0, tzinfo=self.BOGOTA)
        self.assertFalse(is_open_at(self.NORTE["open_hours"], sunday_noon))
        self.assertTrue(is_open_at(self.SUR["open_hours"], sunday_noon))

    def test_lot_without_schedule_is_unknown(self):
        self.assertIsNone(is_open_at(None, datetime(2026, 9, 22, 9, 0, tzinfo=self.BOGOTA)))
