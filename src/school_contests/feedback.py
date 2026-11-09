"""HTTPS-клиент обратной связи. Почтовые пароли в настольном приложении не хранятся."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

from . import __version__

MAX_MESSAGE = 10_000


class FeedbackError(Exception):
    """Понятная пользователю ошибка без внутренних адресов и ответов почтового сервера."""


@dataclass(frozen=True)
class Feedback:
    message: str
    name: str = ""
    contact: str = ""

    def validate(self) -> None:
        if not self.message.strip():
            raise FeedbackError("Опишите свой вопрос или проблему.")
        if len(self.message) > MAX_MESSAGE:
            raise FeedbackError(f"Сократите сообщение до {MAX_MESSAGE} символов.")
        if len(self.name) > 120 or len(self.contact) > 240:
            raise FeedbackError("Сократите имя до 120 символов, контакт — до 240.")


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, *args: object, **kwargs: object) -> None:
        # Контакты и текст не передаются на другой адрес по ответу сервера.
        return None


def feedback_endpoint() -> str:
    configured = os.environ.get("SCHOOL_CONTESTS_FEEDBACK_URL")
    if configured is not None:
        return configured.strip()
    path = Path(__file__).resolve().parent / "resources/feedback.json"
    return str(json.loads(path.read_text(encoding="utf-8"))["endpoint"]).strip()


def send_feedback(feedback: Feedback, request_id: str) -> None:
    feedback.validate()
    endpoint = feedback_endpoint()
    if not endpoint:
        raise FeedbackError("Отправка обратной связи пока недоступна. Связаться с разработчиком можно через «Справка → О программе».")
    parsed = urlsplit(endpoint)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise FeedbackError("Сервис обратной связи настроен некорректно. Сообщите об этом разработчику.")
    body = json.dumps(dict(message=feedback.message.strip(), name=feedback.name.strip(),
                           contact=feedback.contact.strip(), version=__version__, request_id=request_id),
                      ensure_ascii=False).encode("utf-8")
    request = Request(endpoint, data=body, headers={"Content-Type": "application/json; charset=utf-8",
                                                  "User-Agent": f"SchoolContests/{__version__}"}, method="POST")
    try:
        with build_opener(NoRedirects()).open(request, timeout=40) as response:
            if response.status != 200:
                raise FeedbackError("Сервис не подтвердил отправку. Попробуйте позже.")
            result = json.loads(response.read(4096).decode("utf-8"))
            if not isinstance(result, dict) or result.get("sent") is not True or result.get("request_id") != request_id:
                raise FeedbackError("Сервис не подтвердил отправку. Попробуйте позже.")
    except HTTPError as exc:
        if exc.code == 429:
            raise FeedbackError("Вы отправляете сообщения слишком часто. Повторите попытку через несколько минут.") from exc
        raise FeedbackError("Не удалось отправить сообщение. Текст сохранён в форме; попробуйте позже.") from exc
    except (URLError, OSError, ValueError) as exc:
        raise FeedbackError("Не получено подтверждение отправки. Проверьте подключение к интернету. Текст сохранён; можно повторить попытку.") from exc
