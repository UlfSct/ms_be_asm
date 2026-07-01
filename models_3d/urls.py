from django.urls import path

from models_3d.views import Model3DViewSet, AdminModel3DViewSet

app_name = 'models_3d'

urlpatterns = [
    path('models/', Model3DViewSet.as_view({'get': 'list', 'post': 'create'}), name='models'),
    path('models/<int:pk>/', Model3DViewSet.as_view({'patch': 'partial_update', 'delete': 'destroy', 'get': 'retrieve'}), name='models-detail'),
    path('models/selector/', Model3DViewSet.as_view({'get': 'selector'}), name='models-selector'),
    path('admin/models/', AdminModel3DViewSet.as_view({'get': 'list', 'post': 'create'}), name='models'),
    path('admin/models/<int:pk>/', AdminModel3DViewSet.as_view({'patch': 'partial_update', 'delete': 'destroy', 'get': 'retrieve'}), name='models-detail'),
]
