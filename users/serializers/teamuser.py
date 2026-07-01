from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied
from rest_framework.serializers import ModelSerializer, CharField, EmailField, DateTimeField, BooleanField, \
    SerializerMethodField, Serializer
from ..models import TeamUser, User


class TeamUserSerializer(ModelSerializer):
    username = CharField(source='user.username')
    email = EmailField(source='user.email')
    name = CharField(source='user.name')
    surname = CharField(source='user.surname')
    lastname = CharField(source='user.lastname')
    date_joined = DateTimeField(source='user.date_joined')
    is_admin = BooleanField()
    is_approved = BooleanField()
    is_creator = SerializerMethodField()
    is_myself = SerializerMethodField()

    class Meta:
        model = TeamUser
        fields = [
            'username', 'email', 'name', 'surname', 'lastname', 'id',
            'date_joined', 'is_admin', 'is_creator', 'is_myself', 'is_approved'
        ]

    def get_is_creator(self, obj):
        return obj.team.creator_id == obj.user_id

    def get_is_myself(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user.id == obj.user_id
        return False


class TeamUserInvitesListSerializer(ModelSerializer):
    username = CharField(source='user.username')
    email = EmailField(source='user.email')
    name = CharField(source='user.name')
    surname = CharField(source='user.surname')
    lastname = CharField(source='user.lastname')
    team_name = CharField(source='team.name')
    created = CharField(source='team.created')
    is_approved = BooleanField()

    class Meta:
        model = TeamUser
        fields = [
            'username', 'email', 'name', 'surname', 'id', 'lastname',
            'team_name', 'created', 'is_approved'
        ]


class TeamUserInviteSerializer(Serializer):
    identifier = CharField(
        max_length=255,
        required=True,
        error_messages={
            'required': 'Необходимо указать логин или почту.',
            'blank': 'Необходимо указать логин или почту.'
        }
    )

    def validate_identifier(self, value):
        if not value or not value.strip():
            raise ValidationError("Необходимо указать логин или почту.")
        return value.strip()

    def validate_invite(self, team, requesting_user, identifier):
        invited_user = User.objects.filter(
            Q(username=identifier) | Q(email=identifier)
        ).first()

        if not invited_user:
            raise ValidationError(
                {'identifier': 'Пользователь с таким логином или email не найден.'}
            )

        if invited_user == requesting_user:
            raise ValidationError({'identifier': 'Нельзя пригласить самого себя.'})

        existing_membership = TeamUser.objects.filter(
            team=team,
            user=invited_user
        ).first()

        if existing_membership:
            if existing_membership.is_approved is None:
                raise ValidationError(
                    {'identifier': 'Пользователь уже приглашен в команду и ожидает подтверждения.'}
                )
            elif existing_membership.is_approved:
                raise ValidationError(
                    {'identifier': 'Пользователь уже состоит в команде.'}
                )

        return invited_user, existing_membership

    def check_admin_permission(self, team, requesting_user):
        if team.creator == requesting_user:
            return True

        try:
            membership = TeamUser.objects.get(
                team=team,
                user=requesting_user,
                is_approved=True
            )
            if membership.is_admin:
                return True
        except TeamUser.DoesNotExist:
            pass

        raise PermissionDenied(
            {'detail': 'Только создатель команды или администратор могут приглашать пользователей.'}
        )

    def create_invitation(self, team, invited_user):
        return TeamUser.objects.create(
            team=team,
            user=invited_user,
            is_approved=None,
            is_admin=False
        )

    def resend_invitation(self, existing_membership):
        existing_membership.is_approved = None
        existing_membership.save()
        return existing_membership

    def invite(self, team, requesting_user):
        identifier = self.validated_data['identifier']

        self.check_admin_permission(team, requesting_user)

        invited_user, existing_membership = self.validate_invite(
            team, requesting_user, identifier
        )

        if existing_membership and existing_membership.is_approved is False:
            invitation = self.resend_invitation(existing_membership)
            status_code = 200
        else:
            invitation = self.create_invitation(team, invited_user)
            status_code = 201

        return invitation, status_code

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class TeamUserAcceptRejectSerializer(ModelSerializer):
    class Meta:
        model = TeamUser
        fields = ['id']

    def check_admin_permission(self, team, requesting_user):
        if team.creator == requesting_user:
            return True

        try:
            membership = TeamUser.objects.get(
                team=team,
                user=requesting_user,
                is_approved=True
            )
            if membership.is_admin:
                return True
        except TeamUser.DoesNotExist:
            pass

        raise PermissionDenied(
            {'detail': 'Только создатель команды или администратор могут отзывать приглашения пользователей.'}
        )

    def validate_invitation(self, invitation, user, team):
        if not invitation:
            raise NotFound({'detail': 'Приглашение не найдено.'})

        if invitation.is_approved is not None:
            raise ValidationError({'detail': 'Приглашение уже обработано.'})

        if invitation.user == user or self.check_admin_permission(team, user):
            return invitation

        if invitation.user != user:
            raise PermissionDenied({'detail': 'Это приглашение предназначено другому пользователю.'})

        return invitation

    def accept(self, invitation):
        invitation.is_approved = True
        invitation.save()
        return invitation

    def reject(self, invitation):
        invitation.is_approved = False
        invitation.save()
        return invitation


class TeamUserAdminSerializer(ModelSerializer):
    class Meta:
        model = TeamUser
        fields = ['id']

    def validate_team_access(self, team, user):
        try:
            membership = TeamUser.objects.get(team=team, user=user, is_approved=True)
        except TeamUser.DoesNotExist:
            raise PermissionDenied({'detail': 'Вы не являетесь участником команды.'})

        if not (membership.is_admin or user == team.creator):
            raise PermissionDenied({'detail': 'Недостаточно прав для управления администраторами.'})

        return membership

    def validate_target_user(self, target, team, current_user):
        if target.user == team.creator:
            raise ValidationError({'detail': 'Создатель команды всегда является администратором.'})

        if not target.is_approved:
            raise ValidationError({'detail': 'Нельзя управлять правами неподтвержденного участника.'})

        return target

    def make_admin(self, target, team, current_user):
        target.is_admin = True
        target.save()
        return target

    def remove_admin(self, target, team, current_user):
        if not target.is_admin:
            raise ValidationError({'detail': 'Пользователь не является администратором.'})

        target.is_admin = False
        target.save()
        return target


class TeamUserTransferSerializer(ModelSerializer):
    class Meta:
        model = TeamUser
        fields = ['id']

    def validate_transfer(self, team, current_user, target):
        if team.creator != current_user:
            raise PermissionDenied({'detail': 'Только создатель команды может передать права.'})

        if target.user == current_user:
            raise ValidationError({'detail': 'Нельзя передать права создателя самому себе.'})

        if not target.is_approved:
            raise ValidationError({'detail': 'Нельзя передать права создателя неподтвержденному участнику.'})

        return True

    def transfer_creator(self, team, current_user, target):
        with transaction.atomic():
            old_creator = current_user
            new_creator = target.user

            # Обновляем права старого создателя
            old_creator_membership = TeamUser.objects.get(team=team, user=old_creator)
            old_creator_membership.is_admin = True
            old_creator_membership.save()

            team.creator = new_creator
            team.save()

            if not target.is_admin:
                target.is_admin = True
                target.save()

            target.refresh_from_db()
            return target


class TeamUserRemoveSerializer(ModelSerializer):
    class Meta:
        model = TeamUser
        fields = ['id']

    def validate_removal(self, team, current_user, target):
        if target.user == current_user:
            raise ValidationError({'detail': 'Нельзя удалить самого себя. Используйте выход из команды.'})

        if target.user == team.creator:
            raise ValidationError({'detail': 'Нельзя удалить создателя команды.'})

        try:
            current_membership = TeamUser.objects.get(team=team, user=current_user, is_approved=True)
        except TeamUser.DoesNotExist:
            raise PermissionDenied({'detail': 'Вы не являетесь участником команды.'})

        is_creator = (team.creator == current_user)
        is_admin = current_membership.is_admin
        is_target_admin = target.is_admin

        if is_target_admin and not is_creator:
            raise PermissionDenied({'detail': 'Только создатель команды может удалить администратора.'})

        if not (is_creator or is_admin):
            raise PermissionDenied({'detail': 'У вас нет прав на удаление пользователей из команды.'})

        return True

    def remove_user(self, target):
        target.delete()
        return target
