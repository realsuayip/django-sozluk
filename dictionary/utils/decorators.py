from functools import wraps

from django.core.cache import cache
from django.http import HttpResponseBadRequest


# General decoratos


def cached_context(initial_func=None, *, timeout=None, vary_on_user=False, prefix="default"):
    """
    Decorator to cache functions using django's low-level cache api. Arguments are not taken into consideration while
    caching, so values of func(a, b) and func(b, d) will be the same (the value of first called). The decorated function
    should have request as it's first argument. This is used to cache context processors, but not limited to.

    :param initial_func: (decorator thingy, passed when used with parameters)
    :param timeout: Set the cache timeout, None to cache indefinitely.
    :param prefix: Cache keys are set using the name of the function. Set a unique prefix to
    avoid clashes between functions that have the same name.
    :param vary_on_user: Set True to cache per user. (Anonymous users will have the same value)
    """

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user_prefix = ""

            if vary_on_user:
                user_prefix = "_anonymous" if not request.user.is_authenticated else f"_usr{request.user.pk}"

            key = f"{prefix}_context__{func.__name__}{user_prefix}"
            cached_value = cache.get(key)

            if cached_value is not None:
                return cached_value

            calculated_value = func(request, *args, **kwargs)
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
