from django.urls import path

from . import views
from .create_file_view import create_file as create_file_page
from .scan_document_view import scan_document as scan_document_page
from .recent_files_view import recent_files as recent_files_page, archived_files as archived_files_page, archive_file, edit_file, delete_file
from .dashboard_view import dashboard as dashboard_page
from .handoff_view import (inbox, sent, send_file, receive_file,
                           forward_file, inbox_status, review_file, recall_transfer, respond_recall)

urlpatterns = [
    path('', dashboard_page, name='index'),
    path('accounts/register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('create-file/', create_file_page, name='create_file'),
    path('check-status/', views.check_status, name='check_status'),
    path('scan-document/', scan_document_page, name='scan_document'),
    path('recent-files/', recent_files_page, name='recent_files'),
    path('archived-files/', archived_files_page, name='archived_files'),
    path('files/<int:pk>/archive/', archive_file, name='archive_file'),
    path('files/<int:pk>/edit/', edit_file, name='edit_file'),
    path('files/<int:pk>/delete/', delete_file, name='delete_file'),
        path('inbox/', inbox, name='inbox'),
    path('sent/', sent, name='sent'),
    path('handoff/send/', send_file, name='send_file'),
    path('handoff/<int:pk>/receive/', receive_file, name='receive_file'),
    path('handoff/<int:pk>/forward/', forward_file, name='forward_file'),
    path('handoff/<int:pk>/status/', inbox_status, name='inbox_status'),
    path('handoff/<int:pk>/review/', review_file, name='review_file'),
    path('handoff/<int:pk>/recall/', recall_transfer, name='recall_transfer'),
    path('handoff/<int:pk>/recall-response/', respond_recall, name='respond_recall'),
    
]
