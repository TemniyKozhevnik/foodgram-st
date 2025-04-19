from django.urls import path, include
from .views import(
    ClientViewSet,
    ClientAvatarView,
    IngredientView,
    RecipeViewSet,
    SubscribeView,
    ClientMeView
)
from rest_framework import routers


router = routers.DefaultRouter()
router.register(r'recipes', RecipeViewSet)

urlpatterns = [
    path('users/', ClientViewSet.as_view(
        {
            'get': 'list',
            'post': 'create'
        }
    ),
        name='client-list'
    ),
    path('users/<int:pk>/', ClientViewSet.as_view(
        {
            'get': 'retrieve',
        }
    ),
        name='client-detail'
    ),
    path('users/me/avatar/', ClientAvatarView.as_view()),
    path('users/me/', ClientMeView.as_view()),
    path('ingredients/', IngredientView.as_view(), name='ingredient-list'),
    path(
        'ingredients/<int:pk>/',
        IngredientView.as_view(),
        name='ingredient-detail'
    ),
    path('', include(router.urls)),
    path('recipes/', RecipeViewSet.as_view(
        {
            'get': 'list',
            'post': 'create'
        }
    ),
        name='recipe-list'
    ),
    path('recipes/<int:pk>/', RecipeViewSet.as_view(
        {
            'get': 'retrieve',
            'patch': 'partial_update',
            'delete': 'destroy'
        }
    ),
        name='recipe-detail'
    ),
    path('recipes/<int:pk>/get-link/', RecipeViewSet.as_view(
        {
            'get': 'get_link'
        }
    ),
        name='recipe-get-link'
    ),
    path('users/subscriptions/', SubscribeView.as_view(),),
    path('users/<int:pk>/subscribe/', SubscribeView.as_view(),)
]