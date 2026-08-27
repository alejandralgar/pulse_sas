from django.test import TestCase


class MigrationIntegrityTests(TestCase):
    """Guarda que las migraciones de las 3 apps con modelos (`accounts`,
    `personas`, `citas`) puedan recrear la base de datos completa desde
    cero -- lo que necesita el equipo para levantar su propia BD. Ver
    8_FALTO_RESOLVER.md, 2026-08-19: se encontró que la migración
    `personas.0008` usaba `SeparateDatabaseAndState` con
    `database_operations=[]` -- le mentía al ORM (decía tener la columna
    `fecha_creacion` sin crearla de verdad). No rompía la BD ya migrada
    a mano, pero SÍ rompía cualquier BD nueva (confirmado reconstruyendo
    una BD limpia solo con `migrate`, y con `python app.py test`, que
    crea su propia BD desde cero en cada corrida)."""

    def test_no_hay_cambios_de_modelo_sin_migracion(self):
        """Equivalente a `makemigrations --check --dry-run` -- si esto
        falla, hay un campo/modelo nuevo sin migración."""
        import io
        from django.core.management import call_command

        salida = io.StringIO()
        try:
            call_command(
                'makemigrations', 'accounts', 'personas', 'citas',
                dry_run=True, check=True, stdout=salida, stderr=salida,
            )
        except SystemExit:
            self.fail(f'Hay cambios de modelo sin migración generada:\n{salida.getvalue()}')

    def test_ninguna_migracion_miente_sobre_columnas_creadas(self):
        """`SeparateDatabaseAndState` con `database_operations=[]` (o
        vacío) actualiza el *state* de Django sin ejecutar el DDL real
        -- exactamente el bug de `personas.0008`. Si aparece de nuevo en
        cualquier migración, esta prueba debe fallar."""
        import re
        from pathlib import Path

        import pulse_sas.internal.pulse_sas as apps_root

        base = Path(apps_root.__file__).parent
        sospechosas = []
        for app in ('accounts', 'personas', 'citas'):
            for archivo in (base / app / 'migrations').glob('*.py'):
                if archivo.name == '__init__.py':
                    continue
                texto = archivo.read_text(encoding='utf-8')
                if re.search(r'database_operations\s*=\s*\[\s*\]', texto):
                    sospechosas.append(str(archivo.relative_to(base)))
        self.assertEqual(
            sospechosas, [],
            f'Migraciones con database_operations vacío (no crean columnas de verdad): {sospechosas}',
        )

    def test_bd_reconstruida_solo_con_migraciones_tiene_las_mismas_tablas_y_columnas(self):
        """Compara el schema real (conexión de test, que Django ya
        reconstruyó ejecutando SOLO las migraciones para esta corrida)
        contra los modelos actuales -- si una tabla/columna del modelo
        no quedó creada, esto explota acá on introspection."""
        from django.db import connection

        with connection.cursor() as cursor:
            tablas_bd = set(connection.introspection.table_names(cursor))

        tablas_esperadas = {
            'personas_persona', 'personas_rol', 'personas_jornada',
            'personas_historiaclinica', 'personas_receta', 'personas_itemreceta',
            'convenio',  # db_table explícito en el modelo Convenio
            'citas_cita',
        }
        faltantes = tablas_esperadas - tablas_bd
        self.assertEqual(faltantes, set(), f'Tablas esperadas que no existen en la BD de test: {faltantes}')

        with connection.cursor() as cursor:
            columnas_persona = {
                c.name for c in connection.introspection.get_table_description(cursor, 'personas_persona')
            }
        self.assertIn(
            'fecha_creacion', columnas_persona,
            'personas_persona.fecha_creacion no existe -- regresión del bug de migración 0008.',
        )
