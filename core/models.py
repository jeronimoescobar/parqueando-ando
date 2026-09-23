from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


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
    last_updated = models.DateTimeField(auto_now=True)

    # ── Ubicación en el mapa (Sprint 3) ────────────────────────────────────
    # Antes estas coordenadas estaban escritas a mano dentro de home.html,
    # así que el mapa no sabía nada de la base de datos: no podía pintar el
    # estado real de cada parqueadero ni actualizarse solo. Ahora viven aquí
    # y el mapa se dibuja a partir de los parqueaderos reales.
    latitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True,
        verbose_name="Latitud",
        help_text="Ej: 6.2018070. Si se deja vacío, el parqueadero no sale en el mapa.",
    )
    longitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True,
        verbose_name="Longitud",
        help_text="Ej: -75.5777196. Si se deja vacío, el parqueadero no sale en el mapa.",
    )

    # ── Búsqueda inteligente (Sprint 3) ────────────────────────────────────
    search_aliases = models.TextField(
        blank=True,
        default="",
        verbose_name="Otros nombres / como le dice la gente",
        help_text=(
            "Nombres alternativos separados por coma, para que la búsqueda "
            "los reconozca. Ej: 'norte, el de ingeniería, parqueadero de ing, "
            "el de arriba'. No hace falta repetir el nombre oficial."
        ),
    )

    @property
    def alias_list(self):
        """Los alias como lista limpia (sin vacíos ni espacios sobrantes)."""
        return [a.strip() for a in self.search_aliases.split(",") if a.strip()]

    @property
    def has_coordinates(self):
        return self.latitude is not None and self.longitude is not None

    # ── Plano del parqueadero (Sprint 2 — mapa interactivo por espacio) ─────
    layout_image = models.ImageField(
        upload_to="parking_layouts/",
        blank=True,
        null=True,
        verbose_name="Imagen del plano",
        help_text=(
            "Croquis/plano de fondo sobre el que se ubican los espacios "
            "(ParkingSpot) usando posiciones porcentuales (pos_x, pos_y)."
        ),
    )

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

    # Ocupación específica
    occupied_cars = models.PositiveIntegerField(default=0)
    occupied_motorcycles = models.PositiveIntegerField(default=0)
    occupied_accessibility = models.PositiveIntegerField(default=0)

    # ── Propiedades calculadas ─────────────────────────────────────────────
    @property
    def occupied_spaces(self):
        """Suma total de espacios ocupados calculada dinámicamente."""
        return self.occupied_cars + self.occupied_motorcycles + self.occupied_accessibility

    @property
    def occupancy_ratio(self):
        if self.total_capacity == 0:
            return 0.0
        return min(self.occupied_spaces / self.total_capacity, 1.0)

    @property
    def available_spaces(self):
        return max(self.total_capacity - self.occupied_spaces, 0)

    @property
    def available_cars(self):
        return max(self.capacity_cars - self.occupied_cars, 0)

    @property
    def available_motorcycles(self):
        return max(self.capacity_motorcycles - self.occupied_motorcycles, 0)

    @property
    def available_accessibility(self):
        return max(self.capacity_accessibility - self.occupied_accessibility, 0)

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
        """Porcentaje de ocupación (0-100), redondeado a 1 decimal, para FR7."""
        return round(self.occupancy_ratio * 100, 1)

    @property
    def occupancy_percentage_css(self):
        """Porcentaje formateado siempre con punto para evitar que CSS se rompa (ej. width: 70.1%)."""
        return str(round(self.occupancy_ratio * 100, 1)).replace(',', '.')

    @property
    def has_vehicle_type_breakdown(self):
        """Indica si el parqueadero tiene desglose por tipo de vehículo configurado."""
        return any([
            self.capacity_cars,
            self.capacity_motorcycles,
            self.capacity_accessibility,
        ])

    @property
    def spot_status_counts(self):
        """
        Cuenta cuántos ParkingSpot del plano están en cada estado
        (empty/occupied/unknown), aplicando el vencimiento por
        inactividad (ver ParkingSpot.display_status). Usado en el
        dashboard de administrador (FR16).
        """
        counts = {"empty": 0, "occupied": 0, "unknown": 0}
        for spot in self.spots.all():
            counts[spot.display_status] += 1
        return counts

    @property
    def has_spot_map(self):
        """Indica si este parqueadero ya tiene el plano montado (con spots)."""
        return self.spots.exists()

    @property
    def active_notices(self):
        """
        Avisos administrativos actualmente visibles para este parqueadero
        (ej. "Entrada Norte cerrada por obras"). Ver ParkingLotNotice.
        """
        return self.notices.filter(active=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ParkingSpot(models.Model):
    """
    Un espacio individual dentro del plano de un ParkingLot (FR26/FR27 y
    el mapa interactivo del Sprint 2).

    Los 4 parqueaderos son fijos (no se crean/eliminan desde /admin/), pero
    cada uno puede tener su propio conjunto de ParkingSpot para "montar" el
    plano: el administrador define, para cada espacio, su posición como
    porcentaje (pos_x, pos_y) sobre `ParkingLot.layout_image`. Como son
    porcentajes (0-100) y no píxeles, el plano se ve bien sin importar el
    tamaño de pantalla.

    El estado (status) lo reportan los usuarios directamente desde el mapa
    (ocupado / vacío / no se sabe) — ver core.views.update_spot_status.
    """

    VEHICLE_TYPES = [
        ("car", "Carro"),
        ("motorcycle", "Moto"),
        ("accessibility", "PMR"),
    ]

    STATUS_CHOICES = [
        ("empty", "Vacío"),
        ("occupied", "Ocupado"),
        ("unknown", "No se sabe"),
    ]

    # Si nadie actualiza un espacio en este tiempo, se vuelve a mostrar
    # como "No se sabe" (evita que quede un estado viejo mostrado como cierto).
    STALE_AFTER = timedelta(hours=3)

    lot = models.ForeignKey(ParkingLot, on_delete=models.CASCADE, related_name="spots")
    label = models.CharField(max_length=10, help_text="Ej: A1, B12, M03")
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES, default="car")

    pos_x = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name="Posición X (%)",
        help_text="Posición horizontal en porcentaje (0-100) sobre el plano.",
    )
    pos_y = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name="Posición Y (%)",
        help_text="Posición vertical en porcentaje (0-100) sobre el plano.",
    )

    # ── Apariencia de la casilla sobre el plano (editable desde /admin/) ────
    rotation = models.IntegerField(
        default=0,
        verbose_name="Rotación (grados)",
        help_text="Gira el rectángulo de la casilla, en grados (0-359). Útil para celdas en diagonal o perpendiculares al pasillo.",
    )
    width = models.PositiveIntegerField(
        default=42,
        verbose_name="Ancho (px)",
        help_text="Ancho del rectángulo de la casilla en píxeles.",
    )
    height = models.PositiveIntegerField(
        default=26,
        verbose_name="Alto (px)",
        help_text="Alto del rectángulo de la casilla en píxeles.",
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="unknown")
    status_updated_at = models.DateTimeField(null=True, blank=True)

    @property
    def display_status(self):
        """Estado a mostrar, considerando el vencimiento por inactividad."""
        if self.status != "unknown" and self.status_updated_at:
            if timezone.now() - self.status_updated_at > self.STALE_AFTER:
                return "unknown"
        return self.status

    def report_status(self, new_status):
        """Registra el nuevo estado reportado por un usuario desde el mapa."""
        self.status = new_status
        self.status_updated_at = timezone.now()
        self.save(update_fields=["status", "status_updated_at"])

    class Meta:
        ordering = ["label"]
        unique_together = [("lot", "label")]

    def __str__(self):
        return f"{self.lot.name} - {self.label}"


