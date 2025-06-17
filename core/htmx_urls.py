# core/htmx_urls.py
from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    path("reservations/",
         TemplateView.as_view(template_name="reservation_list.html"),
         name="reservation_list"),
    path("reservations/form/",
         TemplateView.as_view(template_name="reservation_form.html"),
         name="reservation_form"),
]
