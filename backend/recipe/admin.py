# admin.py
from django.contrib import admin
from .models import Recipe, Client, Ingredient, RecipeIngredient, Favorite
from django.contrib.auth.admin import UserAdmin
from .forms import (
    EmailAuthenticationForm
)


class CustomUserAdmin(UserAdmin):
    # Укажите поля, которые хотите отображать в админке
    list_display = ('email', 'username', 'first_name', 'last_name')
    
    # Настройте поиск по полям email и username
    search_fields = ('email', 'username')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form = EmailAuthenticationForm  # Указываем свою форму
        return form

    authentication_form = EmailAuthenticationForm


admin.site.register(Client, CustomUserAdmin)


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')  # Поля для отображения в списке
    search_fields = ('name',)  # Поле для поиска по названию ингредиента

# Регистрация модели в админке
admin.site.register(Ingredient, IngredientAdmin)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1  # Количество пустых форм для добавления


class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_author_name', 'favorites_count')
    search_fields = ('name', 'author__username')  # Предполагаем, что у модели Client есть поле username
    list_filter = ('author',)

    def get_author_name(self, obj):
        return obj.author.username  # Измените на нужное поле, если оно отличается

    get_author_name.short_description = 'Автор'

    def favorites_count(self, obj):
        favorite = Favorite.objects.filter(recipe=obj)
        return favorite.count()  # Предполагаем, что у вас есть связь с избранными
    favorites_count.short_description = 'Количество добавлений в избранное'

# Регистрация модели в админке
admin.site.register(Recipe, RecipeAdmin)