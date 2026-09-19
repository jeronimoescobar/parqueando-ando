# Parqueando Ando

Sistema web para consultar y reportar la disponibilidad de los parqueaderos del campus.

## Instalación

```bash
cd parqueando-ando
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux

pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abre [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

Los 4 parqueaderos del campus se crean solos al correr `migrate`, ya con sus
coordenadas y sus apodos de búsqueda.

## Rutas principales

| Ruta | Qué es | Acceso |
|---|---|---|
| `/` | Home: buscador, mapa, disponibilidad, plano interactivo, reportes | Público |
| `/parking/<slug>/` | Detalle de un parqueadero | Público |
| `/dashboard/` | Panel de administrador | Solo staff |
| `/dashboard/mapper/<slug>/` | Mapeador visual del plano | Solo staff |
| `/dashboard/reports/` | Gestión de reportes de usuarios | Solo staff |
| `/admin/` | Admin de Django (parqueaderos, planos, avisos, coordenadas, apodos) | Solo staff |

El login de `/dashboard/` y `/admin/` es el mismo usuario.

### APIs internas (las usa el home para actualizarse solo)

| Ruta | Devuelve |
|---|---|
| `/api/lots/` | Estado actual de todos los parqueaderos |
| `/api/search/?q=...` | Búsqueda inteligente |
| `/api/favorites/<id>/toggle/` | Marca/desmarca favorito |
| `/metro-status/` | Estado del Metro (caché + refresco en segundo plano) |

## Sprint 3 — qué cambió

**La página se actualiza sola, sin recargar.** Antes cada reporte hacía POST +
redirect, o sea recarga completa: la persona reportaba un cupo y el navegador la
devolvía al comienzo del home. Ahora los reportes se envían por fetch y solo se
repintan los números de esa tarjeta. El scroll, los planos abiertos y lo que
estés escribiendo se quedan donde estaban. Además el estado se refresca solo
cada 30 segundos.

**El Metro ya no bloquea la página.** Antes el scraping corría dentro del
request: con la caché vencida, abrir el navegador headless podía dejar el home
cargando 30 segundos. Ahora el servidor responde con lo último que tenga
guardado y refresca en segundo plano. Además, si una sección (semáforo,
horarios, noticias) no se puede refrescar, se conserva la anterior marcada como
desactualizada en vez de quedar vacía, y cada una muestra su propia antigüedad.

**El mapa sale de la base de datos.** Antes los marcadores estaban escritos a
mano en el HTML. Ahora cada parqueadero tiene `latitude`/`longitude` editables
desde `/admin/`, y el mapa pinta círculos de color según el estado con los cupos
libres adentro, encuadra solo todos los parqueaderos y se actualiza en vivo.

**Buscador inteligente.** No hay que escribir el nombre exacto: entiende apodos
("el de ingeniería"), errores de dedo ("parqeadero nrte") e intenciones sin
nombre ("el más desocupado", "uno para moto", "para discapacitados"). Los apodos
se editan desde `/admin/` → campo "Otros nombres", sin tocar código.

**Favoritos.** Se pueden marcar con la estrella de cada tarjeta y aparecen de
primeros. Ver abajo cómo conectarlos al login.

## Para quien implemente usuarios y login

Los favoritos ya están preparados para cuentas, pero funcionan sin ellas: hoy se
guardan por sesión del navegador. Cuando el login esté listo, agrega **una línea**
después de autenticar:

```python
from core.favorites import attach_session_favorites_to_user

login(request, user)
attach_session_favorites_to_user(request, user)   # <-- esto
```

Con eso, los favoritos que la persona marcó antes de tener cuenta pasan a su
cuenta, sin duplicados. No hay que tocar el modelo ni las vistas: ya detectan
solas si hay usuario logueado. El detalle está en `core/favorites.py`.

## Cómo montar el plano de un parqueadero

1. En `/admin/`, abre el parqueadero y sube una imagen en "Imagen del plano".
2. Ve a `/dashboard/` → "📍 Ubicar espacios en el plano".
3. Haz clic sobre el plano para crear cada espacio. Arrastra para reubicar, usa
   "Girar 90°" para rotarlo.

## Estructura del proyecto

- `core/` — modelos, vistas públicas y APIs, búsqueda (`search.py`), favoritos
  (`favorites.py`), scraping del Metro (`metro_status.py`).
- `reports/` — reportes de usuarios (espacio disponible/ocupado/información incorrecta).
- `administration/` — dashboard, mapeador visual del plano, gestión de reportes, y `/admin/`.

## Problemas comunes

- **"Sin conexión a internet en el servidor"** en la sección del Metro: la
  máquina no tiene salida a internet, o algo la bloquea (firewall, antivirus,
  VPN). No afecta al resto del sitio: se sigue mostrando la última información
  conocida y se reintenta solo.
- **El semáforo de líneas del Metro sale vacío**: requiere Playwright, que es
  opcional (`pip install playwright && playwright install chromium`). Sin él,
  las noticias sí funcionan.
- **El mapa sale vacío**: falta poner coordenadas en `/admin/` → "Ubicación en
  el mapa".
- **El plano no aparece en una tarjeta**: falta subir la imagen del plano en `/admin/`.
