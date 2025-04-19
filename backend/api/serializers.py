from rest_framework import serializers
import base64
from django.core.files.base import ContentFile
from recipe.models import (
    Client,
    Ingredient,
    RecipeIngredient,
    Recipe,
    ShoppingCart,
    Subscribe,
    Favorite
)
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.db import IntegrityError
from rest_framework.exceptions import ValidationError


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)
    

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
            regex='^[\w.@+-]+\Z',
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

        if request.user.is_authenticated:
            return Subscribe.objects.filter(
                subscriber=request.user,
                author=obj
            ).exists()
        else:
            return False
    
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
                "username": "Данное имя уже используется"
            })
    

class ClientAvatarSerializer(serializers.ModelSerializer):
    avatar = serializers.CharField(write_only=True)

    class Meta:
        model = Client
        fields = ['avatar']

    def validate_avatar(self, value):
        if not value:
            raise serializers.ValidationError(
                "Поле 'avatar' обязательно для заполнения."
            )
        try:
            format, img_str = value.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(
                base64.b64decode(img_str),
                name=f"user_avatar.{ext}"
            )
        except Exception:
            raise serializers.ValidationError(
                "Некорректный формат изображения"
            )
        return data

    def update(self, instance, validated_data):
        if 'avatar' in validated_data:
            instance.avatar = validated_data["avatar"]
        else:
            raise serializers.ValidationError(
                "Поле 'avatar' обязательно для обновления."
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
        if value <= 0:
            raise ValidationError('Поле amount должен быть положительным.')
        return value
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        ingredient_id = representation.pop('id')

        ingredient = Ingredient.objects.get(id=ingredient_id)
        
        return {
            'id': ingredient.id,
            'name': ingredient.name,
            'measurement_unit': ingredient.measurement_unit,
            'amount': instance.amount,
        }
    

class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)
    

class RecipeSerializer(serializers.ModelSerializer):
    author = ClientSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        many=True,
        source='recipe_ingredients'
    )
    image = Base64ImageField(required=True, allow_null=True)
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
            #'is_favorited',
            'author',
            #'is_in_shopping_cart'
        )
        extra_kwargs = {
            'is_favorited': {'required': False, 'read_only': True},
            'is_in_shopping_cart': {'required': False, 'read_only': True},
        }

    def validate_ingredients(self, value):
        """Проверка наличия ингредиентов."""
        if not value or len(value) == 0:
            raise ValidationError('Поле ingredients не может быть пустым.')
        return value
    
    def validate_cooking_time(self, value):
        if value < 1:
            raise ValidationError('Поле cooking_time не может быть меньше 1')
        return value
    
    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')

        if request.user.is_authenticated:
            return ShoppingCart.objects.filter(
                author=request.user,
                recipe=obj
            ).exists()
        else:
            return False
        
    def get_is_favorited(self, obj):
        request = self.context.get('request')
        
        if request.user.is_authenticated:
            return Favorite.objects.filter(
                author=request.user,
                recipe=obj
            ).exists()
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
            representation['image'] = ""

        return representation

    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients')

        ingredients_set = set()
        for ingredient_data in ingredients_data:
            if ingredient_data['ingredient'].id in ingredients_set:
                raise ValidationError('Ингредиенты не могут повторяться')
            ingredients_set.add(ingredient_data['ingredient'].id)
            
        recipe = Recipe(
            author = validated_data['author'],
            name = validated_data['name'],
            image = validated_data.get('image', None),
            cooking_time = validated_data['cooking_time'],
            text = validated_data['text'],
        )
        recipe.save()
        for ingredient_data in ingredients_data:
            ingredient = ingredient_data.get('ingredient')
            amount = ingredient_data.get('amount')
            if ingredient:
                ingredient = Ingredient.objects.get(id=ingredient.id)
                
                RecipeIngredient.objects.create(
                    recipe=recipe,
                    ingredient=ingredient,
                    amount=amount
                )
            else:
                pass
        return recipe
    
    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients', None)

        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get(
            'cooking_time',
            instance.cooking_time
        )
        instance.image = validated_data.get('image', instance.image)
        instance.save()

        if ingredients_data is not None:
            instance.ingredients.clear()

            ingredients_set = set()
            for ingredient_data in ingredients_data:

                if ingredient_data['ingredient'].id in ingredients_set:
                    raise ValidationError('Ингредиенты не могут повторяться')
                ingredients_set.add(ingredient_data['ingredient'].id)

            for ingredient_data in ingredients_data:

                ingredient = ingredient_data.get('ingredient')
                amount = ingredient_data.get('amount')
                if ingredient:
                    ingredient_instance = Ingredient.objects.get(
                        id=ingredient.id
                    )

                    RecipeIngredient.objects.create(
                        recipe=instance,
                        ingredient=ingredient_instance,
                        amount=amount
                    )
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
        fields = ("id", "name", "image", "cooking_time")


class SubscribeListSerializer(serializers.ModelSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Client
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "avatar",
            "recipes",
            'recipes_count'
        )
        
    def get_is_subscribed(self, obj):
        request = self.context.get('request')

        if request.user.is_authenticated:
            return Subscribe.objects.filter(
                subscriber=request.user,
                author=obj
            ).exists()
        else:
            return False
    
    def get_recipes(self, obj):

        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit', None)

        if recipes_limit is not None:
            try:
                recipes_limit = int(recipes_limit)
            except ValueError:
                recipes_limit = None

        recipes_queryset = Recipe.objects.filter(author_id=obj.id)
        if recipes_limit is not None:
            recipes_queryset = recipes_queryset[:recipes_limit]

        return RecipeAdditionalSerializer(recipes_queryset, many=True).data

    def get_recipes_count(self, obj):
        return len(self.get_recipes(obj))
