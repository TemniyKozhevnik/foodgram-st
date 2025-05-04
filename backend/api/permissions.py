from rest_framework import permissions


class Owner(permissions.BasePermission):

    def has_permission(self, request, view):

        if request.method not in permissions.SAFE_METHODS:
            return request.user.is_authenticated

        return True

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user


class ReadOnly(permissions.BasePermission):

    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS


class RecipePermission(permissions.BasePermission):
    """
    Пермишен, который предоставляет доступ к действиям,
    связанным с рецептами.
    """
    def has_permission(self, request, view):

        if request.method in permissions.SAFE_METHODS:
            return True

        if request.method == 'POST':
            return request.user.is_authenticated

        return True

    def has_object_permission(self, request, view, obj):

        if request.method in ['PATCH', 'DELETE']:
            return obj.author == request.user

        return True
