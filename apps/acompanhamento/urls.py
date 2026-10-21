from django.urls import path

from . import views

app_name = "acompanhamento"

urlpatterns = [
    path("", views.registo, name="registo"),
    path("entrar/", views.entrar, name="entrar"),
    path("acompanhamento/", views.inicio, name="inicio"),
    path("sair/", views.sair, name="sair"),
]
