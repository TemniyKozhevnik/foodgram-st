# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Recipe,
    Client,
    Ingredient,
    RecipeIngredient,
    Favorite,
    ShoppingCart,
    Subscribe
)


class CustomClientAdmin(UserAdmin):
    list_display = (
        'email',
        'username',
        'first_name',
        'last_name',
        'is_staff'
    )
    search_fields = (
        'email',      # Поиск по электронной почте
        'username',   # Поиск по логину
    )
    list_filter = ('is_staff', 'is_superuser')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Персональная информация', {'fields': (
            'username',
            'first_name',
            'last_name',
            'avatar'
        )}),
        ('Права доступа', {'fields': (
            'is_active',
            'is_staff',
            'is_superuser',
            'groups',
            'user_permissions'
        )}),
        ('Даты', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'username',
                'first_name',
                'last_name',
                'password1',
                'password2',
                'avatar'
            ),
        }),
    )


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1


class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_author_name', 'favorites_count')
    search_fields = ('name', 'author__username')
    list_filter = ('author',)
    inlines = [RecipeIngredientInline]

    def get_author_name(self, obj):
        return obj.author.username

    get_author_name.short_description = 'Автор'

    def favorites_count(self, obj):
        return obj.favorite.count()
    favorites_count.short_description = 'Количество добавлений в избранное'


class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'amount', 'recipe')


class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('author', 'recipe')


class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('author', 'recipe')


class SubscribeAdmin(admin.ModelAdmin):
    list_display = ('author', 'subscriber')


# Регистрация модели в админке
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Client, CustomClientAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(ShoppingCart, ShoppingCartAdmin)
admin.site.register(Favorite, FavoriteAdmin)
admin.site.register(Subscribe, SubscribeAdmin)
