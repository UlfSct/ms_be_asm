from django.db.models import Value, When, Case, IntegerField
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.serializers import ModelSerializer, SerializerMethodField, Serializer
from ..models import Team, TeamUser
from ..serializers import TeamUserSerializer


class TeamInfoSerializer(ModelSerializer):
    is_creator = SerializerMethodField()
    is_admin = SerializerMethodField()
    users = SerializerMethodField()

    class Meta:
        model = Team
        fields = ['name', 'created', 'is_creator', 'is_admin', 'users']

    def get_is_creator(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.creator_id == request.user.id
        return False

    def get_is_admin(self, obj):
        request = self.context.get('request')
        if request and request.user:
            try:
                team_user = TeamUser.objects.get(team=obj, user=request.user)
                return team_user.is_admin
            except TeamUser.DoesNotExist:
                return False
        return False

    def get_users(self, obj):
        members = TeamUser.objects.filter(team=obj).select_related('user', 'team').annotate(
            sort_order=Case(
                When(user_id=obj.creator_id, then=Value(1)),
                When(is_admin=True, then=Value(2)),
                default=Value(3),
                output_field=IntegerField()
            )
        ).order_by('sort_order')
        serializer = TeamUserSerializer(members, many=True, context=self.context)
        return serializer.data


class TeamCreateSerializer(ModelSerializer):
    class Meta:
        model = Team
        fields = ['name']

    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user:
            raise ValidationError("Пользователь не аутентифицирован")

        if TeamUser.objects.filter(user=request.user).exists():
            raise ValidationError("Пользователь уже состоит в команде")

        team = Team.objects.create(
            name=validated_data['name'],
            creator=request.user
        )

        TeamUser.objects.create(
            team=team,
            user=request.user,
            is_admin=True,
            is_approved=True
        )

        return team

class TeamUpdateSerializer(ModelSerializer):
    class Meta:
        model = Team
        fields = ['name']

    def validate_edit_permission(self, team, user):
        if team.creator == user:
            return True

        try:
            membership = TeamUser.objects.get(team=team, user=user, is_approved=True)
            if membership.is_admin:
                return True
        except TeamUser.DoesNotExist:
            pass

        raise PermissionDenied("Только создатель или администратор команды может изменять её название")

    def update(self, instance, validated_data):
        request = self.context.get('request')
        if request and request.user:
            self.validate_edit_permission(instance, request.user)

        return super().update(instance, validated_data)


class TeamLeaveSerializer(Serializer):
    def validate_leave(self, team, user):
        if team.creator == user:
            raise ValidationError(
                'Создатель команды не может выйти. Передайте права создателя или удалите команду.'
            )

        try:
            membership = TeamUser.objects.get(team=team, user=user, is_approved=True)
            return membership
        except TeamUser.DoesNotExist:
            raise ValidationError('Вы не состоите в команде.')

    def leave(self, membership):
        membership.delete()
        return membership

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class TeamDeleteSerializer(Serializer):
    def validate_delete(self, team, user):
        if team.creator != user:
            raise PermissionDenied('Только создатель команды может удалить её.')

        return True

    def delete(self, team):
        team.delete()
        return team

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass
