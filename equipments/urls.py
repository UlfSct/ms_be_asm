from django.urls import path

from .views import AdminEquipmentTypeViewSet, EquipmentTypeViewSet, AdminEquipmentViewSet, EquipmentViewSet, EquipmentHoleViewSet

app_name = 'equipments'

urlpatterns = [
    path('admin/types/', AdminEquipmentTypeViewSet.as_view({'get': 'list', 'post': 'create'}), name='equipment-types'),
    path('admin/types/<int:pk>/', AdminEquipmentTypeViewSet.as_view({'patch': 'partial_update', 'delete': 'destroy'}), name='equipment-types-detail'),
    path('types/selector/', EquipmentTypeViewSet.as_view({'get': 'list'}), name='equipment-types-selector'),
    path('equipments/', EquipmentViewSet.as_view({'get': 'list', 'post': 'create'}), name='equipments'),
    path('equipments/<int:pk>/', EquipmentViewSet.as_view({'patch': 'partial_update', 'delete': 'destroy', 'get': 'retrieve'}), name='equipments-detail'),
    path('equipments/selector/', EquipmentViewSet.as_view({'get': 'selector'}), name='equipments-selector'),
    path('admin/equipments/', AdminEquipmentViewSet.as_view({'get': 'list', 'post': 'create'}), name='admin-equipments'),
    path('admin/equipments/<int:pk>/', AdminEquipmentViewSet.as_view({'patch': 'partial_update', 'delete': 'destroy', 'get': 'retrieve'}), name='admin-equipments-detail'),
    path('holes/', EquipmentHoleViewSet.as_view({'get': 'list', 'post': 'create'}), name='equipment-holes'),
    path('holes/<int:pk>/', EquipmentHoleViewSet.as_view({'patch': 'partial_update', 'delete': 'destroy'}), name='equipment-holes-detail'),
]
