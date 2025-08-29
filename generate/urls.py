from django.urls import path
from generate import views

urlpatterns = [
    path('', views.generate_gradient, name='generate_gradient'),
]