import base64

from django.core.files.base import ContentFile
from django.core.validators import RegexValidator
from django.db import IntegrityError
from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from drf_extra_fields.fields import Base64ImageField

from recipes.models import (
    Client,
    Ingredient,
    RecipeIngredient,
    Recipe
)


ZERO_VALUE = 0


class ClientSerializer(serializers.ModelSerializer):

    avatar = Base64ImageField(required=False, allow_null=True)
    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Client
        fields = (
            'id', 'email', 'username', 'first_name',
            'last_name', 'is_subscribed', 'avatar', 'password'
        )
        read_only_fields = ('id', 'is_subscribed', 'avatar')
        username_validator = RegexValidator(
            regex=r'^[\w.@+-]+\Z',
            message='''
                Username должно обладать соответствующим регулярным выражением.
            '''
        )
        extra_kwargs = {
            'password': {'write_only': True},
            'username': {'validators': [username_validator]},
            'is_subscribed': {'required': False, 'read_only': True},
        }

    def get_is_subscribed(self, obj):
        request = self.context.get('request')

        return (
            request
            and request.user.is_authenticated
            and obj.authors.filter(subscriber=request.user).exists()
        )

    def create(self, validated_data):
        try:
            password = validated_data.pop('password')
            user = Client(
                email=validated_data['email'],
                username=validated_data['username'],
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name'],
                avatar=validated_data.get('avatar', None)
            )
            user.set_password(password)
            user.save()
            return user
        except IntegrityError:
            raise serializers.ValidationError({
                'username': 'Данное имя уже используется'
            })


class ClientAvatarSerializer(serializers.ModelSerializer):
    avatar = serializers.CharField(write_only=True)

    class Meta:
        model = Client
        fields = ['avatar']

    def validate_avatar(self, value):
        if not value:
            raise serializers.ValidationError(
                'Поле ''avatar'' обязательно для заполнения.'
            )
        try:
            format, img_str = value.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(
                base64.b64decode(img_str),
                name=f'user_avatar.{ext}'
            )
        except Exception:
            raise serializers.ValidationError(
                'Некорректный формат изображения'
            )
        return data

    def update(self, instance, validated_data):
        if 'avatar' in validated_data:
            instance.avatar = validated_data['avatar']
        else:
            raise serializers.ValidationError(
                'Поле ''avatar'' обязательно для обновления.'
            )

        instance.save()
        return instance


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = (
            'id',
            'name',
            'measurement_unit'
        )


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient'
    )

    class Meta:
        model = RecipeIngredient
        fields = (
            'amount',
            'id',
            'recipe'
        )
        read_only_fields = ('recipe', 'id')

    def validate_amount(self, value):
        """Проверка наличия ингредиентов."""
        if value <= ZERO_VALUE:
            raise ValidationError('Поле amount должен быть положительным.')
        return value

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        ingredient = instance.ingredient

        return {
            'id': ingredient.id,
            'name': ingredient.name,
            'measurement_unit': ingredient.measurement_unit,
            'amount': representation['amount'],
        }


class RecipeSerializer(serializers.ModelSerializer):
    author = ClientSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        many=True,
        source='recipe_ingredients'
    )
    image = Base64ImageField(required=True)
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'image', 'ingredients', 'is_favorited',
            'text', 'cooking_time', 'author', 'is_in_shopping_cart'
        )
        read_only_fields = (
            'id',
            'author',
        )
        extra_kwargs = {
            'is_favorited': {'required': False, 'read_only': True},
            'is_in_shopping_cart': {'required': False, 'read_only': True},
        }

    def validate_ingredients(self, value):
        """Общая валидация для поля ingredients."""
        if not value:
            raise ValidationError('Поле ingredients не может быть пустым.')

        ingredient_ids = set()
        for ingredient_data in value:
            current_id = ingredient_data['ingredient'].id
            if current_id in ingredient_ids:
                raise ValidationError(
                    {'ingredients': ['Ингредиенты не могут повторяться']}
                )
            ingredient_ids.add(current_id)

        return value

    def validate_cooking_time(self, value):
        if value < 1:
            raise ValidationError(
                f'Поле cooking_time={value} не может быть меньше 1'
            )
        return value

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')

        if request.user.is_authenticated:
            return request.user.shopping_cart.filter(recipe=obj).exists()
        else:
            return False

    def get_is_favorited(self, obj):
        request = self.context.get('request')

        if request.user.is_authenticated:
            return request.user.favorite.filter(recipe=obj).exists()
        else:
            return False

    def to_representation(self, instance):
        """Кастомизируем вывод данных."""
        representation = super().to_representation(instance)
        request = self.context.get('request')

        if instance.image:
            representation['image'] = request.build_absolute_uri(
                instance.image.url
            )
        else:
            representation['image'] = ''

        return representation

    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients')

        if not validated_data.get('image'):
            raise ValidationError(
                {'image': ['Изображение обязательно для рецепта']}
            )

        recipe = Recipe.objects.create(**validated_data)
        recipe.save()
        self.add_ingredients(recipe=recipe, data=ingredients_data)
        return recipe

    @staticmethod
    def add_ingredients(recipe, data):
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient_data['ingredient'],
                amount=ingredient_data['amount']
            ) for ingredient_data in data
        ])

    def update(self, instance, validated_data):

        ingredients_data = validated_data.pop('recipe_ingredients', None)
        if not validated_data.get('image'):
            raise ValidationError(
                {'image': ['Изображение обязательно для рецепта']}
            )

        instance = super().update(instance, validated_data)
        instance.image = validated_data.get('image', instance.image)
        instance.save()

        if ingredients_data is not None:
            instance.ingredients.clear()

            self.add_ingredients(recipe=instance, data=ingredients_data)

        else:

            raise ValidationError(
                'Поле ingredients обязательно для обновления рецепта.'
            )

        return instance


class RecipeAdditionalSerializer(serializers.ModelSerializer):
    """
        Дополнительынй сериализатор
        (используется в списке покупок и избранном)
    """

    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscribeListSerializer(ClientSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(ClientSerializer.Meta):
        fields = tuple(
            f for f in ClientSerializer.Meta.fields
            if f != 'password'
        ) + (
            'recipes',
            'recipes_count'
        )

        extra_kwargs = {
            **ClientSerializer.Meta.extra_kwargs,
        }
        extra_kwargs.pop('password', None)

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit', None)

        if recipes_limit is not None:
            try:
                recipes_limit = int(recipes_limit)
            except ValueError:
                recipes_limit = None

        recipes_queryset = Recipe.objects.filter(author_id=obj.id)
        recipes_queryset = recipes_queryset[:recipes_limit]

        return RecipeAdditionalSerializer(recipes_queryset, many=True).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()
