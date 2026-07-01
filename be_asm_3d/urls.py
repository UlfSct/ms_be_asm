''"""
URL configuration for be_asm_3d project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from rest_framework import routers
from django.conf.urls.static import static

from be_asm_3d import settings
from model_constructor.views import *
from users.views import *


model_constructor_router = routers.DefaultRouter()
model_constructor_router.register(r'projects', ProjectViewSet, basename='project')
model_constructor_router.register(r'parts', PartViewSet, basename='part')
model_constructor_router.register(r'assemblies', AssemblyViewSet, basename='assembly')

urlpatterns = [
    path('users/', include('users.urls')),
    path('materials/', include('materials.urls')),
    path('equipments/', include('equipments.urls')),
    path('models/', include('models_3d.urls')),
    path('schemes/', include('schemes.urls')),
    path('results/', include('results.urls')),
    path('constructor/', include(model_constructor_router.urls)),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)