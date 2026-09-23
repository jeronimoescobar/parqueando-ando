"""
Lógica de parqueaderos favoritos (Sprint 3).

Está en su propio archivo (igual que waiting_time.py o
parking_recommendation.py) para que quien implemente usuarios y login no
tenga que ir a buscar esto dentro de views.py.

═══════════════════════════════════════════════════════════════════════
LOGIN (FR2) — ya está conectado
═══════════════════════════════════════════════════════════════════════
El login (core/auth_views.py) ya migra los favoritos: los que la persona
marcó ANTES de tener sesión pasan a su cuenta, sin duplicados.

Si en otro lugar haces login a mano (por ejemplo al terminar el
registro), usa:

    from core.auth_views import log_user_in
    log_user_in(request, user)      # en vez de login(request, user)

No llames `login()` y luego `attach_session_favorites_to_user(request,
user)` a secas: login() cambia la clave de sesión y la migración ya no
encontraría los favoritos. log_user_in se encarga de ese detalle.
═══════════════════════════════════════════════════════════════════════
"""

from .models import FavoriteParkingLot


def _ensure_session_key(request):
    """
    Devuelve la clave de sesión, creándola si el visitante todavía no
    tiene una. Sin esto, un visitante que nunca ha guardado nada en
    sesión tiene session_key=None y no podríamos recordarle sus
    favoritos.
    """
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def favorites_queryset(request):
    """
    Los favoritos de quien está navegando, sea usuario logueado o
    visitante anónimo. Esta es la única función que decide "de quién son
    los favoritos", así que el resto del código no tiene que preguntarse
    si hay login o no.

    Ojo con un detalle: al LEER no creamos sesión. Si lo hiciéramos, cada
    visitante que simplemente abre el home generaría una fila de sesión en
    la base de datos aunque nunca marque nada. La sesión se crea solo
    cuando la persona marca su primer favorito (ver toggle_favorite).
    """
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return FavoriteParkingLot.objects.filter(user=user)

    session_key = request.session.session_key
    if not session_key:
        return FavoriteParkingLot.objects.none()

    return FavoriteParkingLot.objects.filter(user__isnull=True, session_key=session_key)


def favorite_lot_ids(request):
    """Set con los IDs de los parqueaderos favoritos (para marcar corazones)."""
    return set(favorites_queryset(request).values_list("lot_id", flat=True))


def toggle_favorite(request, lot):
    """
    Marca/desmarca un parqueadero como favorito y devuelve True si quedó
    marcado, False si se quitó.
    """
    user = getattr(request, "user", None)

    if user is not None and user.is_authenticated:
        existing = FavoriteParkingLot.objects.filter(user=user, lot=lot).first()
        if existing:
            existing.delete()
            return False
        FavoriteParkingLot.objects.create(user=user, lot=lot, session_key="")
        return True

    session_key = _ensure_session_key(request)
    existing = FavoriteParkingLot.objects.filter(
        user__isnull=True, session_key=session_key, lot=lot
    ).first()
    if existing:
        existing.delete()
        return False
    FavoriteParkingLot.objects.create(user=None, lot=lot, session_key=session_key)
    return True


def attach_session_favorites_to_user(request, user, session_key=None):
    """
    Pasa los favoritos de la sesión anónima a la cuenta que acaba de
    iniciar sesión. Ver el bloque grande arriba: esta es la función que
    el login debe llamar.

    `session_key`: la clave de la sesión ANÓNIMA. Hay que pasarla porque
    `login()` cambia la clave de sesión: si no se pasa, se usa la actual,
    que después de login() ya es la nueva y no tiene favoritos. Lo más
    fácil es no llamar esto directamente y usar
    `core.auth_views.log_user_in(request, user)`, que ya lo hace bien.

    Si la persona ya tenía ese mismo parqueadero como favorito en su
    cuenta, el de la sesión simplemente se descarta (no se duplica).
    Devuelve cuántos favoritos se migraron.
    """
    session_key = session_key or request.session.session_key
    if not session_key:
        return 0

    session_favorites = FavoriteParkingLot.objects.filter(
        user__isnull=True, session_key=session_key
    )
    if not session_favorites.exists():
        return 0

    already_owned = set(
        FavoriteParkingLot.objects.filter(user=user).values_list("lot_id", flat=True)
    )

    migrated = 0
    for favorite in session_favorites:
        if favorite.lot_id in already_owned:
            favorite.delete()
            continue
        favorite.user = user
        favorite.session_key = ""
        favorite.save(update_fields=["user", "session_key"])
        migrated += 1

    return migrated
