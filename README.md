# Pulse SAS — Sistema de Gestión de Citas Médicas

Aplicación web para la gestión de citas de un hospital / centro de urgencias. Pacientes solicitan citas por tipo y horario; el personal administrativo y clínico gestiona esas citas, la historia clínica del paciente, el tratamiento y la autorización de salida. Dominio explícitamente clínico/hospitalario (no es un CRM genérico de citas).

## Tabla de contenidos

- [Requisitos previos](#requisitos-previos)
- [Instalación](#instalación)
- [Uso](#uso)
- [Arquitectura / Tecnologías usadas](#arquitectura--tecnologías-usadas)
- [Estructura de carpetas](#estructura-de-carpetas)
- [Comandos frecuentes](#comandos-frecuentes)
- [Contribución](#contribución)
- [Autores](#autores)
- [Licencia](#licencia)

## Requisitos previos

- Python 3.14
- PostgreSQL 18 (corriendo local)
- pip / venv

## Instalación

```bash
git clone https://github.com/alejandralgar/pulse_sas.git
cd pulse_sas/pulse_sas_django

# 1. Crear y activar entorno virtual
python -m venv venv
.\venv\Scripts\Activate.ps1        # PowerShell

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
copy .env.example .env
# Abrir .env y completar DB_PASSWORD y DB_PORT con los de tu Postgres local.
# Generar tu propia SECRET_KEY (ver instrucciones dentro de .env.example).

# 4. Crear la base de datos vacía (una sola vez)
createdb -U postgres citas_pulse_sas

# 5. Migraciones Django (única fuente de verdad — NO restaurar sql\citas_pulse_sas.sql,
#    ver nota abajo)
python app.py migrate
python app.py createsuperuser

# 6. Datos demo: un usuario por rol (admin, médico, enfermera, guardia,
#    paciente, empresa, recepcionista, gerente), password Pulsesas123 pa todos
python app.py seed_demo_data

# 7. Correr el servidor
python app.py runserver
```

> **`sql/citas_pulse_sas.sql` no se restaura en desarrollo.** Es un
> respaldo puntual, no una fuente de verdad — si lo restauras, su tabla
> `django_migrations` queda congelada en la fecha del dump; el siguiente
> `git pull` trae migraciones nuevas que Django cree no aplicadas, y
> `migrate` falla o corrompe tu esquema porque las columnas ya existen.
> Usa siempre `migrate` + `seed_demo_data` para tener el mismo estado que
> el resto del equipo.

Si `Activate.ps1` falla por política de ejecución de PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

## Uso

Con el servidor corriendo, abrir:

- `http://127.0.0.1:8000/login/` — login del sistema (pacientes, personal clínico y administrativo).
- `http://127.0.0.1:8000/django-admin/` — panel nativo de Django (superusuario).
- `http://127.0.0.1:8000/dashboard/admin/` — panel Admin propio del proyecto (roles, usuarios, convenios).

El acceso y las vistas disponibles dependen del rol del usuario autenticado.

## Arquitectura / Tecnologías usadas

| Capa | Tecnología |
|------|-----------|
| Lenguaje | Python 3.14 |
| Framework web | Django 6.0.7 (patrón MVT) |
| Base de datos | PostgreSQL 18 |
| Driver DB | psycopg2-binary |
| Variables de entorno | python-decouple |
| Entorno virtual | `venv` |

Equivalencia MVC → MVT:

| Término (MVC) | Django (MVT) | Dónde vive |
|---|---|---|
| Modelo | Model | `pulse_sas/internal/pulse_sas/{accounts,personas,citas}/models.py` |
| Controlador | View | `.../views.py` de cada app |
| Vista | Template | `pulse_sas/internal/templates/**/*.html` |
| — | Estáticos (CSS/JS/íconos) | `pulse_sas/internal/static/**` |

Apps Django (cada una agrupa modelo + controlador de un dominio, no de una capa técnica):

- **`accounts`** — autenticación: login, logout, dashboard post-login, gestión de usuarios/roles.
- **`personas`** — catálogo del dominio clínico: `Persona`, `Rol`, `Pais`, `Ciudad`, `TipoSangre`, `HistoriaClinica` y tablas derivadas (antecedentes, motivo de consulta, examen físico, diagnóstico, plan de manejo, receta médica).
- **`citas`** — agenda: `Cita` y `CitaHistorial`.

Detalle completo de decisiones de arquitectura en `context/1_ARQUITECTURA.md` y `context/3_DECISIONES.md` (no versionados en remoto, ver `.gitignore`).

## Estructura de carpetas

```
pulse_sas_django/
├── app.py                     ← manage.py renombrado
├── requirements.txt
├── .env.example                ← plantilla de variables de entorno
├── venv/                       ← entorno virtual (no se sube)
├── sql/
│   └── citas_pulse_sas.sql     ← dump de respaldo de la base de datos
├── config/                     ← configuración raíz del proyecto Django (no es una app)
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py / asgi.py
└── pulse_sas/
    └── internal/
        ├── pulse_sas/           ← paquete de apps Django
        │   ├── accounts/
        │   ├── personas/
        │   └── citas/
        ├── templates/           ← vistas HTML, organizadas por rol/sección
        └── static/
            ├── css/ js/ icono/ img/
```

## Comandos frecuentes

```bash
python app.py runserver              # levantar servidor de desarrollo
python app.py migrate                # aplicar migraciones pendientes
python app.py makemigrations         # generar migraciones nuevas
python app.py makemigrations --check --dry-run   # verificar que no falta ninguna migración
python app.py createsuperuser        # crear usuario admin
python app.py seed_demo_data         # crear usuarios demo (uno por rol), idempotente
python app.py check                  # verificar que el proyecto no tiene errores
python app.py test pulse_sas --noinput   # correr toda la suite de tests
python app.py shell                  # consola interactiva con el ORM cargado
```

Usar `.\venv\Scripts\python.exe app.py ...` si el venv no está activado.

### Tests

```bash
python app.py test pulse_sas --noinput
```

Corre contra una base de datos de prueba separada (`test_citas_pulse_sas`)
que Django crea y destruye solo en cada corrida — no toca la base de datos
real, no hace falta backupear nada antes de correr tests. Requiere que tu
usuario de Postgres (`DB_USER`) tenga permiso `CREATEDB`; el usuario
`postgres` por defecto ya lo tiene.

## Contribución

- Antes de trabajar: `git pull`, luego `python app.py migrate` (por si hay migraciones nuevas).
- Antes de subir cambios: `python app.py test pulse_sas --noinput` — la suite debe pasar completa.
- Las migraciones se commitean junto con el cambio de modelo que las originó, en el mismo commit.
- Si una migración usa `SeparateDatabaseAndState`, `database_operations` tiene que tener las operaciones reales, nunca una lista vacía — una migración vacía en `database_operations` le miente al ORM (dice que agregó una columna sin crearla de verdad) y rompe `migrate` en cualquier base de datos nueva, aunque la tuya ya migrada no lo note.
- `sql/citas_pulse_sas.sql` es un respaldo manual ocasional, no un paso de
  onboarding ni de contribución normal — no lo regeneres en cada cambio de
  modelo ni lo restaures para "avanzar rápido". Restaurarlo desalinea tu
  `django_migrations` del historial real de git (ver nota en Instalación) y
  es la causa más común de que `migrate` falle después de un `git pull`.
- `.env`, `venv/`, `db.sqlite3` y `server.log` nunca se commitean.

## Autores

Equipo Pulse SAS.

## Licencia

MIT.
