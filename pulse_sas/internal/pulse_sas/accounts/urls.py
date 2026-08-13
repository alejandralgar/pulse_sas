from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from pulse_sas.internal.pulse_sas.personas import views as personas_views
from pulse_sas.internal.pulse_sas.citas import views as citas_views

urlpatterns = [
    path('',                    views.login_view,         name='home'),
    path('login/',              views.login_view,         name='login'),
    path('logout/',             views.AccountsLogoutView.as_view(), name='logout'),
    path('dashboard/',          views.dashboard,          name='dashboard'),
    path('cuenta/perfil/',      personas_views.mi_perfil, name='mi_perfil'),

    # ── Recuperar contraseña ─────────────────────────────────────────
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='login/password_reset_form.html',
            email_template_name='login/password_reset_email.html',
            subject_template_name='login/password_reset_subject.txt',
        ),
        name='password_reset',
    ),
    path(
        'password-reset/enviado/',
        auth_views.PasswordResetDoneView.as_view(template_name='login/password_reset_done.html'),
        name='password_reset_done',
    ),
    path(
        'password-reset/confirmar/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(template_name='login/password_reset_confirm.html'),
        name='password_reset_confirm',
    ),
    path(
        'password-reset/completado/',
        auth_views.PasswordResetCompleteView.as_view(template_name='login/password_reset_complete.html'),
        name='password_reset_complete',
    ),

    # Acceso directo por rol
    path('dashboard/admin/',          views.vista_admin,         name='dashboard_admin'),
    path('dashboard/administrativo/', views.vista_administrativo, name='dashboard_administrativo'),
    path('dashboard/medico/',         views.vista_medico,        name='dashboard_medico'),
    path('dashboard/enfermera/',      views.vista_enfermera,     name='dashboard_enfermera'),
    path('dashboard/guardia/',        views.vista_guardia,       name='dashboard_guardia'),
    path('dashboard/cliente/',        views.vista_cliente,       name='dashboard_cliente'),
    path('dashboard/empresa/',        views.vista_empresa,       name='dashboard_empresa'),

    # ── Cliente / Paciente ──────────────────────────────────────────
    path('cliente/perfil/',           personas_views.actualizar_perfil,           name='cliente_perfil'),
    path('cliente/contacto/',         personas_views.guardar_contacto_emergencia, name='cliente_contacto'),
    path('cliente/cita/solicitar/',   citas_views.solicitar_cita,                 name='cliente_solicitar_cita'),
    path('cliente/cita/horarios/',    citas_views.horarios_disponibles,           name='cliente_horarios'),

    # ── Historia clínica / receta ("epicrisis") ──────────────────────
    path('medico/cita/<int:cita_id>/atender/',        personas_views.atender_cita,      name='atender_cita'),
    path('medico/paciente/<int:persona_id>/historias/', personas_views.historia_paciente, name='historia_paciente'),
    path('medico/historia/<int:historia_id>/',        personas_views.historia_detalle,  name='historia_detalle'),
    path('medico/historia/<int:historia_id>/editar/', personas_views.editar_historia,   name='editar_historia'),
    path('medico/historia/<int:historia_id>/receta/', personas_views.receta_view,       name='ver_receta'),
]
