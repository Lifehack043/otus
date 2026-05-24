"""Сервис авторизации."""

import datetime
import hashlib

from domain.requests.base import MethodRequestModel

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"


def check_auth(request: MethodRequestModel) -> bool:
    """Проверяет аутентификацию по токену.

    Для админа токен вычисляется как SHA512(текущая_дата_YYYYMMDDHH + ADMIN_SALT).
    Для обычных пользователей токен вычисляется как SHA512(account + login + SALT).
    """
    account = request.account or ""
    login = request.login or ""
    token = request.token or ""

    if request.is_admin:
        digest = hashlib.sha512(
            (datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode("utf-8")
        ).hexdigest()
    else:
        digest = hashlib.sha512(
            (account + login + SALT).encode("utf-8")
        ).hexdigest()
    return digest == token
