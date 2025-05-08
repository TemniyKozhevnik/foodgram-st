from rest_framework.pagination import PageNumberPagination
from .constans import PAGE_SIZE


class CustomPageNumberPagination(PageNumberPagination):
    page_size = PAGE_SIZE
    page_size_query_param = 'limit'
    max_page_size = PAGE_SIZE * 10
