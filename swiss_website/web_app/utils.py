from sentry_sdk import capture_exception


def log_exception(e):
    return capture_exception(e)
