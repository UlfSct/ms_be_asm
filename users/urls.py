from django.urls import path
from .views import RegistrationView, LoginView, LogoutView, ProfileView, CheckAdminView, TeamView, TeamUserViewSet, \
    TeamActionsViewSet, AdminUsersView

app_name = 'users'

urlpatterns = [
    path('register/', RegistrationView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/admin/', CheckAdminView.as_view(), name='check-admin'),
    path('team/', TeamView.as_view(), name='team'),
    path('team/leave/', TeamActionsViewSet.as_view({'post': 'leave'}), name='team-leave'),
    path('team/delete/', TeamActionsViewSet.as_view({'delete': 'delete'}), name='team-delete'),
    path('team/update/', TeamActionsViewSet.as_view({'patch': 'update'}), name='team-update'),
    path('teamusers/invite/', TeamUserViewSet.as_view({'post': 'invite'}), name='teamuser-invite'),
    path('teamusers/<int:pk>/accept/', TeamUserViewSet.as_view({'post': 'accept'}), name='teamuser-accept'),
    path('teamusers/<int:pk>/reject/', TeamUserViewSet.as_view({'post': 'reject'}), name='teamuser-reject'),
    path('teamusers/<int:pk>/make-admin/', TeamUserViewSet.as_view({'post': 'make_admin'}), name='teamuser-make-admin'),
    path('teamusers/<int:pk>/remove-admin/', TeamUserViewSet.as_view({'post': 'remove_admin'}), name='teamuser-remove-admin'),
    path('teamusers/<int:pk>/transfer-creator/', TeamUserViewSet.as_view({'post': 'transfer_creator'}), name='teamuser-transfer-creator'),
    path('teamusers/<int:pk>/remove-user/', TeamUserViewSet.as_view({'delete': 'remove_user'}), name='teamuser-remove-user'),
    path('admin/users/', AdminUsersView.as_view({'get': 'list'}), name='admin-users'),
    path('admin/users/<int:pk>/', AdminUsersView.as_view({'patch': 'partial_update'}), name='admin-users-update')
]