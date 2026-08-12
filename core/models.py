from django.db import models


class ParkingLot(models.Model):
    """
    Representa un parqueadero del campus EAFIT.

    Campos principales (FR5 & FR6):
        - name, slug, total_capacity, occupied_spaces, last_updated

    Desglose por tipo de vehículo (Weekly 3 — vehicle-type differentiation):
        capacity_cars, capacity_motorcycles, capacity_accessibility.
        Son configurados por el administrador en /admin/.
    """

    # ── Información general ────────────────────────────────────────────────
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    total_capacity = models.PositiveIntegerField()
    occupied_spaces = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    # ── Desglose de capacidad por tipo de vehículo (Weekly 3) ──────────────
    capacity_cars = models.PositiveIntegerField(
        default=0,
        verbose_name="Celdas para carros",
    )
    capacity_motorcycles = models.PositiveIntegerField(
        default=0,
        verbose_name="Celdas para motos",
    )
    capacity_accessibility = models.PositiveIntegerField(
        default=0,
        verbose_name="Celdas para personas con movilidad reducida (PMR)",
    )

    # ── Propiedades calculadas ─────────────────────────────────────────────
    @property
    def occupancy_ratio(self):
        if self.total_capacity == 0:
            return 0.0
        return min(self.occupied_spaces / self.total_capacity, 1.0)

    @property
    def available_spaces(self):
        return max(self.total_capacity - self.occupied_spaces, 0)

    @property
    def occupancy_status(self):
        """Devuelve el estado de ocupación según FR6: 'available', 'limited', o 'full'."""
        if self.total_capacity == 0 or self.occupied_spaces >= self.total_capacity:
            return "full"
        elif self.occupancy_ratio >= 0.70:
            return "limited"
        return "available"

    @property
    def occupancy_status_display(self):
        """Devuelve la etiqueta legible del estado de ocupación."""
        status = self.occupancy_status
        if status == "full":
            return "Lleno"
        elif status == "limited":
            return "Limitado"
        return "Disponible"

    @property
    def occupancy_percentage(self):
        """Porcentaje de ocupación (0-100), redondeado, para FR7."""
        return round(self.occupancy_ratio * 100)

    @property
    def has_vehicle_type_breakdown(self):
        """Indica si el parqueadero tiene desglose por tipo de vehículo configurado."""
        return any([
            self.capacity_cars,
            self.capacity_motorcycles,
            self.capacity_accessibility,
        ])

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
