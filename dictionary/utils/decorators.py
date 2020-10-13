from functools import wraps

from django.core.cache import cache


# General decorators


def cached_context(initial_func=None, *, timeout=None, vary_on_user=False, prefix="default"):
    """
    Decorator to cache functions using django's low-level cache api. Arguments
    are not taken into consideration while caching, so values of func(a, b) and
    func(b, d) will be the same (the value of first called).

    :param initial_func: (decorator thingy, passed when used with parameters)
    :param timeout: Set the cache timeout, None to cache indefinitely.
    :param prefix: Cache keys are set using the name of the function. Set a
    unique prefix to avoid clashes between functions/methods that with same name.
    :param vary_on_user: Set True to cache per user (anonymous users will have
    the same value). The wrapped function needs to have either "request" as
    argument or "user" as keyword argument.
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

            func_name = ""

            if hasattr(func, "__name__"):
                func_name = func.__name__
            elif prefix == "default":
                raise ValueError("Usage with non-wrapped decorators require an unique prefix.")

            key = f"{prefix}_context__{func_name}{user_prefix}"
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


def for_public_methods(decorator):
    """Decorate each 'public' method of this class with given decorator."""

    def decorate(cls):
        for attr in dir(cls):
            if not attr.startswith("_") and callable(getattr(cls, attr)):
                setattr(cls, attr, decorator(getattr(cls, attr)))
        return cls

    return decorate
