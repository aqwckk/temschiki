"""Вход сотрудника УК на стенде Ujin: возвращает его ust для публикации и чтения устройств."""
import json
import urllib.parse
import urllib.request

from app.ujin.credentials import Employee

TIMEOUT = 10


class UjinAuthError(Exception):
    pass


def login(base_url: str, employee: Employee) -> str:
    body = urllib.parse.urlencode(
        {"login": employee.login, "password": employee.password, "app": employee.app}
    ).encode("utf-8")
    request = urllib.request.Request(base_url.rstrip("/") + "/api/auth/authenticate/", data=body, method="POST")
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        answer = json.loads(response.read().decode("utf-8"))
    data = answer.get("data") or {}
    # на стенде токен лежит в data.user.token
    token = (data.get("user") or {}).get("token") or data.get("token")
    if answer.get("error") or not token:
        raise UjinAuthError(f"auth/authenticate: error={answer.get('error')} {answer.get('message') or ''}")
    return token
