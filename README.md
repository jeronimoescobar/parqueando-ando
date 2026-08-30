
# Parqueando Ando — Base del proyecto (Sprint 1)

Aplicación web colaborativa para consultar y reportar la disponibilidad de
parqueaderos en el campus de la Universidad EAFIT.

## Cómo ejecutar el proyecto localmente

### Requisito

Se requiere **Python 3.12 o superior**, porque el proyecto usa Django 6.

### Windows (CMD o PowerShell)

```bat
# 1. Crear y activar el entorno virtual con Python 3.12
py -3.12 -m venv venv
venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Aplicar migraciones (crea la base de datos SQLite local)
python manage.py migrate

# 4. Crear usuario administrador (opcional; necesario para usar /admin/)
python manage.py createsuperuser

# 5. Iniciar el servidor de desarrollo
python manage.py runserver
```

### macOS o Linux

```bash
# 1. Crear y activar el entorno virtual con Python 3.12
python3.12 -m venv venv
source venv/bin/activate

# 2. Instalar dependencias y ejecutar el proyecto
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Luego abre `http://127.0.0.1:8000/` en el navegador. La página principal es
pública; no requiere iniciar sesión. Si deseas crear o editar parqueaderos y
su disponibilidad, ingresa a `http://127.0.0.1:8000/admin/` con el usuario
administrador creado en el paso 4.


```
parqueando_ando/   # Configuración del proyecto (settings, urls)
core/               # App base con la página de bienvenida temporal
manage.py
requirements.txt
```



