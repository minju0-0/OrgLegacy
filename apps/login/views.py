from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect


class OrgLegacyLoginView(LoginView):
    """
    Login screen. Uses Django's battle-tested auth backend for
    authentication, but renders our own OrgLegacy-branded template.
    Owns nothing but the login experience itself — account creation
    lives in the register app, not here.
    """
    template_name = 'login/login.html'
    redirect_authenticated_user = True


def logout_view(request):
    """
    Logs out the user and redirects to the login screen.
    Kept in the login feature because logging out is part of the
    session/authentication lifecycle, not the Home experience.
    """
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login:login')
