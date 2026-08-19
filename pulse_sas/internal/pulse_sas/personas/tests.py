from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils import timezone

from pulse_sas.internal.pulse_sas.citas.models import Cita

from .forms.historia import ConsultaForm
from .models import (
    HistoriaClinica, HistoriaClinicaPersona, ItemReceta, Jornada, Persona, Receta, Rol,
)


def _crear_persona(*, username, nombre, apellido, cedula, sexo='M', correo=''):
    user = User.objects.create_user(username=username, password='x12345678')
    return Persona.objects.create(
        usuario=user, nombre=nombre, apellido=apellido, cedula=cedula,
        fecha_nacimiento=date(1985, 1, 1), sexo=sexo, correo=correo,
    )


def _datos_consulta(**overrides):
    """Payload base que replica el <form> real de atender_cita.html /
    editar_historia -- todos los campos, incluyendo los opcionales, tal
    como los manda el navegador."""
    data = {
        'motivo_consulta': 'Dolor en el pecho',
        'padecimiento_actual': 'Le duele el pecho',
        'factores_desencadenantes': 'tose sangre',
        'tratamientos_previos': 'Dejar de fumar',
        'antecedentes_familiares': 'cancer de pulmon',
        'antecedentes_personales_patologicos': '',
        'antecedentes_no_patologicos': 'Asma',
        'tratamiento': 'tiene un silvido que puede ser cancer de pulmon',
        'presion_arterial': '150',
        'frecuencia_cardiaca': '0',
        'impresion_diagnostica': 'silvido en el pecho',
        'diagnostico_confirmado': 'cancer de pulmon',
        'tratamiento_indicado': 'dejar de fumar, vapores',
        'recomendaciones': 'dejar de fumar',
        'fecha_proxima_cita': '',
    }
    data.update(overrides)
    return data


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


class AtenderCitaViewTests(TestCase):
    """POST real vía `Client`, igual al <form> del navegador."""

    def setUp(self):
        self.rol_medico = Rol.objects.create(nombre='medico_test', categoria=Rol.Categoria.MEDICO)
        self.medico = _crear_persona(username='medico3', nombre='Med', apellido='Tres', cedula='3000000001')
        self.medico.roles.add(self.rol_medico)
        self.paciente = _crear_persona(
            username='pac3', nombre='Pac', apellido='Tres', cedula='3000000002', sexo='F',
        )
        self.hora_cita = timezone.localtime(timezone.now())
        self.cita = Cita.objects.create(
            persona=self.paciente, medico=self.medico, fecha_hora=self.hora_cita,
            estado=Cita.Estado.CONFIRMADA, tipo_cita=Cita.TipoCita.CONSULTA_GENERAL, motivo='chequeo',
        )
        self.client = Client()
        self.client.login(username='medico3', password='x12345678')

    def test_post_guarda_consulta_y_redirige(self):
        resp = self.client.post(f'/medico/cita/{self.cita.id}/atender/', _datos_consulta())
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(HistoriaClinica.objects.filter(historiaclinicapersona__persona=self.paciente).exists())

    def test_post_sin_fecha_proxima_cita_guarda_igual(self):
        resp = self.client.post(
            f'/medico/cita/{self.cita.id}/atender/', _datos_consulta(fecha_proxima_cita='')
        )
        self.assertEqual(resp.status_code, 302)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.Estado.ATENDIDA)

    def test_post_con_jornada_vacia_no_pierde_los_datos_de_la_consulta(self):
        """Regresión directa del bug reportado: con `Jornada` vacía, poner
        una fecha de control válida no debe tirar todo el formulario."""
        fecha = (self.hora_cita.date() + timedelta(days=10)).isoformat()
        resp = self.client.post(
            f'/medico/cita/{self.cita.id}/atender/', _datos_consulta(fecha_proxima_cita=fecha)
        )
        self.assertEqual(resp.status_code, 302)
        historia = HistoriaClinica.objects.get(historiaclinicapersona__persona=self.paciente)
        self.assertEqual(historia.motivo_consulta.descripcion, 'Dolor en el pecho')
        self.assertEqual(historia.tratamiento, 'tiene un silvido que puede ser cancer de pulmon')


def _formset_management(total, initial=0):
    return {
        'medicamentos-TOTAL_FORMS': str(total),
        'medicamentos-INITIAL_FORMS': str(initial),
        'medicamentos-MIN_NUM_FORMS': '0',
        'medicamentos-MAX_NUM_FORMS': '1000',
    }


