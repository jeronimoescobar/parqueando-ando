
# Parqueando Ando — Base del proyecto (Sprint 1)

Aplicación web colaborativa para consultar y reportar la disponibilidad de
parqueaderos en el campus de la Universidad EAFIT.

## Cómo correrlo el proyecto localmente
Tener una versión de python 3.12 o mayor, para poder ejecutarlo correctamente
```bash
# 1. Crear y activar entorno virtual
python3 -m venv venv
source venv/bin/activate      # En Windows: venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Aplicar migraciones (crea la base de datos SQLite local)
python manage.py migrate

# 4. Crear un usuario administrador
python manage.py createsuperuser

# 5. Levantar el servidor de desarrollo
python manage.py runserver
```


Luego abre `http://127.0.0.1:8000/` en el navegador. Necesitas iniciar
sesión (`/accounts/login/`) para ver el listado y reportar disponibilidad.
Puedes crear zonas de parqueo de prueba desde `/admin/`.


```
parqueando_ando/   # Configuración del proyecto (settings, urls)
core/               # App base con la página de bienvenida temporal
manage.py
requirements.txt
```