class ParkingLotNotice(models.Model):
    """
    Aviso administrativo para aclarar algo puntual de un parqueadero —
    ej. "Entrada Norte cerrada por obras", "Mantenimiento el viernes de
    8am a 12m". No es un reporte de ocupación (eso es ParkingReport, en
    la app `reports`); esto es información que el ADMINISTRADOR escribe
    directamente para los usuarios, gestionado desde /admin/ (FR17 —
    ver administration/admin.py: ParkingLotNoticeInline).

    Puede haber varios avisos por parqueadero a la vez (ej. uno sobre una
    entrada cerrada y otro sobre un evento especial). `active=False` deja
    el historial sin borrarlo, pero deja de mostrarse en el sitio — así
    el admin no tiene que borrar y volver a escribir el mismo aviso cada
    vez que deja de aplicar y vuelve a aplicar.
    """
    lot = models.ForeignKey(ParkingLot, on_delete=models.CASCADE, related_name="notices")
    message = models.TextField(
        verbose_name="Mensaje del aviso",
        help_text="Ej: 'Entrada Norte cerrada por obras hasta el viernes'.",
    )
    active = models.BooleanField(
        default=True,
        verbose_name="Activo (visible en el sitio)",
        help_text="Desmárcalo para ocultarlo sin borrar el historial.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Aviso de parqueadero"
        verbose_name_plural = "Avisos de parqueadero"

    def __str__(self):
        preview = self.message if len(self.message) <= 40 else f"{self.message[:40]}..."
        return f"{self.lot.name}: {preview}"


class FavoriteParkingLot(models.Model):
    """
    Un parqueadero marcado como favorito (Sprint 3).

    ─────────────────────────────────────────────────────────────────────
    NOTA PARA QUIEN IMPLEMENTE USUARIOS Y LOGIN
    ─────────────────────────────────────────────────────────────────────
    Este modelo ya está preparado para usuarios, pero NO depende de que
    el login exista todavía. Funciona en dos modos:

      * Sin login (hoy):  user=None  + session_key = la sesión del navegador.
      * Con login:        user=<User> + session_key vacío.

    `user` es un ForeignKey a settings.AUTH_USER_MODEL (no a auth.User
    directamente), así que si se define un modelo de usuario propio,
    esto sigue funcionando sin migración manual.

    El login (FR2, core/auth_views.py) ya pasa los favoritos que la
    persona marcó como anónima a su cuenta recién iniciada, sin
    duplicar. Si se hace login desde otro lugar (ej. el registro), usar
    `core.auth_views.log_user_in(request, user)`.
    ─────────────────────────────────────────────────────────────────────
    """

    lot = models.ForeignKey(ParkingLot, on_delete=models.CASCADE, related_name="favorited_by")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_parking_lots",
        null=True,
        blank=True,
        help_text="Queda vacío mientras la persona no haya iniciado sesión.",
    )

    session_key = models.CharField(
        max_length=40,
        blank=True,
        default="",
        db_index=True,
        help_text=(
            "Sesión del navegador, para recordar favoritos de visitantes "
            "sin cuenta. Se limpia cuando el favorito pasa a un usuario."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Parqueadero favorito"
        verbose_name_plural = "Parqueaderos favoritos"
        constraints = [
            # Un usuario no puede tener el mismo parqueadero dos veces...
            models.UniqueConstraint(
                fields=["user", "lot"],
                condition=models.Q(user__isnull=False),
                name="unique_favorite_per_user",
            ),
            # ...ni una sesión anónima tampoco.
            models.UniqueConstraint(
                fields=["session_key", "lot"],
                condition=models.Q(user__isnull=True),
                name="unique_favorite_per_session",
            ),
        ]

    def __str__(self):
        owner = self.user or f"sesión {self.session_key[:8]}"
        return f"{owner} ♥ {self.lot.name}"

class ParkingRule(models.Model):
    """
    Reglas y restricciones específicas para los parqueaderos (FR29).
    Ejemplo: Pico y placa, tarifas, reglas de pernoctada, etc.
    """
    lot = models.ForeignKey(ParkingLot, on_delete=models.CASCADE, related_name="rules")
    description = models.TextField(help_text="Descripción de la regla")

    class Meta:
        ordering = ["id"]
        verbose_name = "Regla de parqueadero"
        verbose_name_plural = "Reglas de parqueaderos"

    def __str__(self):
        return f"{self.lot.name} - Regla {self.id}"