class RecetaViewTests(TestCase):
    """Cubre `receta_view` (`/medico/historia/<id>/receta/`). Bug
    reportado: el `<form>` no dejaba agregar más medicamentos a mano --
    solo aparecían filas extra después de un `POST` (recarga completa).
    Se agregó JS para clonar `formset.empty_form` (botón "+ Agregar
    medicamento") y un botón "Eliminar" por fila -- ver
    `medico/receta.html`. Estos tests cubren el backend (guardar,
    eliminar, campo vacío ignorado); el clonado en el navegador no es
    testeable acá, solo que el HTML que la JS necesita esté presente."""

    def setUp(self):
        self.rol_medico = Rol.objects.create(nombre='medico_test', categoria=Rol.Categoria.MEDICO)
        self.medico = _crear_persona(username='medico_receta', nombre='Med', apellido='Receta', cedula='4000000001')
        self.medico.roles.add(self.rol_medico)
        self.paciente = _crear_persona(
            username='pac_receta', nombre='Pac', apellido='Receta', cedula='4000000002', sexo='F',
        )

        self.historia = HistoriaClinica.objects.create(
            tratamiento='reposo', fecha_ingreso_paciente=timezone.now(),
        )
        HistoriaClinicaPersona.objects.create(
            historia_clinica=self.historia, persona=self.paciente,
            rol_en_historia=HistoriaClinicaPersona.RolEnHistoria.PACIENTE,
        )
        HistoriaClinicaPersona.objects.create(
            historia_clinica=self.historia, persona=self.medico,
            rol_en_historia=HistoriaClinicaPersona.RolEnHistoria.MEDICO_TRATANTE,
        )

        self.client = Client()
        self.client.login(username='medico_receta', password='x12345678')
        self.url = f'/medico/historia/{self.historia.id}/receta/'

    def test_get_incluye_empty_form_y_boton_agregar_para_la_js(self):
        """El HTML debe traer el `<template>` con `__prefix__` y el botón
        "+" -- son lo que la JS de agregar-fila necesita para funcionar."""
        resp = self.client.get(self.url)
        html = resp.content.decode('utf-8')
        self.assertIn('id="btn-agregar-medicamento"', html)
        self.assertIn('id="medicamento-empty-row"', html)
        self.assertIn('medicamentos-__prefix__-medicamento', html)
        self.assertIn('btn-eliminar-medicamento', html)

    def test_post_guarda_receta_y_medicamentos(self):
        data = {
            'indicaciones_generales': 'Tomar con abundante agua',
            **_formset_management(total=2, initial=0),
            'medicamentos-0-medicamento': 'Acetaminofén',
            'medicamentos-0-dosis': '500mg',
            'medicamentos-0-frecuencia': 'cada 8 horas',
            'medicamentos-0-duracion': '5 días',
            'medicamentos-0-indicaciones': 'Con alimentos',
            'medicamentos-1-medicamento': '',
            'medicamentos-1-dosis': '',
            'medicamentos-1-frecuencia': '',
            'medicamentos-1-duracion': '',
            'medicamentos-1-indicaciones': '',
        }
        resp = self.client.post(self.url, data)
        self.assertEqual(resp.status_code, 302)

        receta = Receta.objects.get(historia_clinica=self.historia)
        self.assertEqual(receta.indicaciones_generales, 'Tomar con abundante agua')
        items = list(receta.medicamentos.all())
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].medicamento, 'Acetaminofén')
        self.assertEqual(items[0].dosis, '500mg')

    def test_agregar_medicamento_extra_vale_como_fila_nueva_al_guardar(self):
        """Simula lo que hace la JS: el navegador manda TOTAL_FORMS más
        alto que INITIAL_FORMS con una fila nueva rellenada -- debe
        guardarse como medicamento nuevo."""
        receta = Receta.objects.create(historia_clinica=self.historia)
        existente = ItemReceta.objects.create(receta=receta, medicamento='Ibuprofeno', dosis='400mg')

        data = {
            'indicaciones_generales': '',
            **_formset_management(total=2, initial=1),
            'medicamentos-0-id': str(existente.id),
            'medicamentos-0-medicamento': 'Ibuprofeno',
            'medicamentos-0-dosis': '400mg',
            'medicamentos-0-frecuencia': '',
            'medicamentos-0-duracion': '',
            'medicamentos-0-indicaciones': '',
            'medicamentos-1-medicamento': 'Loratadina',
            'medicamentos-1-dosis': '10mg',
            'medicamentos-1-frecuencia': 'cada 24 horas',
            'medicamentos-1-duracion': '3 días',
            'medicamentos-1-indicaciones': '',
        }
        resp = self.client.post(self.url, data)
        self.assertEqual(resp.status_code, 302)

        receta.refresh_from_db()
        medicamentos = set(receta.medicamentos.values_list('medicamento', flat=True))
        self.assertEqual(medicamentos, {'Ibuprofeno', 'Loratadina'})

    def test_marcar_eliminar_borra_el_medicamento_existente(self):
        """Simula el botón "Eliminar" en una fila ya guardada -- la JS
        marca el checkbox `DELETE` oculto, el POST debe borrar el item."""
        receta = Receta.objects.create(historia_clinica=self.historia)
        existente = ItemReceta.objects.create(receta=receta, medicamento='Ibuprofeno', dosis='400mg')

        data = {
            'indicaciones_generales': '',
            **_formset_management(total=1, initial=1),
            'medicamentos-0-id': str(existente.id),
            'medicamentos-0-medicamento': 'Ibuprofeno',
            'medicamentos-0-dosis': '400mg',
            'medicamentos-0-frecuencia': '',
            'medicamentos-0-duracion': '',
            'medicamentos-0-indicaciones': '',
            'medicamentos-0-DELETE': 'on',
        }
        resp = self.client.post(self.url, data)
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(ItemReceta.objects.filter(id=existente.id).exists())

    def test_fila_vacia_no_crea_medicamento_fantasma(self):
        """Una fila agregada con la JS y no rellenada (o "Eliminar" antes
        de guardar, que la vacía) no debe guardarse como registro vacío."""
        data = {
            'indicaciones_generales': 'Reposo',
            **_formset_management(total=1, initial=0),
            'medicamentos-0-medicamento': '',
            'medicamentos-0-dosis': '',
            'medicamentos-0-frecuencia': '',
            'medicamentos-0-duracion': '',
            'medicamentos-0-indicaciones': '',
        }
        resp = self.client.post(self.url, data)
        self.assertEqual(resp.status_code, 302)
        receta = Receta.objects.get(historia_clinica=self.historia)
        self.assertEqual(receta.medicamentos.count(), 0)
