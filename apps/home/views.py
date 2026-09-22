from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home_view(request):
    """
    Home screen. Requires login (this is the vertical slice's landing
    point after authentication). It greets the user and previews the
    feature slices planned next (Event Logger, Supplier Directory,
    Handover Notes, Adviser Sign-off) as "coming soon" tiles, each of
    which will become its own vertical slice/app when built.
    """
    return render(request, 'home/home.html', {'user': request.user})
