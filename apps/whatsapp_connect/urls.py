from django.urls import path

from . import views

app_name = "whatsapp_connect"

urlpatterns = [
    path("<uuid:workspace_id>/whatsapp/", views.connect, name="connect"),
    path("<uuid:workspace_id>/whatsapp/<uuid:pk>/", views.pairing, name="pairing"),
    path("<uuid:workspace_id>/whatsapp/<uuid:pk>/status.json", views.status_json, name="status_json"),
    path("<uuid:workspace_id>/whatsapp/<uuid:pk>/disconnect", views.disconnect, name="disconnect"),
]
