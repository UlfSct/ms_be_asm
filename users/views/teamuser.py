from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from be_asm_3d.permissions import IsAuthenticated
from ..models import TeamUser, User
from ..serializers import TeamUserSerializer, TeamUserInviteSerializer, TeamUserAcceptRejectSerializer, \
    TeamUserAdminSerializer, TeamUserTransferSerializer, TeamUserRemoveSerializer
from django.db.models import Q


def _get_creator_permission(team, team_member):
    return team.creator == team_member.user


def _check_creator_permission(team, user):
    if team.creator != user:
        raise PermissionDenied()


def _check_admin_permission(team, team_member):
    is_creator = _get_creator_permission(team, team_member)
    is_admin = team_member.is_admin

    if not (is_creator or is_admin):
        raise PermissionDenied()


def _get_user_team(user):
    team_user = TeamUser.objects.filter(
        user=user,
        is_approved=True
    ).select_related('team').first()

    if not team_user:
        raise ValidationError()

    return team_user.team, team_user


class TeamUserViewSet(ModelViewSet):
    queryset = TeamUser.objects.all().select_related('user', 'team')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        serializer_map = {
            'invite': TeamUserInviteSerializer,
            'accept': TeamUserAcceptRejectSerializer,
            'reject': TeamUserAcceptRejectSerializer,
            'make_admin': TeamUserAdminSerializer,
            'remove_admin': TeamUserAdminSerializer,
            'transfer_creator': TeamUserTransferSerializer,
            'remove_user': TeamUserRemoveSerializer,
        }
        return serializer_map.get(self.action, self.serializer_class)

    def get_queryset(self):
        user = self.request.user

        if user.is_admin:
            return self.queryset

        user_team_user = TeamUser.objects.filter(
            user=user,
            is_approved=True
        ).select_related('team').first()

        if not user_team_user:
            return self.queryset.filter(user=user)

        user_team = user_team_user.team

        return self.queryset.filter(
            Q(team=user_team) |
            Q(user=user)
        ).distinct()

    def get_user_team_or_error(self, user):
        team_user = TeamUser.objects.filter(
            user=user,
            is_approved=True
        ).select_related('team').first()

        if not team_user:
            raise ValidationError({'detail': 'Вы не состоите в команде.'})

        return team_user.team, team_user

    def get_target_or_error(self, pk, team):
        target = self.get_object()

        if target.team != team:
            raise ValidationError(
                {'detail': 'Пользователь не состоит в вашей команде.'}
            )

        return target

    def check_creator_permission(self, team, user):
        if team.creator != user:
            raise PermissionDenied({'detail': 'Вы не являетесь создателем команды.'})

    def check_admin_permission(self, team, team_member):
        is_creator = team.creator == team_member.user
        is_admin = team_member.is_admin

        if not (is_creator or is_admin):
            raise PermissionDenied({'detail': 'У вас нет прав на это действие.'})

    @action(detail=False, methods=['post'], url_path='invite')
    def invite(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        identifier = serializer.validated_data['identifier']

        team, membership = self.get_user_team_or_error(request.user)

        self.check_admin_permission(team, membership)

        invited_user = User.objects.filter(
            Q(username=identifier) | Q(email=identifier)
        ).first()

        if not invited_user:
            raise ValidationError(
                {'identifier': 'Пользователь с таким логином или email не найден.'}
            )

        if invited_user == request.user:
            raise ValidationError({'identifier': 'Нельзя пригласить самого себя.'})

        existing = TeamUser.objects.filter(team=team, user=invited_user).first()

        if existing:
            if existing.is_approved is None:
                raise ValidationError(
                    {'identifier': 'Пользователь уже приглашен в команду и ожидает подтверждения.'}
                )
            elif existing.is_approved:
                raise ValidationError(
                    {'identifier': 'Пользователь уже состоит в команде.'}
                )
            else:
                existing.is_approved = None
                existing.save()
                return Response({}, status=status.HTTP_201_CREATED)

        TeamUser.objects.create(
            team=team,
            user=invited_user,
            is_approved=None,
            is_admin=False
        )

        return Response(
            {},
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'], url_path='accept')
    def accept(self, request, pk=None):
        invitation = self.get_object()
        team = invitation.team
        serializer = TeamUserAcceptRejectSerializer()

        serializer.validate_invitation(invitation, request.user, team)
        serializer.accept(invitation)

        return Response({'detail': 'Приглашение принято'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        invitation = self.get_object()
        team = invitation.team
        serializer = TeamUserAcceptRejectSerializer()

        invitation = serializer.validate_invitation(invitation, request.user, team)
        serializer.reject(invitation)

        return Response(
            {'detail': 'Приглашение отклонено'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], url_path='make-admin')
    def make_admin(self, request, pk=None):
        target = self.get_object()
        team = target.team
        serializer = TeamUserAdminSerializer()

        serializer.validate_team_access(team, request.user)
        serializer.validate_target_user(target, team, request.user)
        result = serializer.make_admin(target, team, request.user)

        response_serializer = self.get_serializer(result)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='remove-admin')
    def remove_admin(self, request, pk=None):
        target = self.get_object()
        team = target.team
        serializer = TeamUserAdminSerializer()

        serializer.validate_team_access(team, request.user)
        serializer.validate_target_user(target, team, request.user)
        result = serializer.remove_admin(target, team, request.user)

        response_serializer = self.get_serializer(result)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='transfer-creator')
    def transfer_creator(self, request, pk=None):
        target = self.get_object()
        team = target.team
        serializer = TeamUserTransferSerializer()

        serializer.validate_transfer(team, request.user, target)
        result = serializer.transfer_creator(team, request.user, target)

        response_serializer = self.get_serializer(result)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'], url_path='remove')
    def remove_user(self, request, pk=None):
        target = self.get_object()
        team = target.team
        serializer = TeamUserRemoveSerializer()

        serializer.validate_removal(team, request.user, target)
        serializer.remove_user(target)

        return Response(
            {'detail': 'Пользователь успешно удален из команды'},
            status=status.HTTP_200_OK
        )
