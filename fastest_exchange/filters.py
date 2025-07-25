from django_filters import rest_framework as df_filters
from rest_framework import filters

# from fastest_exchange.models import Transaction


class DefaultFilter(df_filters.DjangoFilterBackend):
    pass


class SearchFilter(filters.SearchFilter):
    pass


class OrderingFilter(filters.OrderingFilter):
    pass


class NumberInFilter(df_filters.BaseInFilter, df_filters.NumberFilter):
    pass

