from django.test import TestCase
from django.urls import reverse
from .models import ParkingLot


class ParkingLotModelTest(TestCase):
    def test_create_parking_lot(self):
        lot = ParkingLot.objects.create(
            name="Parqueadero Central",
            slug="parqueadero-central",
            total_capacity=100,
            occupied_spaces=25,
        )
        self.assertEqual(str(lot), "Parqueadero Central")
        self.assertAlmostEqual(lot.occupancy_ratio, 0.25)
        self.assertEqual(lot.available_spaces, 75)


    def test_occupancy_ratio_zero_capacity(self):
        lot = ParkingLot.objects.create(
            name="Vacío",
            slug="vacio",
            total_capacity=0,
            occupied_spaces=0,
        )
        self.assertEqual(lot.occupancy_ratio, 0.0)

    def test_fr6_occupancy_status(self):
        available_lot = ParkingLot.objects.create(
            name="Libre", slug="libre", total_capacity=100, occupied_spaces=20
        )
        limited_lot = ParkingLot.objects.create(
            name="Limitado", slug="limitado", total_capacity=100, occupied_spaces=80
        )
        full_lot = ParkingLot.objects.create(
            name="Lleno", slug="lleno", total_capacity=100, occupied_spaces=100
        )
        self.assertEqual(available_lot.occupancy_status, "available")
        self.assertEqual(available_lot.occupancy_status_display, "Disponible")

        self.assertEqual(limited_lot.occupancy_status, "limited")
        self.assertEqual(limited_lot.occupancy_status_display, "Limitado")

        self.assertEqual(full_lot.occupancy_status, "full")
        self.assertEqual(full_lot.occupancy_status_display, "Lleno")


class HomeViewTest(TestCase):
    def test_home_view_displays_parking_lots(self):
        lot1 = ParkingLot.objects.create(
            name="Parqueadero Sur",
            slug="parqueadero-sur",
            total_capacity=50,
            occupied_spaces=10,
        )
        lot2 = ParkingLot.objects.create(
            name="Parqueadero Norte",
            slug="parqueadero-norte",
            total_capacity=80,
            occupied_spaces=40,
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
            occupied_spaces=50,
        )
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PARQUEADERO LLENO")

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
        self.assertContains(response, "Carros: 103")
        self.assertContains(response, "Motos: 4")
        self.assertContains(response, "Movilidad reducida: 3")


