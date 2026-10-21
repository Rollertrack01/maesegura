from django.urls import path

from . import views

app_name = "assistente"

urlpatterns = [
    path("", views.assistente, name="assistente"),
    path("conhecimento.json", views.conhecimento_json, name="conhecimento-json"),
]
