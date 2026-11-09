"""WSGI-сервис: проверка сообщения, IP соединения и SMTP только на фиксированный адрес."""

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
from hashlib import sha256
from http import HTTPStatus
from ipaddress import ip_address
import json
import logging
import os
import smtplib
import ssl
import threading
import time
from typing import Any, Callable
from uuid import UUID

RECIPIENT = "r-r-y@yandex.ru"
SUBJECT = "Contests. Обратная связь из приложения"
BODY_LIMIT = 65_536


@dataclass(frozen=True)
class MailConfig:
    host: str
    username: str
    password: str = field(repr=False)
    sender: str
    port: int = 465

    @classmethod
    def from_env(cls) -> "MailConfig":
        password = os.environ.get("FEEDBACK_SMTP_PASSWORD", "")
        if not password:
            raise ValueError("Задайте FEEDBACK_SMTP_PASSWORD только в окружении сервера.")
        return cls(host=os.environ.get("FEEDBACK_SMTP_HOST", "smtp.yandex.ru"),
                   username=os.environ.get("FEEDBACK_SMTP_USERNAME", RECIPIENT), password=password,
                   sender=os.environ.get("FEEDBACK_SMTP_SENDER", RECIPIENT),
                   port=int(os.environ.get("FEEDBACK_SMTP_PORT", "465")))


def mail_message(data: dict[str, str], client_ip: str, config: MailConfig) -> EmailMessage:
    message = EmailMessage()
    message["From"] = config.sender
    message["To"] = RECIPIENT
    message["Subject"] = SUBJECT
    message["Date"] = format_datetime(datetime.now(timezone.utc))
    message["Message-ID"] = make_msgid()
    message.set_content(
        f"Обратная связь из приложения «Школьные конкурсы»\n\n"
        f"Имя: {data['name'] or 'не указано'}\n"
        f"Контакт для связи: {data['contact'] or 'не указан'}\n"
        f"Версия приложения: {data['version'] or 'не указана'}\n"
        f"IP отправителя, видимый сервису: {client_ip}\n"
        f"Идентификатор обращения: {data['request_id']}\n\n"
        f"Сообщение:\n{data['message']}\n"
    )
    return message


def smtp_send(message: EmailMessage, config: MailConfig) -> None:
    smtp = smtplib.SMTP_SSL(config.host, config.port, timeout=15, context=ssl.create_default_context())
    try:
        smtp.login(config.username, config.password)
        refused = smtp.send_message(message, from_addr=config.sender, to_addrs=[RECIPIENT])
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)
    finally:
        # Ошибка закрытия соединения после принятия письма не означает сбой отправки.
        try:
            smtp.quit()
        except OSError:
            smtp.close()


@dataclass
class Receipt:
    fingerprint: str
    created: float
    sent: bool = False


