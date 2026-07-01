from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.mixins import UpdateModelMixin, ListModelMixin
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import GenericViewSet

from be_asm_3d.utils import DefaultPagination
from ..filters import UserFilter
from ..models import User
from ..serializers import RegistrationSerializer, LoginSerializer, ProfileSerializer, ProfileUpdateSerializer, \
    AdminUserRetrieveSerializer, AdminUserUpdateSerializer
from be_asm_3d.permissions import IsAuthenticated, IsAdmin


class RegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.auth.delete()
        return Response({'detail': 'Успешный выход из системы.'}, status=status.HTTP_200_OK)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = ProfileSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            profile_serializer = ProfileSerializer(request.user)
            return Response(profile_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CheckAdminView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'is_admin': request.user.is_admin
        }, status=status.HTTP_200_OK)


class AdminUsersView(UpdateModelMixin, ListModelMixin, GenericViewSet):
    def get_serializer_class(self):
        serializer_map = {
            'list': AdminUserRetrieveSerializer,
            'partial_update': AdminUserUpdateSerializer
        }
        return serializer_map.get(self.action, self.serializer_class)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['user_id'] = self.request.user.id
        return context

    permission_classes = [IsAdmin]
    queryset = User.objects.all().order_by('-id')
    serializer_class = AdminUserRetrieveSerializer
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = UserFilter
