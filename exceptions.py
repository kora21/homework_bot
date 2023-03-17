class StatusCodeError(Exception):
    """Ошибка кода запроса."""

    pass


class ResponseError(Exception):
    """Ошибка ответа."""

    pass


class TokenError(Exception):
    """Ошибка токена."""

    pass
