from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db.models import Q


class Client(AbstractUser):
    #is_subscribed = models.BooleanField(blank=False, default=False)
    username = models.CharField(max_length=150, blank=False, unique=True)
    email = models.EmailField(max_length=254, blank=False, unique=True)
    last_name = models.CharField(max_length=150, blank=False)
    first_name = models.CharField(max_length=150, blank=False)
    avatar = models.ImageField(
        upload_to='foodgram/images/clients',
        null=True,
        blank=False
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = (
        'username',
        'last_name',
        'first_name',
        #'is_subscribed',
        'avatar'
    )

    def __str__(self):
        return self.email
    

class Ingredient(models.Model):
    name = models.CharField(max_length=150)
    measurement_unit = models.CharField(max_length=150)

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    ingredient = models.ForeignKey(
        Ingredient, #related_name='recipe_ingredients',
        on_delete=models.CASCADE
    )
    amount = models.IntegerField()
    recipe = models.ForeignKey(
        'recipe.Recipe', related_name='recipe_ingredients',
        on_delete=models.CASCADE
    )


class Recipe(models.Model):
    author = models.ForeignKey(
        Client, related_name='authors',
        on_delete=models.CASCADE
    )
    name = models.CharField(blank=False, max_length=150)
    image = models.ImageField(
        upload_to='foodgram/images/recipes',
        null=True,
        blank=True
    )
    cooking_time = models.IntegerField(blank=False)
    text = models.TextField(blank=False)
    ingredients = models.ManyToManyField(
        Ingredient,
        through=RecipeIngredient,
        #related_name='recipes'
    )

    REQUIRED_FIELDS = (
        'ingredients',
        'image',
        'name',
        'text',
        'cooking_time'
    )

    def __str__(self):
        return self.name
    

class ShoppingCart(models.Model):
    author = models.ForeignKey(
        Client,
        on_delete=models.CASCADE
    )
    recipe = models.ForeignKey(
        'recipe.Recipe',
        on_delete=models.CASCADE
    )

    class Meta:
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
        on_delete=models.CASCADE
    )
    recipe = models.ForeignKey(
        'recipe.Recipe',
        on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["author", "recipe"], name="unique_favorite"
            )
        ]

    def __str__(self):
        return f"{self.author}: {self.recipe}"
    

class Subscribe(models.Model):
    subscriber = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='subscriber'
    )
    author = models.ForeignKey(
        Client,
        on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["subscriber", "author"], name="unique_subscribe"
            ),
        ]