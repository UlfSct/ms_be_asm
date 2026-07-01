from ..models import User
from rest_framework.serializers import ModelSerializer, CharField, ValidationError, Serializer
from django.contrib.auth import authenticate


class RegistrationSerializer(ModelSerializer):
    password = CharField(write_only=True, min_length=6)
    password_confirm = CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = (
            'username', 'email', 'password', 'password_confirm',
            'name', 'surname', 'lastname'
        )
        extra_kwargs = {
            'is_admin': {'read_only': True},
        }

    def validate(self, data):
        errors = {}

        if data['password'] != data['password_confirm']:
            errors['password_confirm'] = ['Пароли не совпадают.']

        if User.objects.filter(username=data['username']).exists():
            errors['username'] = ['Пользователь с таким именем уже существует.']

        if User.objects.filter(email=data['email']).exists():
            errors['email'] = ['Пользователь с таким email уже существует.']

        if errors:
            raise ValidationError(errors)

        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            name=validated_data.get('name', ''),
            surname=validated_data.get('surname', ''),
            lastname=validated_data.get('lastname', ''),
        )
        return user


class LoginSerializer(Serializer):
    username = CharField()
    password = CharField(write_only=True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')
        errors = {}

        if not username:
            errors['username'] = ['Это поле обязательно.']

        if not password:
            errors['password'] = ['Это поле обязательно.']

        if errors:
            raise ValidationError(errors)

        user = authenticate(username=username, password=password)
        if user:
            if not user.is_active:
                raise ValidationError({
                    'username': ['Учетная запись неактивна.']
                })
            data['user'] = user
            return data

        raise ValidationError({
            'username': ['Неверные учетные данные.']
        })

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class ProfileSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = [
            'username', 'name', 'surname', 'lastname', 'email', 'date_joined'
        ]


class ProfileUpdateSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = [
           'name', 'surname', 'lastname'
        ]


class AdminUserRetrieveSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email',
            'name', 'surname', 'lastname', 'is_admin', 'is_active'
        )


class AdminUserUpdateSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ('is_admin', 'is_active')

    def validate(self, attrs):
        if self.context.get('user_id') == self.instance.id:
            raise ValidationError({'detail': 'Нельзя редактировать статусы самого себя.'})
        return attrs
