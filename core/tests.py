from django.test import TestCase
from django.urls import reverse
from .models import ParkingLot
from .parking_recommendation import recommend_parking_lot


class ParkingLotModelTest(TestCase):
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
        self.assertContains(response, "Parqueadero recomendado: Parqueadero Recomendado")

    def test_fr7_home_view_shows_occupancy_percentage(self):
        ParkingLot.objects.create(
            name="Parqueadero Detalle", slug="parqueadero-detalle",
            total_capacity=100, occupied_cars=30,
        )
        response = self.client.get(reverse("home"))
        self.assertContains(response, "30,0%")
        self.assertContains(response, "30 ocupadas")

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
        self.assertContains(response, "🚗 Carros: 103/103")
        self.assertContains(response, "🏍️ Motos: 4/4")
        self.assertContains(response, "♿ PMR: 3/3")


