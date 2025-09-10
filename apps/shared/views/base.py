from django.views.generic import TemplateView


class HomeView(TemplateView):
    template_name = "main.html"

class DefaultView(TemplateView):
    template_name = "index.html"