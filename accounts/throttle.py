"""
FR20 – Protección del login contra fuerza bruta.

Cuenta los intentos fallidos por (usuario, IP) en la caché de Django. Al
llegar a MAX_ATTEMPTS la combinación queda bloqueada LOCKOUT_SECONDS, aun si
después se escribe la contraseña correcta. Un login exitoso borra el contador.

Usa la caché por defecto (memoria local). Con varios procesos/servidores hay
que configurar una caché compartida (Redis, Memcached o la base de datos)
para que el conteo sea común.
"""

from django.core.cache import cache

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60


def client_ip(request):
    """IP del cliente. No se confía en X-Forwarded-For (se puede falsificar)."""
    return request.META.get("REMOTE_ADDR", "") or "unknown"


def _key(request, identifier):
    identifier = (identifier or "").strip().lower()[:150]
    return f"login-fail:{identifier}:{client_ip(request)}"


def is_locked(request, identifier):
    return cache.get(_key(request, identifier), 0) >= MAX_ATTEMPTS


def register_failure(request, identifier):
    """Suma un intento fallido y devuelve cuántos lleva."""
    key = _key(request, identifier)
    # add() solo crea la llave si no existe y fija el vencimiento una vez:
    # el bloqueo dura LOCKOUT_SECONDS desde el primer fallo de la racha.
    cache.add(key, 0, LOCKOUT_SECONDS)
    try:
        return cache.incr(key)
    except ValueError:  # la llave venció justo ahora
        cache.set(key, 1, LOCKOUT_SECONDS)
        return 1


def reset(request, identifier):
    cache.delete(_key(request, identifier))


def lockout_minutes():
    return LOCKOUT_SECONDS // 60
