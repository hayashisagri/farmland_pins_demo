from django.urls import path

from . import views

urlpatterns = [
    path("", views.root_view, name="root"),
    path('map/', views.map_view, name='map'),
]