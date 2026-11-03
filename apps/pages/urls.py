from django.urls import path

from . import views
from .create_file_view import create_file as create_file_page
from .scan_document_view import scan_document as scan_document_page


urlpatterns = [
    path('', views.index, name='index'),
    path('tables/', views.tables, name='tables'),
    path('billing/', views.billing, name='billing'),
    path('profile/', views.profile, name='profile'),
    path('create-file/', create_file_page, name='create_file'),
    path('check-status/', views.check_status, name='check_status'),
    path('scan-document/', scan_document_page, name='scan_document'),
    path('recent-files/', views.recent_files, name='recent_files'),
]
