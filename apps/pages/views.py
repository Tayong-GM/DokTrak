from django.shortcuts import render


def index(request):
    return render(request, 'pages/index.html', {'segment': 'dashboard'})


def tables(request):
    return render(request, 'pages/tables.html', {'segment': 'tables'})


def billing(request):
    return render(request, 'pages/billing.html', {'segment': 'billing'})


def virtual_reality(request):
    return render(request, 'pages/virtual-reality.html', {'segment': 'virtual_reality'})


def rtl(request):
    return render(request, 'pages/rtl.html', {'segment': 'rtl'})


def profile(request):
    return render(request, 'pages/profile.html', {'segment': 'profile'})
