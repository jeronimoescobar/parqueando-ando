"""
Scraping del sitio oficial metrodemedellin.gov.co (noticias, horarios y
semáforo de estado de líneas) para la sección de transporte del home.

═══════════════════════════════════════════════════════════════════════
POR QUÉ ESTE ARCHIVO SE REESCRIBIÓ EN EL SPRINT 3
═══════════════════════════════════════════════════════════════════════
La versión anterior tenía tres problemas que se notaban en la página:

1. BLOQUEABA LA PÁGINA. `get_metro_status()` hacía el scraping dentro
   del request: si la caché estaba vencida, abrir Chromium y esperar al
   sitio del Metro podía tardar 20-30 segundos, y el home entero se
   quedaba cargando ese tiempo. Con internet lento o caído, peor.

   Ahora el request NUNCA scrapea. Lee lo que haya en caché y responde
   de una; si los datos están viejos, lanza el scraping en un hilo
   aparte y responde igual, con los datos anteriores marcados como
   "actualizando". La página nunca espera.

2. UN FALLO BORRABA LOS DATOS BUENOS. El resultado se guardaba completo
   en caché aunque viniera vacío. Si un scrape fallaba (o el semáforo no
   alcanzaba a cargar), se cacheaban listas vacías ENCIMA de los datos
   buenos y la sección quedaba en blanco 10 minutos. Por eso "a veces
   los estados de las líneas quedan vacíos".

   Ahora cada sección (noticias / horarios / semáforo) se guarda por
   separado con su propia marca de tiempo, y si una vuelve vacía se
   CONSERVA la anterior. Se pierde frescura, nunca contenido.

3. EL "ACTUALIZADO HACE X" NO CAMBIABA. Había una sola marca de tiempo
   para todo y se congelaba cuando el scrape fallaba o se colgaba. Ahora
   cada sección reporta su propio `fetched_at`, y además se expone
   `last_attempt_at` (último intento, exitoso o no), así el navegador
   siempre tiene algo real que mostrar.
═══════════════════════════════════════════════════════════════════════

Sobre el semáforo: el estado NO es texto ("Normal"/"Restringido") en
ningún lado del HTML — es un COLOR que JavaScript escribe en
<span class="color-semaforo" style="background-color:rgba(r,g,b,a)">
dentro de cada <div class="semaforo-item">. Por eso hace falta un
navegador headless (Playwright) para leerlo; con requests solo se ve el
ícono de "cargando". Ojo: el color de fondo del propio .semaforo-item es
el color de marca de la línea, NO el estado.

Playwright es OPCIONAL:
    pip install playwright && playwright install chromium
Sin él, las noticias siguen funcionando (esas sí son HTML estático) y el
semáforo/horarios quedan vacíos sin romper nada.
"""

import re
import threading

import requests
from bs4 import BeautifulSoup
from django.core.cache import cache
from django.utils import timezone

METRO_HOME_URL = "https://www.metrodemedellin.gov.co"
METRO_USERS_URL = "https://www.metrodemedellin.gov.co/usuarios"

CACHE_KEY = "metro_status_data"
# Cuánto tiempo consideramos "fresco" un dato antes de querer refrescarlo.
FRESH_FOR_SECONDS = 600  # 10 minutos
# La caché guarda los datos mucho más tiempo del que los considera
# frescos: así, si el scraping falla varias veces seguidas, todavía
# tenemos los últimos datos buenos para mostrar en vez de una pantalla
# vacía (se muestran marcados como desactualizados).
CACHE_TTL_SECONDS = 60 * 60 * 24  # 24 horas

# Evita que dos peticiones simultáneas lancen dos Chromium a la vez.
_refresh_lock = threading.Lock()
_refresh_in_progress = False

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ParqueandoAndoBot/1.0)"
}
REQUEST_TIMEOUT = 8
BROWSER_TIMEOUT_MS = 15000


def _empty_state():
    """Estado inicial cuando nunca se ha scrapeado nada."""
    return {
        "news": [],
        "schedules": [],
        "line_status": [],
        # Marca de tiempo POR SECCIÓN: cuándo se obtuvo cada una con éxito.
        "news_fetched_at": None,
        "schedules_fetched_at": None,
        "line_status_fetched_at": None,
        # Último intento (haya salido bien o mal).
        "last_attempt_at": None,
        "ok": True,
        "error": None,
        "refreshing": False,
    }


def _fetch_html(url):
    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.text


