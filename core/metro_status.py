"""
Scraping (no API) del sitio oficial metrodemedellin.gov.co para mostrar
noticias/avisos de servicio, horarios y el semáforo de estado de líneas
en la sección de transporte alternativo del home (FR37 ampliado).

Tres piezas de datos:

1. Noticias del blog "Al Día Metro" — HTML estático, se lee con
   requests + BeautifulSoup sin problema (_scrape_news).

2 y 3. Horarios de operación Y el semáforo "Estado de las líneas" —
   ambos se pintan con JavaScript después de cargar la página (el sitio
   usa módulos personalizados de HubSpot), así que un simple
   requests.get() no los ve. Usamos un navegador headless (Playwright)
   para los dos, reutilizando la misma sesión de navegador
   (_scrape_via_browser).

   Sobre el semáforo específicamente: inspeccionando el DOM real (con
   las DevTools del navegador) se confirmó que el estado NO es texto
   ("Normal"/"Restringido"/"Sin operación") en ningún lado — es un
   COLOR que JavaScript escribe en el atributo style de un
   <span class="color-semaforo" style="background-color:rgba(r,g,b,a)">
   anidado dentro de cada <div class="semaforo-item">. El color de
   fondo del propio .semaforo-item es el color de marca de la línea
   (ej. Línea K siempre amarillo-verde), NO el estado — no hay que
   confundirlos. Además cada item trae:
     - div.nombre-linea      -> código de la línea (ej. "K")
     - span.tooltiptext      -> nombre de la ruta (ej. "Acevedo - Santo Domingo")
     - span.color-semaforo   -> el color real de estado (leer background-color)

   Clasificamos ese color a Normal/Restringido/Sin operación por canal
   RGB dominante (verde -> Normal, rojo+verde alto -> Restringido, rojo
   dominante -> Sin operación). Es una heurística de color, no un
   diccionario exacto de la paleta del Metro, así que puede necesitar
   ajuste si cambian sus colores.

   Playwright requiere instalación aparte en el servidor:
       pip install playwright
       playwright install chromium      # una sola vez, ~300 MB

   Si no está instalado, o el widget no carga a tiempo, las funciones
   devuelven listas vacías sin lanzar excepción — el resto de la página
   sigue funcionando con noticias.

El resultado completo se cachea (CACHE_TTL_SECONDS) para no golpear el
sitio del Metro ni abrir un navegador en cada carga del home — home.html
hace polling cada 5 minutos contra /metro-status/, pero el scraping real
(incluido abrir el navegador) solo ocurre cada 10 minutos.
"""

import re

import requests
from bs4 import BeautifulSoup
from django.core.cache import cache
from django.utils import timezone

METRO_HOME_URL = "https://www.metrodemedellin.gov.co"
METRO_USERS_URL = "https://www.metrodemedellin.gov.co/usuarios"

CACHE_KEY = "metro_status_data"
CACHE_TTL_SECONDS = 600  # 10 minutos

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ParqueandoAndoBot/1.0)"
}
REQUEST_TIMEOUT = 8

# Tiempo máximo esperando cada widget con el navegador headless. Si no
# cargó en este tiempo, seguimos sin él — nunca se queda pegado.
BROWSER_TIMEOUT_MS = 15000


def _fetch_html(url):
    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.text


