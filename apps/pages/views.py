from django.shortcuts import render


def index(request):
    return render(request, 'pages/index.html', {'segment': 'dashboard'})


def tables(request):
    return render(request, 'pages/tables.html', {'segment': 'tables'})


def billing(request):
    return render(request, 'pages/billing.html', {'segment': 'billing'})





def profile(request):
    return render(request, 'pages/profile.html', {'segment': 'profile'})

def create_file(request):
    return render(request, 'pages/create_file.html', {'segment': 'create_file'})

def check_status(request):
    return render(request, 'pages/check_status.html', {'segment': 'check_status'})

def scan_document(request):
    return render(request, 'pages/scan_document.html', {'segment': 'scan_document'})

def recent_files(request):
    return render(request, 'pages/Recent_files.html', {'segment': 'recent_files'})