def _friendly_connection_error(exc):
    """
    Traduce la excepción técnica a algo que ayude a diagnosticar. La
    mayoría de las veces esto NO es un bug del scraper: es que la máquina
    donde corre Django no tiene salida a internet (sin wifi, firewall,
    antivirus, VPN corporativa, DNS caído).

    Señal típica: "NameResolutionError" / "getaddrinfo failed" (Windows)
    o "Name or service not known" (Linux) — la petición ni siquiera
    alcanzó a salir de la máquina.
    """
    text = str(exc)
    if "NameResolutionError" in text or "getaddrinfo failed" in text or "Name or service not known" in text:
        return (
            "Sin conexión a internet en el servidor: no se pudo resolver "
            "metrodemedellin.gov.co. Se sigue mostrando la última "
            "información conocida y se reintenta solo."
        )
    if isinstance(exc, requests.exceptions.Timeout):
        return (
            f"metrodemedellin.gov.co no respondió a tiempo (más de "
            f"{REQUEST_TIMEOUT}s). Se reintenta solo en unos minutos."
        )
    return f"No se pudo consultar metrodemedellin.gov.co: {exc}"


def _scrape_news(html, limit=6):
    """
    Enlaces hacia /al-dia/noticias/... en la portada. No dependemos de una
    clase CSS específica (podría cambiar sin aviso); cualquier link a esa
    ruta con texto de título nos sirve.
    """
    soup = BeautifulSoup(html, "html.parser")
    news = []
    seen_urls = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/al-dia/noticias/" not in href or "/tag/" in href:
            continue
        title = a.get_text(strip=True)
        if not title or len(title) < 15:
            continue
        url = href if href.startswith("http") else f"{METRO_HOME_URL}{href}"
        if url in seen_urls:
            continue
        seen_urls.add(url)
        news.append({"title": title, "url": url})
        if len(news) >= limit:
            break

    return news


# ── Horarios ─────────────────────────────────────────────────────────────────

_SCHEDULE_CATEGORY_PATTERNS = [
    ("Metro / Metrocable / Tranvía / Buses", re.compile(r"Horarios del Metro de Medell", re.IGNORECASE)),
    ("Metrocable Santo Domingo - Arví (Línea L)", re.compile(r"Horarios del Metrocable Santo Domingo", re.IGNORECASE)),
    ("Puntos de venta (PDV)", re.compile(r"Horarios puntos de venta", re.IGNORECASE)),
    ("Ingreso de bicicletas", re.compile(r"Horarios para ingreso de bicicletas", re.IGNORECASE)),
]
_SCHEDULE_STOP_PATTERN = re.compile(r"Reglamentos del usuario", re.IGNORECASE)
_DAY_TYPE_PATTERN = re.compile(
    r"(lunes|martes|mi[ée]rcoles|jueves|viernes|s[áa]bado|domingo)", re.IGNORECASE
)
_LINE_CODES_PATTERN = re.compile(r"^[A-Z0-9](?:[-\s][A-Z0-9]+)*$")


def _parse_schedule_lines(raw_lines, limit=20):
    """
    Recorre el texto (ya separado en líneas) buscando bloques
    "Horarios: HH:MM ... - HH:MM ...", asociándolos con la categoría, tipo
    de día y línea(s) más recientes vistas antes de cada uno.
    """
    schedules = []
    seen = set()
    current_category = None
    current_day_type = None
    current_lines_label = None

    for line in raw_lines:
        if _SCHEDULE_STOP_PATTERN.search(line):
            break

        matched_category = next(
            (label for label, pattern in _SCHEDULE_CATEGORY_PATTERNS if pattern.search(line)),
            None,
        )
        if matched_category:
            current_category = matched_category
            current_day_type = None
            current_lines_label = None
            continue

        if current_category is None:
            continue

        horario_match = re.match(r"Horarios:\s*(.+)", line)
        if horario_match:
            hours = horario_match.group(1).strip(" *")
            key = (current_category, current_day_type, current_lines_label, hours)
            if hours and key not in seen:
                seen.add(key)
                schedules.append({
                    "category": current_category,
                    "day_type": current_day_type,
                    "lines": current_lines_label,
                    "hours": hours,
                })
            current_lines_label = None
            continue

        if _DAY_TYPE_PATTERN.search(line) and len(line) < 60:
            current_day_type = line
            current_lines_label = None
            continue

        if len(line) <= 30 and _LINE_CODES_PATTERN.match(line):
            current_lines_label = line
            continue

        if len(schedules) >= limit:
            break

    return schedules[:limit]


def _scrape_schedules_from_html(html, limit=20):
    """Intento estático (requests) — fallback por si deja de requerir JS."""
    soup = BeautifulSoup(html, "html.parser")
    raw_lines = [ln.strip() for ln in soup.get_text(separator="\n").split("\n")]
    raw_lines = [ln for ln in raw_lines if ln]
    return _parse_schedule_lines(raw_lines, limit)


