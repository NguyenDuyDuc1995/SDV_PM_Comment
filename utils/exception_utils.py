import traceback
import warnings

__all__ = [
    'DeveloperWarning',
    'warn_developers',
    'try_catch_exception',
]


class DeveloperWarning(FutureWarning):
    pass


def warn_developers(message='', warning_type=DeveloperWarning):
    def inner(func):
        def wrap(*args, **kwargs):
            if len(message):
                warnings.warn(message, warning_type)
            return func(*args, **kwargs)

        return wrap

    return inner


def try_catch_exception(raise_exception=False):
    def inner(func=None):
        def wrap(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                traceback.print_exc()
                if raise_exception:
                    raise e

        return wrap

    return inner
