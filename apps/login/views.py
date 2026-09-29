from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect

from .forms import CustomLoginForm


class OrgLegacyLoginView(LoginView):
    template_name = 'login/login.html'
    form_class = CustomLoginForm
    redirect_authenticated_user = True


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')