def _scrape_schedules_from_rendered_text(text, limit=20):
    """Mismo parser, sobre el texto YA renderizado por el navegador."""
    raw_lines = [ln.strip() for ln in text.split("\n")]
    raw_lines = [ln for ln in raw_lines if ln]
    return _parse_schedule_lines(raw_lines, limit)


# ── Semáforo de líneas (color real, no texto — ver docstring del módulo) ──────

_RGB_PATTERN = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)")
_HEX_PATTERN = re.compile(r"#([0-9a-fA-F]{6})\b")


def _parse_css_color(style_attr):
    """Extrae (r, g, b) de un style con background-color, en rgb()/rgba() o #hex."""
    if not style_attr:
        return None
    m = _RGB_PATTERN.search(style_attr)
    if m:
        return tuple(int(m.group(i)) for i in (1, 2, 3))
    m = _HEX_PATTERN.search(style_attr)
    if m:
        hex_value = m.group(1)
        return tuple(int(hex_value[i:i + 2], 16) for i in (0, 2, 4))
    return None


def _classify_status_color(rgb):
    """
    Heurística de color -> estado, porque el Metro no publica un texto
    fijo para esto:
      - Verde dominante               -> Normal
      - Rojo y verde altos, azul bajo -> Restringido (naranja/amarillo)
      - Rojo dominante, verde bajo    -> Sin operación
    """
    if rgb is None:
        return "Desconocido"
    r, g, b = rgb
    if g >= r and g >= b and g > 100:
        return "Normal"
    if r > 150 and g > 90 and b < 120:
        return "Restringido"
    if r > 120 and g < 100:
        return "Sin operación"
    return "Desconocido"


def _extract_line_status_from_page(page):
    """
    Lee el semáforo desde el DOM ya renderizado: cada
    #semaforosDesk .semaforo-item trae el código de línea (.nombre-linea),
    el nombre de la ruta (.tooltiptext) y el color real de estado
    (.color-semaforo, leído de su style="background-color:...").
    """
    try:
        page.wait_for_selector("#semaforosDesk .semaforo-item", timeout=BROWSER_TIMEOUT_MS)
    except Exception:
        return []

    items = page.query_selector_all("#semaforosDesk .semaforo-item")
    line_status = []
    for item in items:
        try:
            nombre_el = item.query_selector(".nombre-linea")
            tooltip_el = item.query_selector(".tooltiptext")
            color_el = item.query_selector(".color-semaforo")
            line_code = nombre_el.text_content().strip() if nombre_el else None
            route_name = tooltip_el.text_content().strip() if tooltip_el else None
            style_attr = color_el.get_attribute("style") if color_el else None
        except Exception:
            continue

        if not line_code:
            continue

        line_status.append({
            "line": line_code,
            "route": route_name,
            "status": _classify_status_color(_parse_css_color(style_attr)),
        })

    return line_status