class FeedbackApp:
    def __init__(self, config: MailConfig, sender: Callable[[EmailMessage, MailConfig], None] = smtp_send) -> None:
        self.config, self.sender = config, sender
        self.lock = threading.Lock()
        self.receipts: dict[str, Receipt] = {}
        self.attempts: dict[str, deque[float]] = defaultdict(deque)
        self.global_attempts: deque[float] = deque()

    @staticmethod
    def response(start_response: Callable[..., Any], code: int, **body: Any) -> list[bytes]:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers = [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(payload))),
                   ("Cache-Control", "no-store"), ("X-Content-Type-Options", "nosniff")]
        if code == 429:
            headers.append(("Retry-After", "600"))
        start_response(f"{code} {HTTPStatus(code).phrase}", headers)
        return [payload]

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        if environ.get("PATH_INFO") != "/feedback":
            return self.response(start_response, 404, error="not_found")
        if environ.get("REQUEST_METHOD") != "POST":
            return self.response(start_response, 405, error="method_not_allowed")
        if environ.get("HTTP_ORIGIN"):
            return self.response(start_response, 403, error="desktop_client_required")
        if environ.get("CONTENT_TYPE", "").split(";", 1)[0].strip().lower() != "application/json":
            return self.response(start_response, 415, error="json_required")
        length = environ.get("CONTENT_LENGTH", "")
        if not isinstance(length, str) or not length.isascii() or not length.isdigit() or len(length) > 10:
            return self.response(start_response, 411, error="length_required")
        if not 0 < int(length) <= BODY_LIMIT:
            return self.response(start_response, 413, error="body_too_large")
        try:
            raw = json.loads(environ["wsgi.input"].read(int(length)).decode("utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("object required")
            data = {key: raw.get(key, "") for key in ("message", "name", "contact", "version", "request_id")}
            for key, maximum in (("message", 10_000), ("name", 120), ("contact", 240), ("version", 32), ("request_id", 36)):
                if not isinstance(data[key], str) or len(data[key]) > maximum:
                    raise ValueError("invalid field")
                data[key] = data[key].strip()
            if not data["message"] or str(UUID(data["request_id"])) != data["request_id"]:
                raise ValueError("message and UUID required")
            # REMOTE_ADDR устанавливает HTTP-сервер, клиентский JSON с IP не используется.
            client_ip = str(ip_address(environ.get("REMOTE_ADDR", "")))
        except (ValueError, UnicodeError, KeyError):
            return self.response(start_response, 400, error="invalid_request")
        now = time.monotonic()
        request_id = data["request_id"]
        fingerprint = sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        with self.lock:
            self.receipts = {key: receipt for key, receipt in self.receipts.items() if now - receipt.created < 86400}
            receipt = self.receipts.get(request_id)
            if receipt is not None:
                if receipt.fingerprint != fingerprint:
                    return self.response(start_response, 409, error="id_conflict")
                if receipt.sent:
                    return self.response(start_response, 200, sent=True, request_id=request_id)
                return self.response(start_response, 409, error="in_progress")
            self.attempts = defaultdict(deque, {ip: deque(t for t in times if now - t < 600)
                                              for ip, times in self.attempts.items() if times and now - times[-1] < 600})
            while self.global_attempts and now - self.global_attempts[0] >= 3600:
                self.global_attempts.popleft()
            if len(self.attempts[client_ip]) >= 10 or len(self.global_attempts) >= 120:
                return self.response(start_response, 429, error="rate_limit")
            if len(self.receipts) >= 10_000:
                return self.response(start_response, 503, error="busy")
            self.attempts[client_ip].append(now)
            self.global_attempts.append(now)
            self.receipts[request_id] = Receipt(fingerprint, now)
        try:
            self.sender(mail_message(data, client_ip, self.config), self.config)
        except (OSError, ValueError):
            logging.warning("Feedback delivery failed; request_id=%s", request_id)
            with self.lock:
                self.receipts.pop(request_id, None)
            return self.response(start_response, 502, error="delivery_failed")
        with self.lock:
            self.receipts[request_id].sent = True
        return self.response(start_response, 200, sent=True, request_id=request_id)


def main() -> None:
    from waitress import serve

    application = FeedbackApp(MailConfig.from_env())
    proxy = os.environ.get("FEEDBACK_TRUSTED_PROXY")
    options: dict[str, Any] = {}
    if proxy:
        if proxy == "*":
            raise ValueError("Укажите конкретный IP доверенного прокси вместо '*'.")
        options.update(trusted_proxy=proxy, trusted_proxy_count=1,
                       trusted_proxy_headers={"x-forwarded-for", "x-forwarded-proto"})
    serve(application, host=os.environ.get("FEEDBACK_BIND", "127.0.0.1"),
          port=int(os.environ.get("FEEDBACK_PORT", "8080")), threads=4,
          max_request_body_size=BODY_LIMIT, channel_timeout=60, **options)


if __name__ == "__main__":
    main()
