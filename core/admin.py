"""
OJO: la personalización del admin de Django para los modelos de esta app
(ParkingLot, ParkingSpot) NO vive aquí — vive en `administration/admin.py`.

Esto es intencional (no un descuido): la app `administration` agrupa TODA la
funcionalidad de administrador del proyecto (dashboard FR16, gestión de
datos FR17, y el registro en /admin/) en un solo lugar, aunque los
modelos en sí sigan definidos aquí en `core` porque el sitio público
también los usa.

Si necesitas agregar o cambiar algo del admin de ParkingLot/ParkingSpot,
edita administration/admin.py — NO agregues un @admin.register(ParkingLot)
aquí. Django no permite registrar el mismo modelo dos veces: si este
archivo también registra ParkingLot, la app entera deja de arrancar con
un error "AlreadyRegistered" (le pasó a este proyecto — así se descubrió
que hacía falta este aviso).
"""
