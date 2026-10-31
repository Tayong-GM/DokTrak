from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('tables/', views.tables, name='tables'),
    path('billing/', views.billing, name='billing'),
    path('virtual-reality/', views.virtual_reality, name='vr'),
    path('rtl/', views.rtl, name='rtl'),
    path('profile/', views.profile, name='profile'),
]
