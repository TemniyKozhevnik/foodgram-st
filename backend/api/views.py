import os

from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets, filters
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.http import FileResponse
from dotenv import load_dotenv

from .pagination import CustomPageNumberPagination
from .permissions import Owner, RecipePermission
from recipes.models import (
    Client,
    Ingredient,
    Recipe,
    ShoppingCart,
    Favorite,
    Subscribe,
    RecipeIngredient
)
from .serializers import (
    ClientAvatarSerializer,
    IngredientSerializer,
    RecipeAdditionalSerializer,
    SubscribeListSerializer,
    ClientReadSerializer,
    ClientWriteSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer
)
from .filters import RecipeFilter

load_dotenv()


class ClientViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = Client.objects.all()
    serializer_class = ClientReadSerializer
    pagination_class = CustomPageNumberPagination
    http_method_names = ['get', 'post', 'delete', 'put']

    def create(self, request):
        serializer = ClientWriteSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            data = serializer.data
            data.pop('is_subscribed', None)
            data.pop('avatar', None)
            return Response(data, status=201)
        return Response(serializer.errors, status=400)

    def retrieve(self, request, pk=None):
        queryset = Client.objects.all()
        user = get_object_or_404(queryset, pk=pk)
        serializer = ClientReadSerializer(user, context={'request': request})
        return Response(serializer.data)

    @action(
        methods=['post'],
        detail=False,
        url_path='set_password',
        url_name='set_password'
    )
    def set_password(self, request):
        user = request.user
        old_password = request.data.get('current_password')
        new_password = request.data.get('new_password')

        if not user.check_password(old_password):
            return Response(
                {'error': 'Неверный текущий пароль'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()
        return Response(
            {'status': 'Пароль изменен'},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=False, methods=['get'], url_path='subscriptions')
    def subscriptions(self, request):
        queryset = Client.objects.filter(
            authors__subscriber=self.request.user
        ).distinct()

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = SubscribeListSerializer(
                page,
                many=True,
                context={'request': request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = SubscribeListSerializer(
            queryset,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)

    @action(
        methods=['post', 'delete'],
        detail=True,
        url_path='subscribe',
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, pk=None):

        author = get_object_or_404(Client, pk=pk)
        subscriber = request.user

        if subscriber == author:
            return Response(
                {'error': 'Нельзя выполнить действие с самим собой'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.method == 'POST':
            if Subscribe.objects.filter(
                subscriber=subscriber, author=author
            ).exists():
                return Response(
                    {'error': 'Подписка уже существует'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            Subscribe.objects.create(subscriber=subscriber, author=author)
            serializer = SubscribeListSerializer(
                author,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            try:
                get_object_or_404(
                    Subscribe,
                    author=author,
                    subscriber=subscriber
                ).delete()
            except Exception:
                return Response(
                    {'error': 'Нельзя удалить несуществующую подписку.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['get'],
        detail=False,
        url_path='me',
        permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        user = request.user
        serializer = ClientReadSerializer(user, context={'request': request})
        return Response(serializer.data)

    @action(
        methods=['put', 'delete'],
        detail=False,
        url_path='me/avatar',
        url_name='my-avatar',
        serializer_class=ClientAvatarSerializer,
        permission_classes=[Owner]
    )
    def avatar(self, request):
        """Обработка аватара текущего пользователя"""
        user = request.user

        if request.method == 'DELETE':
            try:
                user = request.user
                user.avatar.delete(save=False)
                user.avatar = None
                user.save()
                return Response(
                    {'message': 'Аватар успешко удален.'},
                    status=status.HTTP_204_NO_CONTENT
                )
            except Client.DoesNotExist:
                return Response(
                    {'error': 'Пользователь не найден.'},
                    status=status.HTTP_404_NOT_FOUND
                )

        serializer = self.get_serializer(
            user,
            data=request.data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {'avatar': user.avatar.url},
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    http_method_names = ['get']
    filterset_fields = ['name']


class RecipeViewSet(viewsets.ModelViewSet):
    permission_classes = [RecipePermission]
    queryset = Recipe.objects.all()
    serializer_class = RecipeReadSerializer
    pagination_class = CustomPageNumberPagination
    filter_backends = (DjangoFilterBackend,)
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']
    filterset_fields = ('author', 'ingredients')
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RecipeWriteSerializer
        return RecipeReadSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        """
            Получаем рецепты, которые находятся
             в корзине текущего пользователя.
        """
        return super().get_queryset()

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        short_link = f'({os.getenv("LINK_DOMEN")}{recipe.pk})'
        return Response({'short-link': short_link})

    @action(
        detail=True,
        permission_classes=[IsAuthenticated],
        methods=['post', 'delete']
    )
    def shopping_cart(self, request, pk=None):
        """Добавление и удаление рецептов в список покупок."""

        author = request.user
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':
            shoppingcart, created = ShoppingCart.objects.get_or_create(
                author=author,
                recipe=recipe
            )
            if not created:
                return Response(
                    {'error': f'Рецепт "{recipe}" уже находится в корзине.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = RecipeAdditionalSerializer(
                recipe,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        try:
            get_object_or_404(
                ShoppingCart,
                author=author,
                recipe=recipe
            ).delete()
        except Exception:
            return Response(
                {'error': '''
                    Нельзя удалить несуществующий в списке покупок товар.
                 '''},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        permission_classes=[IsAuthenticated],
        methods=['get']
    )
    def download_shopping_cart(self, request):
        """Скачать список покупок."""
        shopping_cart_items = request.user.shopping_cart.all()
        shopping_cart = {}
        for item_shopping_cart in shopping_cart_items:
            recipe = item_shopping_cart.recipe
            for item in RecipeIngredient.objects.filter(recipe=recipe):
                if item.ingredient in shopping_cart:
                    shopping_cart[item.ingredient] += item.amount
                else:
                    shopping_cart[item.ingredient] = item.amount

        if not shopping_cart_items.exists():
            return Response({'message': 'Корзина покупок пуста.'}, status=404)

        shopping_cart_list = [
            'Список покупок:'
        ]

        for key in shopping_cart:
            shopping_cart_list.append(
                f'{key}: {shopping_cart[key]} {key.measurement_unit}'
            )

        return FileResponse(
            ("\n".join(shopping_cart_list)),
            as_attachment=True,
            filename="shopping_list.txt",
            content_type="text/plain; charset=utf-8",
        )

    @action(
        detail=True,
        permission_classes=[IsAuthenticated],
        methods=['post', 'delete']
    )
    def favorite(self, request, pk=None):
        """Добавление и удаление рецептов в избранное."""
        author = request.user
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':
            favorite, created = Favorite.objects.get_or_create(
                author=author,
                recipe=recipe
            )
            if not created:
                return Response(
                    {'error': f'Рецепт "{recipe}" уже находится в избранном.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = RecipeAdditionalSerializer(
                recipe,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        try:
            get_object_or_404(Favorite, author=author, recipe=recipe).delete()
        except Exception:
            return Response(
                {'error': 'Нельзя удалить несуществующий в избранном товар.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
