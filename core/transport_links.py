"""
Enlaces de transporte externo (Requerimiento 2).

Cada entrada de TRANSPORT_LINKS es un botón que se muestra en el home.
Para agregar o quitar un servicio, solo hay que editar esta lista;
no hace falta tocar views.py ni el template.

Coordenadas de Universidad EAFIT (Cra 49 #7 Sur-50, Medellín): 6.2002, -75.5788
"""

EAFIT_LAT = 6.2002
EAFIT_LNG = -75.5788
EAFIT_NAME = "Universidad EAFIT"

TRANSPORT_LINKS = [
    {
        "name": "Uber",
        # Deep link universal de Uber: si el usuario tiene la app instalada,
        # la abre directamente con el destino ya cargado (EAFIT). Si no,
        # lo lleva a la web/tienda de apps. No requiere API key.
        "url": (
            "https://m.uber.com/ul/?action=setPickup"
            f"&dropoff[latitude]={EAFIT_LAT}&dropoff[longitude]={EAFIT_LNG}"
            f"&dropoff[nickname]={EAFIT_NAME}"
        ),
        "icon": "🚗",
        "description": "Pedir un Uber con destino a EAFIT",
    },
    {
        "name": "DiDi",
        # DiDi no ofrece un deep link público y estable con destino
        # precargado (a diferencia de Uber), así que se enlaza a su sitio;
        # si el usuario tiene la app instalada, el sistema operativo suele
        # ofrecer abrirla directamente.
        "url": "https://www.didiglobal.com/didi-account/download",
        "icon": "🚕",
        "description": "Abrir DiDi",
    },
    {
        "name": "InDrive",
        # Mismo caso que DiDi: no hay deep link oficial con destino,
        # se enlaza al sitio oficial.
        "url": "https://indrive.com/es-co/",
        "icon": "🚙",
        "description": "Abrir InDrive",
    },
]
