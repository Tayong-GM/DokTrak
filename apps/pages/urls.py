from django.urls import path

from . import views
from .create_file_view import create_file as create_file_page
from .scan_document_view import scan_document as scan_document_page
from .recent_files_view import recent_files as recent_files_page, edit_file, delete_file, update_file_status
from .dashboard_view import dashboard as dashboard_page

urlpatterns = [
    path('', dashboard_page, name='index'),
    path('profile/', views.profile, name='profile'),
    path('create-file/', create_file_page, name='create_file'),
    path('check-status/', views.check_status, name='check_status'),
    path('scan-document/', scan_document_page, name='scan_document'),
    path('recent-files/', recent_files_page, name='recent_files'),
    path('files/<int:pk>/edit/', edit_file, name='edit_file'),
    path('files/<int:pk>/delete/', delete_file, name='delete_file'),
    path('files/<int:pk>/status/', update_file_status, name='update_file_status'),
    
]
