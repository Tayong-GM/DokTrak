from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .forms import DokTrakRegistrationForm, UserProfileForm


def index(request):
    return render(request, 'pages/index.html', {'segment': 'dashboard'})








@login_required(login_url='login')
def profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile details have been updated.')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'pages/profile.html', {
        'segment': 'profile',
        'form': form,
    })


def register(request):
    if request.method == 'POST':
        form = DokTrakRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your account is ready. Sign in to continue.')
            return redirect('login')
    else:
        form = DokTrakRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

def create_file(request):
    return render(request, 'pages/create_file.html', {'segment': 'create_file'})

def check_status(request):
    return render(request, 'pages/check_status.html', {'segment': 'check_status'})

def scan_document(request):
    return render(request, 'pages/scan_document.html', {'segment': 'scan_document'})

def recent_files(request):
    return render(request, 'pages/Recent_files.html', {'segment': 'recent_files'})
