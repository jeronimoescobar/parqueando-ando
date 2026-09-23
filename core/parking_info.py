"""
Información general de los parqueaderos de EAFIT (FR35).

Mismo patrón que transport_links.py: todo el contenido vive aquí, como
datos, y el template solo lo pinta. Si cambia una tarifa, un horario o un
teléfono, se edita ESTE archivo — no hace falta tocar vistas ni HTML.

Fuente: https://www.eafit.edu.co/pago-de-parqueaderos (y reglamento de
parqueaderos de EAFIT). Los valores pueden cambiar; revisar cada semestre.

Los horarios están escritos dos veces a propósito:
  - `schedule`: el texto tal como se le muestra a la persona.
  - `open_hours`: la misma información en formato que Python entiende,
    para poder decir "Abierto ahora" / "Cerrado ahora" en la página.
Si cambias uno, cambia el otro.
"""

from datetime import time

from django.utils import timezone

SOURCE_URL = "https://www.eafit.edu.co/pago-de-parqueaderos"

# Días de la semana como los numera Python: lunes=0 ... domingo=6.
WEEKDAYS = range(0, 5)
SATURDAY = 5
SUNDAY = 6


def _weekly(weekdays=None, saturday=None, sunday=None):
    """Arma el dict día -> [(abre, cierra), ...] a partir de rangos simples."""
    hours = {}
    for day in WEEKDAYS:
        hours[day] = list(weekdays or [])
    hours[SATURDAY] = list(saturday or [])
    hours[SUNDAY] = list(sunday or [])
    return hours


# ── Horarios por parqueadero ─────────────────────────────────────────────────
# `slug` coincide con ParkingLot.slug (ver core/migrations/0006), así la
# página puede mostrar al lado la disponibilidad en vivo de cada uno.
LOTS_INFO = [
    {
        "slug": "parqueadero-norte",
        "name": "Parqueadero Norte",
        "schedule": [
            ("Lunes a viernes", "5:00 a. m. – 10:30 p. m."),
            ("Sábados", "6:00 a. m. – 6:00 p. m."),
            ("Domingos y festivos", "Cerrado"),
        ],
        "open_hours": _weekly(
            weekdays=[(time(5, 0), time(22, 30))],
            saturday=[(time(6, 0), time(18, 0))],
        ),
    },
    {
        "slug": "parqueadero-sur",
        "name": "Parqueadero Sur",
        "schedule": [
            ("Lunes a viernes", "5:00 a. m. – 10:30 p. m."),
            ("Sábados", "5:00 a. m. – 7:00 p. m. por la portería de Las Vegas · "
                        "6:00 a. m. – 6:00 p. m. por Ingenierías"),
            ("Domingos y festivos", "6:00 a. m. – 6:00 p. m. por Las Vegas · "
                                    "Ingenierías cerrado"),
        ],
        "open_hours": _weekly(
            weekdays=[(time(5, 0), time(22, 30))],
            saturday=[(time(5, 0), time(19, 0))],
            sunday=[(time(6, 0), time(18, 0))],
        ),
    },
    {
        "slug": "parque-los-guayabos",
        "name": "Parque Los Guayabos",
        "schedule": [
            ("Lunes a viernes", "5:00 a. m. – 10:30 p. m."),
            ("Sábados", "6:00 a. m. – 6:00 p. m."),
            ("Domingos y festivos", "Cerrado"),
        ],
        "open_hours": _weekly(
            weekdays=[(time(5, 0), time(22, 30))],
            saturday=[(time(6, 0), time(18, 0))],
        ),
    },
    {
        "slug": "parqueadero-de-empleados",
        "name": "Parqueadero de Empleados",
        # EAFIT no publica un horario para este parqueadero. Cuando se
        # conozca, llenar `schedule` y `open_hours` igual que los demás.
        "schedule": [],
        "open_hours": None,
    },
]


# ── Tarifas ──────────────────────────────────────────────────────────────────
RATES = [
    {
        "user_type": "Estudiantes, profesores, empleados y contratistas",
        "car": "$8.700 / día",
        "motorcycle": "$4.300 / día",
    },
    {
        "user_type": "Graduados",
        "car": "$3.800 / hora — máx. $13.500 / día",
        "motorcycle": "$2.500 / hora — máx. $10.000 / día",
    },
    {
        "user_type": "Visitantes",
        "car": "$5.400 / hora — máx. $21.300 / día",
        "motorcycle": "$4.000 / hora — máx. $16.000 / día",
    },
    {
        "user_type": "Vehículos 100 % eléctricos",
        "car": "$5.000 / día",
        "motorcycle": "$3.000 / día",
    },
]


