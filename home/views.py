from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home_view(request):
    """
    Home screen. Requires login (this is the vertical slice's landing
    point after authentication). For this exam version it simply
    greets the user and role; later slices (Event Logger, Supplier
    Directory, Handover Notes, Adviser Sign-off) will plug in here.
    """
    return render(request, 'home/home.html', {'user': request.user})
