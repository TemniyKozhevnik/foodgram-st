from rest_framework.pagination import PageNumberPagination

PAGE_SIZE = 10


class CustomPageNumberPagination(PageNumberPagination):
    page_size = PAGE_SIZE
    page_size_query_param = 'limit'
    max_page_size = PAGE_SIZE * 10
