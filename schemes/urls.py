from django.urls import path
from .views import SchemeViewSet

app_name = 'schemes'

urlpatterns = [
    path('schemes/', SchemeViewSet.as_view({'get': 'list', 'post': 'create'}), name='schemes'),
    path('schemes/<int:pk>/', SchemeViewSet.as_view({'patch': 'partial_update', 'delete': 'destroy', 'get': 'retrieve'}), name='schemes-detail'),
    path('schemes/<int:pk>/full/', SchemeViewSet.as_view({'get': 'full', 'put': 'full_update'}), name='schemes-full'),
    path('schemes/<int:pk>/convert-to-result/', SchemeViewSet.as_view({'post': 'convert_to_result'}), name='schemes-convert-to-result'),
]