from django.urls import path

from . import views
from .create_file_view import create_file as create_file_page


urlpatterns = [
    path('', views.index, name='index'),
    path('tables/', views.tables, name='tables'),
    path('billing/', views.billing, name='billing'),
    path('profile/', views.profile, name='profile'),
    path('create-file/', create_file_page, name='create_file'),
    path('check-status/', views.check_status, name='check_status'),
    path('scan-document/', views.scan_document, name='scan_document'),
    path('recent-files/', views.recent_files, name='recent_files'),
]
