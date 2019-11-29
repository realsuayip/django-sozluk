from functools import wraps
from django.http import HttpResponseBadRequest


def require_ajax(view):
    @wraps(view)
    def _wrapped_view(request, *args, **kwargs):
        if request.is_ajax():
            return view(request, *args, **kwargs)
        else:
            return HttpResponseBadRequest()

    return _wrapped_view


def ajax_post(func):
    # Compatible only with utils.views.AjaxView
    def inner(self, *args, **kwargs):
        if self.method != "post":
            return HttpResponseBadRequest()
        else:
            return func(self, *args, **kwargs)
    return inner


def ajax_get(func):
    # Compatible only with utils.views.AjaxView
    def inner(self, *args, **kwargs):
        if self.method != "get":
            return HttpResponseBadRequest()
        else:
            return func(self, *args, **kwargs)
    return inner
