from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from generate import views

urlpatterns = [
    path('', views.generate_gradient, name='generate_gradient'),
    path('gradient/', views.generate_gradient, name='generate_gradient'),
    path('gradient/palette/', views.get_saved_palette, name='get_saved_palette'),
    path('gradient/<int:palette_id>/', views.get_palette, name='get_palette'),
    path('gradient/<int:pk>/edit/', views.PaletteUpdateView.as_view(), name='edit-palette'),
    path('gradient/<int:pk>/delete/', views.PaletteDeleteView.as_view(), name='delete-palette'),
    path('api/gradient/', views.GradientAPIView.as_view(), name='api_gradient'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
]