from django.contrib import admin
from django.urls import include, path

from apps.core import views as core_views

urlpatterns = [
    path("", include("apps.acompanhamento.urls")),
    path("assistente/", include("apps.assistente.urls")),
    path("", include("apps.painel.urls")),
    path("gestao/", include("apps.gestao.urls")),
    path("saude/", core_views.saude, name="saude"),
    path("sw.js", core_views.service_worker, name="service-worker"),
    path("offline/", core_views.offline, name="offline"),
    # Django admin: manutenção técnica, só superuser. O trabalho do dia-a-dia
    # faz-se no painel próprio em /gestao/.
    path("sistema/", admin.site.urls),
]
