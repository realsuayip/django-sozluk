from functools import wraps

from django.http import HttpResponseBadRequest


def require_ajax(view):
    @wraps(view)
    def _wrapped_view(request, *args, **kwargs):
        if request.is_ajax():
            return view(request, *args, **kwargs)
        return HttpResponseBadRequest()

    return _wrapped_view


def force_post(func):
    # Compatible only with utils.views.JsonView
    def inner(self, *args, **kwargs):
        if self.method != "post":
            return HttpResponseBadRequest()
        return func(self, *args, **kwargs)

    return inner


def force_get(func):
    # Compatible only with utils.views.JsonView
    def inner(self, *args, **kwargs):
        if self.method != "get":
            return HttpResponseBadRequest()
        return func(self, *args, **kwargs)

    return inner
