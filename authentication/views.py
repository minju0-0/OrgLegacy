from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.shortcuts import render, redirect
from .forms import RegisterForm


def logout_view(request):
    """
    Logs out the user and redirects to login page.
    Supports both POST and GET to prevent 405 Method Not Allowed errors.
    """
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('authentication:login')


class OrgLegacyLoginView(LoginView):
    """
    Login screen. Uses Django's battle-tested auth backend for
    authentication, but renders our own OrgLegacy-branded template.
    """
    template_name = 'authentication/login.html'
    redirect_authenticated_user = True


def register_view(request):
    """
    Registration screen. On success, redirects the user to the login screen
    with a success message so they can log in.
    """
    if request.user.is_authenticated:
        return redirect('home:home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully. Please log in.")
            return redirect('authentication:login')
    else:
        form = RegisterForm()

    return render(request, 'authentication/register.html', {'form': form})
