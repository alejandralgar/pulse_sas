# Diagnóstico Técnico: ¿Por qué el proyecto Pulse SAS no funciona tras correr las migraciones?

## Resumen Ejecutivo

Al clonar y ejecutar el proyecto **Pulse SAS**, e incluso tras correr exitosamente las migraciones de Django (`python app.py migrate`), el sistema se percibe como **no funcional, inusable o inaccesible**. 

A pesar de que la suite de pruebas unitarias se ejecuta correctamente (`python app.py test pulse_sas --noinput` pasa 44/44 pruebas debido a que crea objetos temporales en memoria durante los tests), el entorno de desarrollo local queda en un estado **inoperativo**.

Este documento detalla técnicamente las **5 causas principales** de este comportamiento y ofrece las soluciones necesarias para poner en marcha el sistema.

---

## Causas Principales

### 1. Ausencia de datos de Usuarios y Perfiles (`auth_user` y `Persona` vacíos)

* **Ubicación relevante:** [`pulse_sas/internal/pulse_sas/personas/migrations/`](file:///c:/Users/LORENA/Downloads/repoclonado_pulse_sas/2/pulse_sas/pulse_sas/internal/pulse_sas/personas/migrations) y [`pulse_sas/internal/pulse_sas/accounts/views.py`](file:///c:/Users/LORENA/Downloads/repoclonado_pulse_sas/2/pulse_sas/pulse_sas/internal/pulse_sas/accounts/views.py#L26-L34)
* **Descripción del problema:**
  Las migraciones de Django solo crean las tablas relacionales y pueblan catálogos maestros básicos (`Rol`, `TipoSangre`, `Pais`, `Ciudad`). **Ninguna migración crea cuentas de usuario (`auth_user`), perfiles de personas (`Persona`) ni asignaciones de roles (`RolPersona`)**.
* **Impacto en el Login:**
  El sistema de autenticación del proyecto (`login_view` en [`accounts/views.py`](file:///c:/Users/LORENA/Downloads/repoclonado_pulse_sas/2/pulse_sas/pulse_sas/internal/pulse_sas/accounts/views.py#L111-L130)) valida estrictamente los permisos llamando a `_usuario_tiene_rol(user, rol)`:
  ```python
  def _usuario_tiene_rol(user, categoria):
      if user.is_superuser:
          return True
      from pulse_sas.internal.pulse_sas.personas.models import Rol
      return Rol.objects.filter(categoria=categoria, personas__usuario=user).exists()
  ```
  Si un desarrollador ejecuta `python app.py createsuperuser` o crea un usuario manual:
  1. Si crea un usuario estándar, **no tiene registro `Persona` asociado**. Al intentar iniciar sesión seleccionando cualquier rol (Médico, Paciente, Recepcionista, etc.), la vista rechaza la autenticación mostrando el mensaje de error:  
     > *"Tu usuario no tiene asignado ese rol."*
  2. Si ingresa como superusuario, la función `dashboard()` en [`accounts/views.py:L138`](file:///c:/Users/LORENA/Downloads/repoclonado_pulse_sas/2/pulse_sas/pulse_sas/internal/pulse_sas/accounts/views.py#L138) lo redirige **siempre y de forma obligatoria a la vista de administración (`vista_admin`)**, impidiendo probar las vistas de los demás roles si no existen registros en la tabla `Persona`.

---

### 2. Inoperatividad de los Dashboards por falta de Datos Clínicos

* **Ubicación relevante:** [`pulse_sas/internal/pulse_sas/accounts/views.py`](file:///c:/Users/LORENA/Downloads/repoclonado_pulse_sas/2/pulse_sas/pulse_sas/internal/pulse_sas/accounts/views.py#L291-L499)
* **Descripción del problema:**
  Pulse SAS es un sistema de gestión hospitalaria altamente acoplado a la relación entre Médicos, Pacientes, Citas, Historias Clínicas y Jornadas de personal.
* **Manifestaciones en la aplicación:**
  * **Dashboard de Recepción/Administrativo (`vista_administrativo`):** La lógica de asignación de citas (`_sugerir_medico`) busca instancias de `Persona` con categoría `Rol.Categoria.MEDICO`. Al no haber médicos cargados en la base de datos, la gestión de citas queda totalmente bloqueada.
  * **Dashboard Médico (`vista_medico`):** Depende de `request.user.persona`. Si la cuenta de acceso no está enlazada a una `Persona`, la agenda se muestra vacía y no se pueden consultar pacientes ni redactar historias clínicas o recetas.
  * **Dashboard de Pacientes (`vista_cliente`):** Requiere un registro `Persona` del paciente para solicitar citas y visualizar historiales.

---

### 3. Discrepancia entre la Guía de Instalación (Paso 5A vs. Paso 5B)

* **Ubicación relevante:** [`README.md`](file:///c:/Users/LORENA/Downloads/repoclonado_pulse_sas/2/pulse_sas/README.md#L44-L50) y [`sql/citas_pulse_sas.sql`](file:///c:/Users/LORENA/Downloads/repoclonado_pulse_sas/2/pulse_sas/sql/citas_pulse_sas.sql)
* **Descripción del problema:**
  El archivo `README.md` presenta dos alternativas de instalación:
  * **Paso 5A (Recomendado según el README):** `python app.py migrate` + `python app.py createsuperuser`.
  * **Paso 5B (Alternativa rápida):** Restaurar el dump `sql/citas_pulse_sas.sql`.
* **Impacto:**
  El dataset completo de pruebas (57 usuarios con contraseñas, médicos, pacientes, citas creadas e historias clínicas) se encuentra **únicamente en el archivo SQL respaldo `sql/citas_pulse_sas.sql`**, y **no en las migraciones de Django**. Por ende, si se sigue la ruta 5A recomendada por la documentación, la base de datos queda vacía y el proyecto no funciona.

---

### 4. Configuración rígida de PostgreSQL sin fallback a SQLite

* **Ubicación relevante:** [`config/settings.py`](file:///c:/Users/LORENA/Downloads/repoclonado_pulse_sas/2/pulse_sas/config/settings.py#L80-L89) y [`.env`](file:///c:/Users/LORENA/Downloads/repoclonado_pulse_sas/2/pulse_sas/.env#L6-L10)
* **Descripción del problema:**
  El proyecto exige una instancia local activa de **PostgreSQL 18** en la base de datos `citas_pulse_sas`:
  ```python
  DATABASES = {
      'default': {
          'ENGINE': 'django.db.backends.postgresql',
          'NAME': config('DB_NAME', default='citas_pulse_sas'),
          'USER': config('DB_USER', default='postgres'),
          'PASSWORD': config('DB_PASSWORD', default=''),
          'HOST': config('DB_HOST', default='localhost'),
          'PORT': config('DB_PORT', default='5432'),
      }
  }
  ```
* **Impacto:**
  No existe configuración alternativa para desarrollo rápido con SQLite. Si PostgreSQL no está instalado, la base de datos no fue creada previamente con `createdb`, o la contraseña en `.env` no coincide, cualquier intento de ejecutar `python app.py migrate` o `python app.py runserver` se detiene con un error `psycopg2.OperationalError` (Imposible conectar con el servidor de base de datos).

---

### 5. Renombrado del ejecutable nativo (`manage.py` → `app.py`)

* **Ubicación relevante:** [`app.py`](file:///c:/Users/LORENA/Downloads/repoclonado_pulse_sas/2/pulse_sas/app.py) y [`README.md`](file:///c:/Users/LORENA/Downloads/repoclonado_pulse_sas/2/pulse_sas/README.md#L103)
* **Descripción del problema:**
  El archivo estándar de gestión de Django `manage.py` fue renombrado en este repositorio como `app.py`.
* **Impacto:**
  Cualquier desarrollador o entorno automatizado que intente ejecutar los comandos estándar de Django (`python manage.py runserver` o `python manage.py migrate`) obtendrá un error de archivo no encontrado (`FileNotFoundError`).

---

## Solución y Pasos para Hacer Funcionar el Proyecto

Para disponer de un entorno funcional con usuarios, médicos, pacientes y citas de prueba cargados, siga estos pasos:

### Opción 1: Restaurar el Dump de Datos Completo (Recomendado)

1. Crear la base de datos en PostgreSQL local:
   ```bash
   createdb -U postgres citas_pulse_sas
   ```
2. Cargar el respaldo SQL que contiene la estructura y los 57 usuarios de demostración:
   ```bash
   psql -U postgres -h localhost -d citas_pulse_sas -f sql\citas_pulse_sas.sql
   ```
3. Iniciar el servidor:
   ```bash
   python app.py runserver
   ```

---

### Opción 2: Si se utiliza `python app.py migrate`

Si decide usar las migraciones de Django en una base de datos limpia:

1. Ejecutar las migraciones:
   ```bash
   python app.py migrate
   ```
2. Crear un superusuario:
   ```bash
   python app.py createsuperuser
   ```
3. Para poder probar roles específicos (Médico, Paciente, Recepcionista), debe ingresar al panel de administración de Django (`http://127.0.0.1:8000/django-admin/`) o a la consola interactiva (`python app.py shell`) y crear un registro en la tabla `Persona` enlazado al `User` creado, asignándole los roles correspondientes en `RolPersona`.

---

## Tabla Resumen de Diagnóstico

| Componente | Estado tras `migrate` | Consecuencia / Error |
| :--- | :--- | :--- |
| **Tablas relacionales** | Creadas | Funcional |
| **Catálogos (Países, Roles, Sangre)** | Poblados | Funcional |
| **Usuarios (`auth_user`)** | Vacío (0 registros) | No es posible iniciar sesión |
| **Perfiles (`Persona`)** | Vacío (0 registros) | Formulario de login rechaza autenticación ("Tu usuario no tiene asignado ese rol") |
| **Médicos y Pacientes** | Vacío (0 registros) | Asignación de citas e Historias Clínicas inoperativas |
| **Respaldo SQL (`sql/citas_pulse_sas.sql`)** | No aplicado por `migrate` | Los datos de demostración quedan ignorados |
