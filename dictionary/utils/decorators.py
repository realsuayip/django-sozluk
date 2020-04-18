from functools import wraps

from django.core.cache import cache


# General decoratos


def cached_context(initial_func=None, *, timeout=None, vary_on_user=False, prefix="default"):
    """
    Decorator to cache functions using django's low-level cache api. Arguments are not taken into consideration while
    caching, so values of func(a, b) and func(b, d) will be the same (the value of first called). This is used to cache
    context processors, but not limited to.

    :param initial_func: (decorator thingy, passed when used with parameters)
    :param timeout: Set the cache timeout, None to cache indefinitely.
    :param prefix: Cache keys are set using the name of the function. Set a unique prefix to
    avoid clashes between functions that have the same name.
    :param vary_on_user: Set True to cache per user. (Anonymous users will have the same value)
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_prefix = ""

            if vary_on_user:
                request = kwargs.get("request")

                if request is not None:
                    user = request.user
                else:
                    user = kwargs.get("user")

                user_prefix = "_anonymous" if not user.is_authenticated else f"_usr{user.pk}"

            key = f"{prefix}_context__{func.__name__}{user_prefix}"
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
