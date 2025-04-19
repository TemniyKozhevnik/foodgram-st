from rest_framework.response import Response
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from django.shortcuts import get_object_or_404
from recipe.models import (
    Client,
    Ingredient,
    Recipe,
    ShoppingCart,
    Favorite,
    Subscribe
)
from .serializers import (
    ClientSerializer,
    ClientAvatarSerializer,
    IngredientSerializer,
    RecipeSerializer,
    RecipeAdditionalSerializer,
    SubscribeListSerializer
)
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status, viewsets, filters
from rest_framework.permissions import AllowAny, IsAuthenticated
from .permissions import Owner, RecipePermission
from rest_framework.decorators import action
import os
from django.http import FileResponse
from .pagination import CustomPageNumberPagination
    

class ClientViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    pagination_class = CustomPageNumberPagination

    def get(self, request, *args, **kwargs):
        if 'pk' in kwargs:
            return self.retrieve(request, *args, **kwargs)
        else:
            return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)
    
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    def create(self, request):
        serializer = ClientSerializer(data=request.data, context={'request': request})
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
        serializer = ClientSerializer(user, context={'request': request})
        return Response(serializer.data)
    

class ClientMeView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    pagination_class = CustomPageNumberPagination

    def list(self, request, *args, **kwargs):
        user = request.user
        serializer = ClientSerializer(user, context={'request': request})
        return Response(serializer.data)


class ClientAvatarView(generics.UpdateAPIView, generics.DestroyAPIView):
    permission_classes = [Owner]
    queryset = Client.objects.all()
    serializer_class = ClientAvatarSerializer

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    def update(self, request, pk=None):
        user = request.user
        serializer = ClientAvatarSerializer(
            user,
            data=request.data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"avatar": user.avatar.url},
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
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


class IngredientView(
    ListModelMixin,
    RetrieveModelMixin,
    generics.GenericAPIView
):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    filterset_fields = ['name']

    def get(self, request, *args, **kwargs):
        if 'pk' in kwargs:
            return self.retrieve(request, **kwargs)
        else:
            return self.list(request, *args, **kwargs)

    def list(self, request):
        search_query = request.query_params.get('search', None)
        queryset = self.filter_queryset(self.get_queryset())
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)
        serializer = IngredientSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        queryset = Ingredient.objects.all()
        user = get_object_or_404(queryset, pk=pk)
        serializer = IngredientSerializer(user)
        return Response(serializer.data)


class RecipeViewSet(viewsets.ModelViewSet):
    permission_classes = [RecipePermission]
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    pagination_class = CustomPageNumberPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('author', 'ingredients')

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_link(self, request, pk=None):
        recipe = self.get_object()
        short_link = f"https://foodgram.example.org/s/{recipe.pk}"
        return Response({"short-link": short_link})
    
    def get_queryset(self):
        """
            Получаем рецепты, которые находятся
             в корзине текущего пользователя.
        """
        user = self.request.user
        if user.is_authenticated:

            is_in_shopping_cart = self.request.query_params.get(
                'is_in_shopping_cart',
                '0'
            ).lower()
            is_favorited = self.request.query_params.get(
                'is_favorited',
                '0'
            ).lower()

            if is_in_shopping_cart == '1':
                shopping_cart = ShoppingCart.objects.filter(author=user)
                recipe_ids = shopping_cart.values_list('recipe_id', flat=True)
                return Recipe.objects.filter(id__in=recipe_ids)

            if is_favorited == '1':
                favorite = Favorite.objects.filter(author=user)
                recipe_ids = favorite.values_list('recipe_id', flat=True)
                return Recipe.objects.filter(id__in=recipe_ids)
            
        return Recipe.objects.all()
    
    @action(
        detail=True,
        permission_classes=[IsAuthenticated],
        methods=["post", "delete"]
    )
    def shopping_cart(self, request, pk=None):
        """Добавление и удаление рецептов в список покупок."""

        author = request.user
        try:
            recipe = Recipe.objects.get(pk=pk)
        except Exception:
            return Response(
                {'error': 'Данного рецепта не существует.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if request.method == "POST":
            shoppingcart, created = ShoppingCart.objects.get_or_create(
                author=author,
                recipe=recipe
            )
            if not created:
                return Response(
                    {"error": f"Рецепт '{recipe}' уже находится в корзине."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = RecipeAdditionalSerializer(
                recipe,
                context={"request": request}
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
        methods=["get"]
    )
    def download_shopping_cart(self, request, pk=None):
        """Скачать список покупок."""
        shopping_cart_items = ShoppingCart.objects.filter(author=request.user)

        if not shopping_cart_items.exists():
            return Response({"message": "Корзина покупок пуста."}, status=404)
        
        file_path = os.path.join('api', 'shopping_cart.txt')

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("Список покупок:\n")
            for item in shopping_cart_items:
                f.write(f'''
                    Рецепт: {item.recipe.name},
                    Автор: {item.author.username}\n
                ''')

        response = FileResponse(
            open(file_path, 'rb'),
            as_attachment=True,
            filename='shopping_cart.txt'
        )
        return response
    
    @action(
        detail=True,
        permission_classes=[IsAuthenticated],
        methods=["post", "delete"]
    )
    def favorite(self, request, pk=None):
        """Добавление и удаление рецептов в избранное."""
        author = request.user
        try:
            recipe = Recipe.objects.get(pk=pk)
        except Exception:
            return Response(
                {'error': 'Данного рецепта не существует.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if request.method == "POST":
            favorite, created = Favorite.objects.get_or_create(
                author=author,
                recipe=recipe
            )
            if not created:
                return Response(
                    {"error": f"Рецепт '{recipe}' уже находится в избранном."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = RecipeAdditionalSerializer(
                recipe,
                context={"request": request}
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
   
    
class SubscribeView(generics.ListCreateAPIView, generics.DestroyAPIView):
    queryset = Client.objects.all()
    serializer_class = SubscribeListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):

        queryset = Subscribe.objects.filter(subscriber=self.request.user)
        queryset1 = []
        for query in queryset:
            queryset1.append(Client.objects.get(pk=query.author_id))
        return queryset1
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
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
    
    def create(self, request, pk, *args, **kwargs):
        subscriber = request.user
        
        try:
            author = Client.objects.get(pk=pk)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Пользователь не найден.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if subscriber == author:
            return Response(
                {'error': 'Нельзя подписаться на самого себя.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            Subscribe.objects.create(subscriber=subscriber, author=author)
        except Exception:
            return Response(
                {'error': '''
                    нельзя подписаться на пользователя,
                     на которого ты уже подписан
                 '''},
                status=status.HTTP_400_BAD_REQUEST
            )
                
        author.is_subscribed = True
        serializer = SubscribeListSerializer(
            author,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, pk=None):
        try:
            author = Client.objects.get(pk=pk)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Пользователь не найден.'},
                status=status.HTTP_404_NOT_FOUND
            )

        author.is_subscribed = False
        subscriber = request.user
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




