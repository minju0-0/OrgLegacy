from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.shared.selectors import organizations_for_home


@login_required
def home_view(request):
    return render(request, "home/home.html", {"organizations": organizations_for_home(request.user)})
