from functools import wraps

from django.core.exceptions import PermissionDenied


def login_required(func):
    """Utility decorator to check if the user logged in (mutations & resolvers)"""

    @wraps(func)
    def decorator(_, info, *args, **kwargs):
        if not info.context.user.is_authenticated:
            raise PermissionDenied("giriş yaparsan bu özellikten yararlanabilirsin aslında")
        return func(_, info, *args, **kwargs)

    return decorator
