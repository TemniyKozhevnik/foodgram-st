from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import routers
from django.views.generic import TemplateView

#from client.views import ClientViewSet


# router = routers.DefaultRouter()
# router.register(r'client', ClientViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('api/', include('djoser.urls')),  # Работа с пользователями
    path('api/auth/', include('djoser.urls.authtoken')),  # Работа с токенами
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += (path('__debug__/', include(debug_toolbar.urls)),) 
