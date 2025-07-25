from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    # page_size_query_param = 'limit'
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100000

    def get_paginated_response(self, data):
        response = super(StandardResultsSetPagination, self).get_paginated_response(
            data
        )
        response.data["current_page"] = self.page.number
        response.data["total_pages"] = self.page.paginator.num_pages
        return response