# ── Dónde pagar ──────────────────────────────────────────────────────────────
PAYMENT_POINTS = [
    "Bloque 20 – piso 1",
    "Bloque 18 – piso 1",
    "Bloque 33 – piso 1",
    "Bloque 38 – piso 1",
    "Bloque 1 – piso 5",
]

ONLINE_PAYMENT_NOTE = (
    "También puedes pagar el tiquete en línea y recargar el carné en línea."
)


# ── Cómo entrar ──────────────────────────────────────────────────────────────
ENTRY_OPTIONS = [
    {
        "title": "Estudiantes y comunidad con carné",
        "icon": "🎓",
        "items": [
            "Ingreso con el carné de EAFIT.",
            "O por lectura de la placa registrada (usuarios carnetizados).",
        ],
    },
    {
        "title": "Visitantes o sin carné activo",
        "icon": "🎫",
        "items": [
            "Presiona “TIQUETE” en la máquina de entrada.",
            "Guarda el tiquete con código de barras: con él pagas al salir.",
        ],
    },
]

GRACE_PERIOD_NOTE = (
    "Hay 30 minutos de gracia para la comunidad en general. Los visitantes, "
    "después de pagar el tiquete, tienen 30 minutos para salir."
)


# ── Normas básicas ───────────────────────────────────────────────────────────
RULES = [
    "Solo se puede estacionar en las celdas habilitadas.",
    "No se permite estacionar en zonas de circulación ni en vías perimetrales.",
    "No se pueden ocupar las celdas reservadas para personas con movilidad reducida.",
    "No se permite entregar las llaves del vehículo al personal de seguridad.",
    "No se permite realizar trabajos de mecánica dentro del parqueadero.",
    "Cuando un parqueadero llega a su capacidad máxima, se cierra temporalmente "
    "el ingreso hasta que se liberen espacios.",
    "Los domingos y festivos el servicio de parqueadero es gratuito, según el reglamento.",
    "EAFIT aplica las restricciones de pico y placa correspondientes.",
    "Los vehículos 100 % eléctricos tienen condiciones especiales de parqueo y "
    "tarifas diferenciadas.",
]


# ── Contacto ─────────────────────────────────────────────────────────────────
CONTACTS = [
    {
        "title": "Lectoras de entrada/salida o puntos de pago",
        "icon": "🛠️",
        "lines": [
            {"label": "Extensión", "value": "8744"},
            {"label": "Teléfono", "value": "(604) 261 93 07", "href": "tel:+576042619307"},
        ],
        "note": "También puedes reportar la novedad al personal de vigilancia.",
    },
    {
        "title": "Consultas sobre pagos",
        "icon": "💬",
        "lines": [
            {"label": "WhatsApp", "value": "+57 322 948 7540", "href": "https://wa.me/573229487540"},
            {"label": "Correo", "value": "parqueadero@eafit.edu.co", "href": "mailto:parqueadero@eafit.edu.co"},
        ],
        "note": "Atención: lunes a viernes 6:00 a. m. – 10:00 p. m. y sábados 6:00 a. m. – 5:00 p. m.",
    },
]


# ── Lógica ───────────────────────────────────────────────────────────────────


def is_open_at(open_hours, moment):
    """
    ¿Está abierto el parqueadero en `moment` (datetime con zona horaria)?
    Devuelve None si no hay horario publicado.

    Ojo: no sabe de festivos (un festivo entre semana lo trata como día
    normal). La página lo aclara al lado del indicador.
    """
    if open_hours is None:
        return None
    local = timezone.localtime(moment)
    now = local.time()
    return any(start <= now < end for start, end in open_hours.get(local.weekday(), []))


def lots_with_status(parking_lots_by_slug=None, moment=None):
    """
    LOTS_INFO + "abierto ahora" + (si existe en la base de datos) el
    ParkingLot correspondiente, para mostrar su disponibilidad en vivo.
    """
    moment = moment or timezone.now()
    parking_lots_by_slug = parking_lots_by_slug or {}

    result = []
    for info in LOTS_INFO:
        result.append({
            **info,
            "is_open": is_open_at(info["open_hours"], moment),
            "lot": parking_lots_by_slug.get(info["slug"]),
        })
    return result
