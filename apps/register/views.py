from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import RegisterForm


def register_view(request):
    """
    Registration screen. On success, redirects the user to the login
    screen (a different feature) with a success message so they can
    log in. Account creation stays entirely inside this app.
    """
    if request.user.is_authenticated:
        return redirect('home:home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully. Please log in.")
            return redirect('login:login')
    else:
        form = RegisterForm()

    return render(request, 'register/register.html', {'form': form})