def _scrape_news(html, limit=6):
    """
    Enlaces hacia /al-dia/noticias/... en la portada. No dependemos de
    una clase CSS específica (podría cambiar sin aviso); cualquier link
    a esa ruta con texto de título nos sirve.
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
    "Horarios: HH:MM ... - HH:MM ...", asociándolos con la categoría,
    tipo de día y línea(s) más recientes vistas antes de cada uno.
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
    """Intento estático (requests) — fallback por si algún día deja de requerir JS."""
    soup = BeautifulSoup(html, "html.parser")
    raw_lines = [ln.strip() for ln in soup.get_text(separator="\n").split("\n")]
    raw_lines = [ln for ln in raw_lines if ln]
    return _parse_schedule_lines(raw_lines, limit)


def _scrape_schedules_from_rendered_text(text, limit=20):
    """Mismo parser, pero sobre el texto YA renderizado por el navegador headless."""
    raw_lines = [ln.strip() for ln in text.split("\n")]
    raw_lines = [ln for ln in raw_lines if ln]
    return _parse_schedule_lines(raw_lines, limit)


# ── Semáforo de líneas (color real, no texto — ver docstring del módulo) ───────

_RGB_PATTERN = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)")
_HEX_PATTERN = re.compile(r"#([0-9a-fA-F]{6})\b")


def _parse_css_color(style_attr):
    """Extrae (r, g, b) de un atributo style con background-color, en rgb()/rgba() o #hex."""
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
    Heurística de color -> estado. El Metro no usa un texto fijo para
    esto, así que clasificamos por canal dominante:
      - Verde dominante          -> Normal
      - Rojo y verde altos, azul bajo (naranja/amarillo) -> Restringido
      - Rojo dominante, verde bajo -> Sin operación
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
    Lee el semáforo real desde el DOM ya renderizado: cada
    #semaforosDesk .semaforo-item trae el código de línea
    (.nombre-linea), el nombre de la ruta (.tooltiptext) y el color de
    estado real (.color-semaforo, leído de su style="background-color:...").
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

        rgb = _parse_css_color(style_attr)
        line_status.append({
            "line": line_code,
            "route": route_name,
            "status": _classify_status_color(rgb),
        })

    return line_status


def _scrape_via_browser():
    """
    Abre un único Chromium headless y lo reutiliza para las dos cosas
    que requieren JavaScript: el semáforo (portada) y los horarios
    (/usuarios). Nunca lanza excepción hacia arriba — si Playwright no
    está instalado o algo falla, devuelve ([], []).
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
                page.goto(METRO_HOME_URL, timeout=BROWSER_TIMEOUT_MS, wait_until="domcontentloaded")
                line_status = _extract_line_status_from_page(page)

                # --- Horarios (/usuarios) ---
                page.goto(METRO_USERS_URL, timeout=BROWSER_TIMEOUT_MS, wait_until="domcontentloaded")
                try:
                    # Deja correr el JS que pinta los horarios antes de leer el texto.
                    page.wait_for_timeout(2500)
                    rendered_text = page.inner_text("body")
                    schedules = _scrape_schedules_from_rendered_text(rendered_text)
                except Exception:
                    schedules = []
            finally:
                browser.close()
    except Exception:
        # Navegador no instalado, timeout, sitio caído, etc.
        return line_status, schedules

    return line_status, schedules


def fetch_metro_status():
    """Scraping real (sin caché). Usar get_metro_status() en vistas."""
    result = {
        "news": [],
        "schedules": [],
        "line_status": [],
        "fetched_at": timezone.now(),
        "ok": True,
        "error": None,
    }

    try:
        home_html = _fetch_html(METRO_HOME_URL)
        result["news"] = _scrape_news(home_html)
    except requests.RequestException as exc:
        result["ok"] = False
        result["error"] = f"No se pudo consultar metrodemedellin.gov.co: {exc}"

    line_status, schedules = _scrape_via_browser()
    result["line_status"] = line_status
    result["schedules"] = schedules

    # Fallback estático: por si algún día el Metro deja de requerir JS
    # para los horarios (o Playwright no está instalado y aun así
    # queremos intentar algo con requests, aunque probablemente vuelva
    # vacío igual).
    if not result["schedules"]:
        try:
            users_html = _fetch_html(METRO_USERS_URL)
            fallback_schedules = _scrape_schedules_from_html(users_html)
            if fallback_schedules:
                result["schedules"] = fallback_schedules
        except requests.RequestException:
            pass

    return result


def get_metro_status(force_refresh=False):
    """
    Devuelve el estado cacheado (CACHE_TTL_SECONDS). Si no hay caché o
    `force_refresh=True`, vuelve a scrapear metrodemedellin.gov.co.
    """
    if not force_refresh:
        cached = cache.get(CACHE_KEY)
        if cached is not None:
            return cached

    data = fetch_metro_status()
    cache.set(CACHE_KEY, data, CACHE_TTL_SECONDS)
    return data
