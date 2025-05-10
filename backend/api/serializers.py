import base64

from django.core.files.base import ContentFile
from django.core.validators import RegexValidator
from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from drf_extra_fields.fields import Base64ImageField

from recipes.models import (
    Client,
    Ingredient,
    RecipeIngredient,
    Recipe
)
from .constans import MIN_INGREDIENT_AMOUNT, MIN_RECIPE_COOKING_TIME


class ClientReadSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Client
        fields = (
            'id', 'email', 'username', 'first_name',
            'last_name', 'is_subscribed', 'avatar'
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')

        return (
            request
            and request.user.is_authenticated
            and obj.authors.filter(subscriber=request.user).exists()
        )


class ClientWriteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Client
        fields = (
            'id', 'email', 'username', 'first_name',
            'last_name', 'password'
        )
        username_regex_validator = RegexValidator(
            regex=r'^[\w.@+-]+\Z',
            message='''
                Username должно обладать соответствующим регулярным выражением.
            '''
        )
        username_unique_validator = UniqueValidator(
            queryset=Client.objects.all(),
            message='Данное имя пользователя уже занято'
        )
        extra_kwargs = {
            'password': {'write_only': True},
            'username': {'validators': [
                username_regex_validator,
                username_unique_validator
            ]},
        }

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = Client(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ClientAvatarSerializer(serializers.ModelSerializer):
    avatar = serializers.CharField(
        write_only=True,
        required=True,
        allow_null=False
    )

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


class RecipeIngredientReadSerializer(serializers.ModelSerializer):

    class Meta:
        model = RecipeIngredient
        fields = (
            'amount',
            'id',
            'recipe'
        )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        ingredient = instance.ingredient

        return {
            'id': ingredient.id,
            'name': ingredient.name,
            'measurement_unit': ingredient.measurement_unit,
            'amount': representation['amount'],
        }


class RecipeIngredientWriteSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient'
    )

    class Meta:
        model = RecipeIngredient
        fields = (
            'amount',
            'id',
        )
        read_only_fields = ('id',)

    def validate_amount(self, value):
        """Проверка наличия ингредиентов."""
        if value < MIN_INGREDIENT_AMOUNT:
            raise ValidationError('Поле amount должен быть положительным.')
        return value

    def to_representation(self, instance):
        return RecipeIngredientReadSerializer(
            instance,
            context=self.context
        ).data


class RecipeReadSerializer(serializers.ModelSerializer):
    author = ClientReadSerializer(read_only=True)
    ingredients = RecipeIngredientReadSerializer(
        many=True,
        source='recipe_ingredients'
    )
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'image', 'ingredients', 'is_favorited',
            'text', 'cooking_time', 'author', 'is_in_shopping_cart'
        )

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


class RecipeWriteSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientWriteSerializer(
        many=True,
        source='recipe_ingredients'
    )
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = (
            'name', 'image', 'ingredients',
            'text', 'cooking_time'
        )

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError(
                'Поле ''image'' обязательно для заполнения.'
            )
        return value

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
        if value < MIN_RECIPE_COOKING_TIME:
            raise ValidationError(
                f'Поле cooking_time={value} не может быть меньше '
                f'{MIN_RECIPE_COOKING_TIME}'
            )
        return value

    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients')
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

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data


class RecipeAdditionalSerializer(serializers.ModelSerializer):
    """
        Дополнительынй сериализатор
        (используется в списке покупок и избранном)
    """

    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscribeListSerializer(ClientReadSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(ClientReadSerializer.Meta):
        fields = tuple(
            f for f in ClientReadSerializer.Meta.fields
            if f != 'password'
        ) + (
            'recipes',
            'recipes_count'
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit', None)

        if recipes_limit is not None:
            try:
                recipes_limit = int(recipes_limit)
            except ValueError:
                recipes_limit = None

        recipes_queryset = obj.recipes.all()
        recipes_queryset = recipes_queryset[:recipes_limit]

        return RecipeAdditionalSerializer(recipes_queryset, many=True).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()
