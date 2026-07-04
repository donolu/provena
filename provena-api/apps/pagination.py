from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 200


class PaginatedListMixin:
    """
    Adds a paginate() helper to raw APIView subclasses.

    Usage:
        class MyListView(PaginatedListMixin, APIView):
            def get(self, request):
                qs = MyModel.objects.all()
                return self.paginate(qs, MySerializer, request)
    """

    pagination_class = StandardPagination

    def paginate(self, queryset, serializer_class, request, **serializer_kwargs):
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)  # type: ignore[arg-type]
        if page is not None:
            serializer = serializer_class(page, many=True, **serializer_kwargs)
            return paginator.get_paginated_response(serializer.data)
        serializer = serializer_class(queryset, many=True, **serializer_kwargs)
        return Response(serializer.data)