def _scrape_via_browser():
    """
    Abre un único Chromium headless y lo reutiliza para las dos cosas que
    requieren JavaScript: el semáforo (portada) y los horarios
    (/usuarios). Nunca lanza excepción hacia arriba: si Playwright no está
    instalado o algo falla, devuelve lo que alcanzó a obtener.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return [], []

    line_status = []
    schedules = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(user_agent=REQUEST_HEADERS["User-Agent"])

                # --- Semáforo de líneas (portada) ---
                try:
                    page.goto(METRO_HOME_URL, timeout=BROWSER_TIMEOUT_MS, wait_until="domcontentloaded")
                    line_status = _extract_line_status_from_page(page)
                except Exception:
                    line_status = []

                # --- Horarios (/usuarios) ---
                try:
                    page.goto(METRO_USERS_URL, timeout=BROWSER_TIMEOUT_MS, wait_until="domcontentloaded")
                    page.wait_for_timeout(2500)  # deja correr el JS que los pinta
                    schedules = _scrape_schedules_from_rendered_text(page.inner_text("body"))
                except Exception:
                    schedules = []
            finally:
                browser.close()
    except Exception:
        return line_status, schedules

    return line_status, schedules


def _scrape_everything():
    """
    Hace el scraping completo y devuelve SOLO lo que consiguió, sin
    mezclarlo todavía con lo anterior. Quien llama decide qué conservar
    (ver `_merge_into_cache`). Nunca lanza excepción.
    """
    fresh = {"news": [], "schedules": [], "line_status": [], "error": None}

    try:
        fresh["news"] = _scrape_news(_fetch_html(METRO_HOME_URL))
    except requests.RequestException as exc:
        fresh["error"] = _friendly_connection_error(exc)
    except Exception as exc:  # parser roto, HTML inesperado, etc.
        fresh["error"] = f"No se pudieron leer las noticias del Metro: {exc}"

    line_status, schedules = _scrape_via_browser()
    fresh["line_status"] = line_status
    fresh["schedules"] = schedules

    # Fallback estático para horarios, por si dejan de requerir JS.
    if not fresh["schedules"]:
        try:
            fresh["schedules"] = _scrape_schedules_from_html(_fetch_html(METRO_USERS_URL))
        except Exception:
            pass

    return fresh


def _merge_into_cache(fresh):
    """
    Combina lo recién scrapeado con lo que ya había, SECCIÓN POR SECCIÓN.

    Regla clave: una sección que vuelve vacía NO borra la anterior. Es
    mejor mostrar el semáforo de hace 20 minutos (marcado como viejo) que
    mostrar un espacio en blanco. Cada sección conserva la marca de tiempo
    de la última vez que sí trajo datos.
    """
    current = cache.get(CACHE_KEY) or _empty_state()
    now = timezone.now()

    merged = dict(current)
    for section in ("news", "schedules", "line_status"):
        if fresh.get(section):
            merged[section] = fresh[section]
            merged[f"{section}_fetched_at"] = now
        # si vino vacío, se deja tal cual lo que ya estaba

    merged["last_attempt_at"] = now
    merged["refreshing"] = False

    got_something = any(fresh.get(s) for s in ("news", "schedules", "line_status"))
    if fresh.get("error"):
        merged["ok"] = False
        merged["error"] = fresh["error"]
    elif not got_something:
        merged["ok"] = False
        merged["error"] = (
            "No se pudo obtener información nueva del Metro en este intento. "
            "Se muestra la última información conocida."
        )
    else:
        merged["ok"] = True
        merged["error"] = None

    cache.set(CACHE_KEY, merged, CACHE_TTL_SECONDS)
    return merged


def _background_refresh():
    """Corre el scraping fuera del request y guarda el resultado combinado."""
    global _refresh_in_progress
    try:
        _merge_into_cache(_scrape_everything())
    except Exception:
        # Pase lo que pase, nunca dejamos la bandera trabada: si no, no se
        # volvería a intentar mientras el proceso siga vivo.
        state = cache.get(CACHE_KEY) or _empty_state()
        state["refreshing"] = False
        state["last_attempt_at"] = timezone.now()
        cache.set(CACHE_KEY, state, CACHE_TTL_SECONDS)
    finally:
        with _refresh_lock:
            _refresh_in_progress = False


def _is_stale(state):
    """¿Ya toca refrescar? Se mira el último INTENTO, no el último éxito."""
    last_attempt = state.get("last_attempt_at")
    if last_attempt is None:
        return True
    return (timezone.now() - last_attempt).total_seconds() >= FRESH_FOR_SECONDS


def trigger_refresh_if_stale(state):
    """
    Lanza el scraping en segundo plano si hace falta y devuelve si quedó
    uno corriendo. Nunca espera a que termine: el request sigue de una.
    """
    global _refresh_in_progress

    if not _is_stale(state):
        return False

    with _refresh_lock:
        if _refresh_in_progress:
            return True  # ya hay uno corriendo; no lanzamos otro
        _refresh_in_progress = True

    threading.Thread(target=_background_refresh, daemon=True).start()
    return True


def get_metro_status():
    """
    Devuelve el estado del Metro SIN BLOQUEAR NUNCA.

    Lee lo que haya en caché y responde de inmediato. Si esos datos ya
    están viejos, dispara el refresco en segundo plano y responde igual
    (con `refreshing: True`, para que la interfaz pueda mostrar que se
    está actualizando). La página jamás espera al sitio del Metro.
    """
    state = cache.get(CACHE_KEY) or _empty_state()
    refreshing = trigger_refresh_if_stale(state)
    state = dict(state)
    state["refreshing"] = refreshing
    return state


def serialize_metro_status(state):
    """Convierte el estado a JSON-friendly (fechas en ISO) para la API."""
    def iso(value):
        return value.isoformat() if value else None

    return {
        "news": state.get("news", []),
        "schedules": state.get("schedules", []),
        "line_status": state.get("line_status", []),
        "news_fetched_at": iso(state.get("news_fetched_at")),
        "schedules_fetched_at": iso(state.get("schedules_fetched_at")),
        "line_status_fetched_at": iso(state.get("line_status_fetched_at")),
        "last_attempt_at": iso(state.get("last_attempt_at")),
        "ok": state.get("ok", True),
        "error": state.get("error"),
        "refreshing": state.get("refreshing", False),
    }
