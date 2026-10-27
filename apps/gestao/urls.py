from django.urls import path

from . import views

app_name = "gestao"

urlpatterns = [
    path("entrar/", views.entrar, name="entrar"),
    path("sair/", views.sair, name="sair"),
    path("", views.painel, name="painel"),
    path("conteudos/", views.conteudos, name="conteudos"),
    path("conteudos/<int:pk>/", views.conteudo_editar, name="conteudo-editar"),
    path("conteudos/<int:pk>/validar/", views.conteudo_validar, name="conteudo-validar"),
    path("conteudos/<int:pk>/retirar/", views.conteudo_retirar, name="conteudo-retirar"),
    path("consultas/", views.consultas, name="consultas"),
    path("consultas/<int:pk>/estado/", views.consulta_marcar, name="consulta-marcar"),
    path("gestantes/", views.gestantes, name="gestantes"),
    path("unidades/", views.unidades, name="unidades"),
    path("unidades/nova/", views.unidade_editar, name="unidade-nova"),
    path("unidades/<int:pk>/", views.unidade_editar, name="unidade-editar"),
    path("equipa/", views.equipa, name="equipa"),
    path("seguranca/", views.seguranca, name="seguranca"),
    path("exportar/indicadores.csv", views.exportar_metricas, name="exportar-indicadores"),
]
