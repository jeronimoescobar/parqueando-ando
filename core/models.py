from django.db import models


class ParkingLot(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    total_capacity = models.PositiveIntegerField()
    occupied_spaces = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

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

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


