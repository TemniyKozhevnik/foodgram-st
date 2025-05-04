from django.urls import path, include
from rest_framework import routers

from .views import (
    ClientViewSet,
    IngredientViewSet,
    RecipeViewSet
)

router = routers.DefaultRouter()
router.register(r'recipes', RecipeViewSet)
router.register(r'ingredients', IngredientViewSet)
router.register(r'users', ClientViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
