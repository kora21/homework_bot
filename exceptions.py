class StatusCodeError(Exception):
    """Ошибка кода запроса."""

    pass


class ResponseError(Exception):
    """Ошибка ответа."""

    pass


class TokenError(Exception):
    """Ошибка токена."""

    pass


class APIResponseStatusCodeException:
    """Api не отвечает."""

    pass


class ApiStatusError:
    """Неожидаемый ответ от Api."""

    pass


class ApiAnswerError:
    """Неожидаемый ответ от Api."""

    pass
