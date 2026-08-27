from datetime import timedelta

from django.test import Client, TestCase
from django.utils import timezone

from pulse_sas.internal.pulse_sas.citas.models import Cita
from pulse_sas.internal.pulse_sas.personas.models import (
    HistoriaClinica, HistoriaClinicaPersona, ItemReceta, Receta, Rol,
)

from .helpers import _crear_persona, _datos_consulta, _formset_management


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
