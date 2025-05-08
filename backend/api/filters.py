from django_filters import rest_framework as rf_filters

from recipes.models import (
    Recipe,
)


class RecipeFilter(rf_filters.FilterSet):
    is_in_shopping_cart = rf_filters.BooleanFilter(
        method='filter_shopping_cart'
    )
    is_favorited = rf_filters.BooleanFilter(method='filter_favorited')

    class Meta:
        model = Recipe
        fields = ['author', 'ingredients']

    def filter_shopping_cart(self, queryset, name, value):
        if value and self.request.user.is_authenticated:
            return queryset.filter(shopping_cart__author=self.request.user)
        return queryset

    def filter_favorited(self, queryset, name, value):
        if value and self.request.user.is_authenticated:
            return queryset.filter(favorite__author=self.request.user)
        return queryset
