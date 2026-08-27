from datetime import date, time, timedelta

from django.test import TestCase
from django.utils import timezone

from pulse_sas.internal.pulse_sas.citas.models import Cita
from pulse_sas.internal.pulse_sas.personas.models import (
    HistoriaClinica, HistoriaClinicaPersona, Jornada, Rol,
)

from pulse_sas.internal.pulse_sas.medico.forms import ConsultaForm

from .helpers import _crear_persona, _datos_consulta


class ConsultaFormGuardarNuevaTests(TestCase):
    """Cubre `atender_cita` -- registrar una consulta nueva. Reproduce el
    <form> real (ver 8_FALTO_RESOLVER.md, campo `fecha_proxima_cita`
    perdía datos en edición por formato de fecha, y el bloqueo de
    disponibilidad rompía el guardado completo con `Jornada` vacía)."""

    def setUp(self):
        self.rol_medico = Rol.objects.create(nombre='medico_test', categoria=Rol.Categoria.MEDICO)
        self.medico = _crear_persona(username='medico1', nombre='Med', apellido='Uno', cedula='1000000001')
        self.medico.roles.add(self.rol_medico)
        self.paciente = _crear_persona(
            username='pac1', nombre='Pac', apellido='Uno', cedula='1000000002',
            sexo='F', correo='paciente@example.com',
        )
        self.hora_cita = timezone.localtime(timezone.now())
        self.cita = Cita.objects.create(
            persona=self.paciente, medico=self.medico, fecha_hora=self.hora_cita,
            estado=Cita.Estado.CONFIRMADA, tipo_cita=Cita.TipoCita.CONSULTA_GENERAL, motivo='chequeo',
        )

    def _form_kwargs(self):
        return {'medico': self.medico, 'paciente': self.paciente, 'hora_referencia': self.cita.fecha_hora}

    def test_guarda_todos_los_campos_de_la_consulta(self):
        data = _datos_consulta()
        form = ConsultaForm(data, **self._form_kwargs())
        self.assertTrue(form.is_valid(), form.errors)

        historia = form.guardar_nueva(cita=self.cita, medico=self.medico)

        self.assertEqual(historia.tratamiento, data['tratamiento'])
        self.assertEqual(historia.motivo_consulta.descripcion, data['motivo_consulta'])
        self.assertEqual(historia.enfermedad_actual.descripcion_cronologica, data['padecimiento_actual'])
        self.assertEqual(historia.enfermedad_actual.factores_desencadenantes, data['factores_desencadenantes'])
        self.assertEqual(historia.enfermedad_actual.tratamientos_previos, data['tratamientos_previos'])
        self.assertEqual(historia.antecedente.familiares, data['antecedentes_familiares'])
        self.assertEqual(historia.antecedente.personales_patologicos, data['antecedentes_personales_patologicos'])
        self.assertEqual(historia.antecedente.no_patologicos, data['antecedentes_no_patologicos'])
        self.assertEqual(historia.examen_fisico.presion_arterial, data['presion_arterial'])
        self.assertEqual(historia.examen_fisico.frecuencia_cardiaca, 0)
        self.assertEqual(historia.diagnostico.impresion_diagnostica, data['impresion_diagnostica'])
        self.assertEqual(historia.diagnostico.diagnostico_confirmado, data['diagnostico_confirmado'])
        self.assertEqual(historia.plan_de_manejo.tratamiento_indicado, data['tratamiento_indicado'])
        self.assertEqual(historia.plan_de_manejo.recomendaciones, data['recomendaciones'])
        self.assertIsNone(historia.plan_de_manejo.fecha_proxima_cita)

        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.Estado.ATENDIDA)
        self.assertEqual(self.cita.historia_clinica_id, historia.id)

        roles = set(
            HistoriaClinicaPersona.objects.filter(historia_clinica=historia).values_list(
                'persona_id', 'rol_en_historia'
            )
        )
        self.assertIn((self.paciente.id, HistoriaClinicaPersona.RolEnHistoria.PACIENTE), roles)
        self.assertIn((self.medico.id, HistoriaClinicaPersona.RolEnHistoria.MEDICO_TRATANTE), roles)

    def test_fecha_proxima_cita_es_opcional_al_registrar(self):
        data = _datos_consulta(fecha_proxima_cita='')
        form = ConsultaForm(data, **self._form_kwargs())
        self.assertTrue(form.is_valid(), form.errors)

        historia = form.guardar_nueva(cita=self.cita, medico=self.medico)
        self.assertIsNone(historia.plan_de_manejo.fecha_proxima_cita)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.Estado.ATENDIDA)

    def test_fecha_proxima_cita_libre_crea_cita_de_control(self):
        fecha = (self.hora_cita.date() + timedelta(days=7))
        Jornada.objects.create(
            persona=self.medico, fecha=fecha,
            hora_inicio=time(0, 0), hora_fin=time(23, 59),
            tipo_jornada=Jornada.TipoJornada.MANANA,
        )
        data = _datos_consulta(fecha_proxima_cita=fecha.isoformat())
        form = ConsultaForm(data, **self._form_kwargs())
        self.assertTrue(form.is_valid(), form.errors)

        historia = form.guardar_nueva(cita=self.cita, medico=self.medico)
        self.assertEqual(historia.plan_de_manejo.fecha_proxima_cita, fecha)
        self.assertTrue(
            Cita.objects.filter(
                persona=self.paciente, medico=self.medico, tipo_cita=Cita.TipoCita.CONTROL,
                fecha_hora__date=fecha,
            ).exists()
        )

    def test_sin_jornada_no_bloquea_el_guardado_solo_avisa(self):
        """Regresión del bug real: con `Jornada` vacía, la primera versión
        de la validación bloqueaba el `<form>` COMPLETO (se perdían todos
        los campos de la consulta), no solo la fecha de control."""
        self.assertEqual(Jornada.objects.filter(persona=self.medico).count(), 0)

        fecha = self.hora_cita.date() + timedelta(days=7)
        data = _datos_consulta(fecha_proxima_cita=fecha.isoformat())
        form = ConsultaForm(data, **self._form_kwargs())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNotNone(form.advertencia_fecha_proxima_cita)

        historia = form.guardar_nueva(cita=self.cita, medico=self.medico)
        self.assertEqual(historia.motivo_consulta.descripcion, data['motivo_consulta'])
        self.assertEqual(historia.plan_de_manejo.fecha_proxima_cita, fecha)

    def test_choque_real_de_agenda_bloquea_el_guardado(self):
        fecha = self.hora_cita.date() + timedelta(days=7)
        otro_paciente = _crear_persona(username='pac_otro', nombre='Otro', apellido='Pac', cedula='1000000003')
        Cita.objects.create(
            persona=otro_paciente, medico=self.medico,
            fecha_hora=self.hora_cita.replace(year=fecha.year, month=fecha.month, day=fecha.day),
            estado=Cita.Estado.CONFIRMADA, tipo_cita=Cita.TipoCita.CONTROL, motivo='choque',
        )
        data = _datos_consulta(fecha_proxima_cita=fecha.isoformat())
        form = ConsultaForm(data, **self._form_kwargs())
        self.assertFalse(form.is_valid())
        self.assertIn('fecha_proxima_cita', form.errors)
        self.assertFalse(HistoriaClinica.objects.exists())


