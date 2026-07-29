from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.AccountsLoginView.as_view(), name='login'),
    path('logout/', views.AccountsLogoutView.as_view(), name='logout'),
    path('registro/', views.registro, name='registro'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('', views.AccountsLoginView.as_view(), name='home'),
]
