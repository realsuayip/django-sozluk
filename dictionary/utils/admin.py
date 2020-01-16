from django.shortcuts import reverse, redirect


# Admin site specific utilities


class IntermediateActionHandler:
    def __init__(self, queryset, url_name):
        self.queryset = queryset
        self.url_name = url_name

    def get_source_list(self):
        return '-'.join([str(value["id"]) for value in self.queryset.values("id")])

    @property
    def redirect_url(self):
        return redirect(reverse(self.url_name) + f"?source_list={self.get_source_list()}")