class ConsultaFormGuardarEdicionTests(TestCase):
    """Cubre `editar_historia`. El bug reportado: el `<input type="date">`
    mostraba la fecha ya guardada en formato `31/08/2026` (por
    `LANGUAGE_CODE='es'`), que un `<input type="date">` HTML5 no acepta
    -- el picker aparecía vacío pese a haber una fecha guardada."""

    def setUp(self):
        self.rol_medico = Rol.objects.create(nombre='medico_test', categoria=Rol.Categoria.MEDICO)
        self.medico = _crear_persona(username='medico2', nombre='Med', apellido='Dos', cedula='2000000001')
        self.medico.roles.add(self.rol_medico)
        self.paciente = _crear_persona(
            username='pac2', nombre='Pac', apellido='Dos', cedula='2000000002', sexo='F',
        )

        self.hora_cita = timezone.localtime(timezone.now())
        self.cita = Cita.objects.create(
            persona=self.paciente, medico=self.medico, fecha_hora=self.hora_cita,
            estado=Cita.Estado.CONFIRMADA, tipo_cita=Cita.TipoCita.CONSULTA_GENERAL, motivo='chequeo',
        )
        form = ConsultaForm(
            _datos_consulta(fecha_proxima_cita='2026-08-31'),
            medico=self.medico, paciente=self.paciente, hora_referencia=self.cita.fecha_hora,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.historia = form.guardar_nueva(cita=self.cita, medico=self.medico)

    def test_initial_de_edicion_precarga_fecha_en_formato_iso(self):
        """La fecha guardada (2026-08-31) debe aparecer en el <input> como
        `value="2026-08-31"` -- no `31/08/2026` -- para que el navegador
        la muestre seleccionada."""
        form = ConsultaForm(historia=self.historia)
        self.assertEqual(form.initial['fecha_proxima_cita'], date(2026, 8, 31))
        rendered = str(form['fecha_proxima_cita'])
        self.assertIn('value="2026-08-31"', rendered)
        self.assertNotIn('31/08/2026', rendered)

    def test_guardar_edicion_actualiza_los_campos(self):
        nuevos = _datos_consulta(
            motivo_consulta='Motivo editado',
            tratamiento='Tratamiento editado',
            fecha_proxima_cita='2026-09-15',
        )
        form = ConsultaForm(nuevos, historia=self.historia)
        self.assertTrue(form.is_valid(), form.errors)
        form.guardar_edicion(historia=self.historia)

        self.historia.refresh_from_db()
        self.assertEqual(self.historia.tratamiento, 'Tratamiento editado')
        self.assertEqual(self.historia.motivo_consulta.descripcion, 'Motivo editado')
        self.assertEqual(self.historia.plan_de_manejo.fecha_proxima_cita, date(2026, 9, 15))

    def test_fecha_proxima_cita_es_opcional_al_editar(self):
        """Editar y dejar la fecha en blanco no debe exigirla ni fallar --
        campo opcional también en edición."""
        nuevos = _datos_consulta(fecha_proxima_cita='')
        form = ConsultaForm(nuevos, historia=self.historia)
        self.assertTrue(form.is_valid(), form.errors)
        form.guardar_edicion(historia=self.historia)

        self.historia.refresh_from_db()
        self.assertIsNone(self.historia.plan_de_manejo.fecha_proxima_cita)

    def test_editar_no_valida_choque_de_agenda(self):
        """`editar_historia` no pasa medico/paciente/hora_referencia al
        form -- a diferencia de la consulta nueva, editar la fecha de
        control no re-dispara el chequeo de choque (no crea una cita
        nueva, solo actualiza el dato del plan de manejo)."""
        otro_paciente = _crear_persona(username='pac_otro2', nombre='Otro2', apellido='Pac', cedula='2000000003')
        fecha_choque = date(2026, 10, 1)
        Cita.objects.create(
            persona=otro_paciente, medico=self.medico,
            fecha_hora=self.hora_cita.replace(year=fecha_choque.year, month=fecha_choque.month, day=fecha_choque.day),
            estado=Cita.Estado.CONFIRMADA, tipo_cita=Cita.TipoCita.CONTROL, motivo='choque',
        )
        nuevos = _datos_consulta(fecha_proxima_cita=fecha_choque.isoformat())
        form = ConsultaForm(nuevos, historia=self.historia)
        self.assertTrue(form.is_valid(), form.errors)
