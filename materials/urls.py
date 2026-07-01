from django.urls import path
from .views import MaterialViewSet, AdminMaterialViewSet

app_name = 'materials'

urlpatterns = [
    path('materials/', MaterialViewSet.as_view({'get': 'list', 'post': 'create'}), name='materials'),
    path('materials/<int:pk>/', MaterialViewSet.as_view({'patch': 'partial_update', 'delete': 'destroy', 'get': 'retrieve'}), name='materials-detail'),
    path('materials/selector/', MaterialViewSet.as_view({'get': 'selector'}), name='materials-selector'),
    path('admin/materials/', AdminMaterialViewSet.as_view({'get': 'list', 'post': 'create'}), name='materials'),
    path('admin/materials/<int:pk>/', AdminMaterialViewSet.as_view({'patch': 'partial_update', 'delete': 'destroy', 'get': 'retrieve'}), name='materials-detail'),
]