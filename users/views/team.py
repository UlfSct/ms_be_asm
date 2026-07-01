from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from be_asm_3d.permissions import IsAuthenticated
from ..models import TeamUser, Team
from ..serializers import TeamInfoSerializer, TeamCreateSerializer, TeamUpdateSerializer, TeamLeaveSerializer, \
    TeamDeleteSerializer, TeamUserInvitesListSerializer


class TeamView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        team_users = TeamUser.objects.filter(user=request.user).select_related('user', 'team')
        team_user = team_users.filter(is_approved=True).first()

        if team_user:
            team = team_user.team
            serializer = TeamInfoSerializer(team, context={'request': request})
            return Response(serializer.data)

        invites_serializer = TeamUserInvitesListSerializer(team_users.filter(is_approved=None), many=True)

        return Response({
            'name': None,
            'created': None,
            'is_creator': False,
            'is_admin': False,
            'users': list(invites_serializer.data)
        })

    def post(self, request):
        if TeamUser.objects.filter(user=request.user).exists():
            return Response(
                {'error': 'Вы уже состоите в команде. Покините текущую команду перед созданием новой.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = TeamCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            team = serializer.save()

            response_serializer = TeamInfoSerializer(team, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TeamActionsViewSet(ModelViewSet):
    queryset = Team.objects.all()

    def get_serializer_class(self):
        if self.action == 'update':
            return TeamUpdateSerializer
        elif self.action == 'leave':
            return TeamLeaveSerializer
        elif self.action == 'delete':
            return TeamDeleteSerializer
        return TeamInfoSerializer

    def get_team_membership(self, user):
        try:
            return TeamUser.objects.select_related('team').get(
                user=user,
                is_approved=True
            )
        except TeamUser.DoesNotExist:
            return None

    @action(detail=True, methods=['post'], url_path='leave')
    def leave(self, request, pk=None):
        membership = self.get_team_membership(request.user)

        if not membership:
            raise ValidationError('Вы не состоите в команде.')

        serializer = self.get_serializer(data={})
        serializer.is_valid(raise_exception=True)

        membership = serializer.validate_leave(membership.team, request.user)
        serializer.leave(membership)

        return Response(
            {'detail': 'Вы успешно вышли из команды.'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['delete'], url_path='delete')
    def delete(self, request, pk=None):
        membership = self.get_team_membership(request.user)

        if not membership:
            raise ValidationError('Вы не состоите в команде.')

        team = membership.team

        serializer = self.get_serializer(data={})
        serializer.is_valid(raise_exception=True)

        serializer.validate_delete(team, request.user)
        serializer.delete(team)

        return Response(
            {'detail': 'Команда успешно удалена.'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['patch'], url_path='update')
    def update(self, request, pk=None):
        membership = self.get_team_membership(request.user)

        if not membership:
            raise ValidationError('Вы не состоите в команде.')

        team = membership.team

        serializer = self.get_serializer(
            team,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = TeamInfoSerializer(
            team,
            context={'request': request}
        )

        return Response(response_serializer.data)