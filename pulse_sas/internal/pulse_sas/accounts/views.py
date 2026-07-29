from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import RegistroForm


class AccountsLoginView(LoginView):
    template_name = 'login/login.html'


class AccountsLogoutView(LogoutView):
    next_page = reverse_lazy('login')


def registro(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = RegistroForm()

    return render(request, 'login/registro.html', {'form': form})


@login_required
def dashboard(request):
    return render(request, 'login/dashboard.html')
