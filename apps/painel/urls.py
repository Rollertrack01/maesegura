from django.urls import path

from . import views

urlpatterns = [
    path("painel/", views.painel, name="painel"),
    path("api/metricas.json", views.metricas_json, name="metricas-json"),
]
