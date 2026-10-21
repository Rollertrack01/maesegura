from django.contrib import admin
from django.urls import include, path

from apps.core import views as core_views

urlpatterns = [
    path("", include("apps.acompanhamento.urls")),
    path("assistente/", include("apps.assistente.urls")),
    path("", include("apps.painel.urls")),
    path("saude/", core_views.saude, name="saude"),
    path("sw.js", core_views.service_worker, name="service-worker"),
    path("offline/", core_views.offline, name="offline"),
    path("gestao/", admin.site.urls),
]
