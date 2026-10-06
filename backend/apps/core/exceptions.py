from rest_framework.views import exception_handler


def _text(value) -> str:
    if isinstance(value, (list, tuple)):
        return _text(value[0]) if value else "Request failed."
    return str(value)


def _messages(value) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [_text(item) for item in value]
    if isinstance(value, dict):
        return [_text(item) for item in value.values()]
    return [_text(value)]


def api_exception_handler(exc, context):
    """Return one error shape for every API failure."""
    response = exception_handler(exc, context)
    if response is None:
        return None
    payload = response.data
    if isinstance(payload, dict) and {"success", "message", "errors"} <= set(payload):
        return response
    errors = {}
    message = "Request failed."
    view_name = context.get("view").__class__.__name__ if context.get("view") else ""
    if isinstance(payload, dict):
        if list(payload.keys()) == ["detail"]:
            message = _text(payload["detail"])
        else:
            message = "Invalid prediction input." if "Prediction" in view_name else "Invalid request."
            errors = {key: _messages(value) for key, value in payload.items()}
    elif isinstance(payload, list):
        message = _text(payload[0]) if payload else message
        errors = {"non_field_errors": _messages(payload)}
    response.data = {"success": False, "message": message, "errors": errors}
    return response
