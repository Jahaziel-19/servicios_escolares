from django.urls import path
from .views import importar_excel, importar_modelo

urlpatterns = [
    path('', importar_excel, name='importar_excel'),
    path('importar/<int:pk>/', importar_modelo, name='importar_modelo'),
]
