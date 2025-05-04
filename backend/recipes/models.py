from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator
from django.core.exceptions import ValidationError


MAX_CHAR_FIELD_LENGTH = 150


class Client(AbstractUser):
    username = models.CharField(
        max_length=MAX_CHAR_FIELD_LENGTH,
        blank=False,
        unique=True,
        verbose_name="Логин"
    )
    email = models.EmailField(
        max_length=MAX_CHAR_FIELD_LENGTH,
        blank=False,
        unique=True,
        verbose_name="Электронная почта"
    )
    last_name = models.CharField(
        max_length=MAX_CHAR_FIELD_LENGTH,
        blank=False,
        verbose_name="Фамилия пользователя"
    )
    first_name = models.CharField(
        max_length=MAX_CHAR_FIELD_LENGTH,
        blank=False,
        verbose_name="Имя пользователя"
    )
    avatar = models.ImageField(
        upload_to='foodgram/images/clients',
        null=True,
        blank=False,
        verbose_name="Аватар"
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = (
        'username',
        'last_name',
        'first_name',
        'avatar'
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.email


class Ingredient(models.Model):
    name = models.CharField(
        max_length=MAX_CHAR_FIELD_LENGTH,
        verbose_name="Название ингредиента"
    )
    measurement_unit = models.CharField(
        max_length=MAX_CHAR_FIELD_LENGTH,
        verbose_name="Единицы измерения"
    )

    class Meta:
        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"
        constraints = [
            models.UniqueConstraint(
                fields=["name", "measurement_unit"], name="unique_ingredient"
            )
        ]

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name="recipe_ingredients",
        verbose_name="Ингредиент"
    )
    amount = models.IntegerField(
        verbose_name="Количество ингредиента",
        validators=[MaxValueValidator(10000)]
    )
    recipe = models.ForeignKey(
        'recipes.Recipe',
        related_name='recipe_ingredients',
        on_delete=models.CASCADE,
        verbose_name="Рецепт"
    )

    class Meta:
        verbose_name = "Соответствие рецепт - ингредиент"


class Recipe(models.Model):
    author = models.ForeignKey(
        Client,
        related_name='recipes',
        on_delete=models.CASCADE,
        verbose_name="Автор рецепта"
    )
    name = models.CharField(
        blank=False,
        max_length=MAX_CHAR_FIELD_LENGTH,
        verbose_name="Название рецепта"
    )
    image = models.ImageField(
        upload_to='foodgram/images/recipes',
        verbose_name="Изображение рецепта"
    )
    cooking_time = models.IntegerField(
        blank=False,
        verbose_name="Время приготовления (в мин)",
        validators=[MaxValueValidator(600)]
    )
    text = models.TextField(
        blank=False,
        verbose_name="Описание рецепта"
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through=RecipeIngredient,
        blank=False,
        related_name="recipes",
        verbose_name="Ингредиенты"
    )

    class Meta:
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"

    def __str__(self):
        return self.name


class ShoppingCart(models.Model):
    author = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="shopping_cart",
        verbose_name="Пользователь"
    )
    recipe = models.ForeignKey(
        'recipes.Recipe',
        on_delete=models.CASCADE,
        related_name="shopping_cart",
        verbose_name="Рецепт, добавленный пользователем в список покупок"
    )

    class Meta:
        verbose_name = "Список покупок"
        verbose_name_plural = "Список покупок"
        constraints = [
            models.UniqueConstraint(
                fields=["author", "recipe"], name="unique_shopping_cart"
            )
        ]

    def __str__(self):
        return f"{self.author}: {self.recipe}"


class Favorite(models.Model):
    author = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="favorite",
        verbose_name="Пользователь"
    )
    recipe = models.ForeignKey(
        'recipes.Recipe',
        on_delete=models.CASCADE,
        related_name="favorite",
        verbose_name="Рецепт, добавленный пользователем в избранное"
    )

    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"
        constraints = [
            models.UniqueConstraint(
                fields=["author", "recipe"],
                name="unique_favorite"
            )
        ]

    def __str__(self):
        return f"{self.author}: {self.recipe}"


class Subscribe(models.Model):
    subscriber = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='subscribers',
        verbose_name="Подписчик"
    )
    author = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='authors',
        verbose_name="Тот, на кого подписываются"
    )

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        constraints = [
            models.UniqueConstraint(
                fields=["subscriber", "author"],
                name="unique_subscribe"
            ),
        ]

    def clean(self):
        super().clean()
        if self.subscriber == self.author:
            raise ValidationError("Подписка на самого себя не разрешена.")

    def __str__(self):
        return f"{self.subscriber} подписан на {self.author}"
