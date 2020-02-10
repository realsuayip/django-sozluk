from functools import wraps

from django.core.cache import cache
from django.http import HttpResponseBadRequest


# General decoratos

def cache_retval(initial_func=None, *, timeout=None, prefix="default"):
    """
    Decorator to cache functions using django's low-level cache api. Arguments are
    not taken into consideration while caching, so values of func(a, b) and func(b, d)
    will be the same (the value of first called). Used in context-processors.

    :param initial_func: (decorator thingy, passed when used with parameters)
    :param timeout: Set the cache timeout, None to cache indefinitely.
    :param prefix: Cache keys are set using the name of the function. Set a unique prefix to
    avoid clashes between functions that have the same name.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = f"crtvl_{prefix}_{func.__name__}"
            cached_value = cache.get(key)

            if cached_value is not None:
                return cached_value

            calculated_value = func(*args, **kwargs)
            cache.set(key, calculated_value, timeout)
            return calculated_value

        return wrapper

    if initial_func:
        return decorator(initial_func)
    return decorator


# View (function/method) decorators


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
