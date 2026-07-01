from django.urls import path
from .views import ResultViewSet

app_name = 'results'

urlpatterns = [
    path('results/', ResultViewSet.as_view({'get': 'list'}), name='results-list'),
    path('results/<int:pk>/', ResultViewSet.as_view({'delete': 'destroy'}), name='results-detail'),
    path('results/<int:pk>/full/', ResultViewSet.as_view({'get': 'full'}), name='results-full'),
    path('results/<int:pk>/optimize/', ResultViewSet.as_view({'post': 'optimize'}), name='results-optimize'),
]