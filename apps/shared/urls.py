from django.urls import path

from apps.shared.views.base import HomeView, DefaultView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("default/", DefaultView.as_view(), name="default"),
]
