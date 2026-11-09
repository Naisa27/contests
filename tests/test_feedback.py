from io import BytesIO
import json
from unittest.mock import MagicMock
from urllib.error import URLError
from uuid import uuid4

import pytest
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QMessageBox

from school_contests.feedback import Feedback, FeedbackError, send_feedback
from school_contests.ui.feedback import FeedbackDialog
from server.app import FeedbackApp, MailConfig, SUBJECT, RECIPIENT


def call_service(app, payload: dict, ip: str = "198.51.100.27", **extra) -> tuple[int, dict]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    environ = dict(PATH_INFO="/feedback", REQUEST_METHOD="POST", CONTENT_TYPE="application/json",
                   CONTENT_LENGTH=str(len(data)), REMOTE_ADDR=ip, **{"wsgi.input": BytesIO(data)})
    environ.update(extra)
    status = []
    response = app(environ, lambda code, headers: status.append(int(code.split()[0])))
    return status[0], json.loads(b"".join(response))


def test_server_letter_subject_optional_fields_real_ip_and_deduplication() -> None:
    sent = []
    config = MailConfig("smtp.example.org", "user", "secret", "sender@example.org")
    app = FeedbackApp(config, lambda message, settings: sent.append(message))
    payload = dict(message="Вопрос о конкурсе", request_id=str(uuid4()), version="0.1.1", ip="spoofed")
    code, result = call_service(app, payload, HTTP_X_FORWARDED_FOR="1.2.3.4")
    assert code == 200 and result["sent"] is True
    assert len(sent) == 1
    assert str(sent[0]["Subject"]) == SUBJECT
    assert sent[0]["To"] == RECIPIENT
    body = sent[0].get_content()
    assert "не указано" in body and "Вопрос о конкурсе" in body
    assert "198.51.100.27" in body
    assert "spoofed" not in body and "1.2.3.4" not in body
    assert call_service(app, payload)[0] == 200
    assert len(sent) == 1
    assert call_service(app, dict(payload, message="Другой текст"))[0] == 409


def test_server_does_not_confirm_failed_email_and_allows_retry() -> None:
    sender = MagicMock(side_effect=OSError("SMTP unavailable"))
    app = FeedbackApp(MailConfig("host", "user", "secret", "sender@example.org"), sender)
    payload = dict(message="Пожелание", name="Регина", contact="@contact", request_id=str(uuid4()))
    status, result = call_service(app, payload)
    assert status == 502 and result.get("sent") is not True
    sender.side_effect = None
    assert call_service(app, payload)[0] == 200
    assert sender.call_count == 2


def test_server_validation_and_rate_limit() -> None:
    sender = MagicMock()
    app = FeedbackApp(MailConfig("host", "user", "secret", "sender@example.org"), sender)
    assert call_service(app, dict(message=" ", request_id=str(uuid4())))[0] == 400
    assert call_service(app, dict(message="x" * 10_001, request_id=str(uuid4())))[0] == 400
    assert sender.call_count == 0
    for _ in range(10):
        assert call_service(app, dict(message="Вопрос", request_id=str(uuid4())))[0] == 200
    assert call_service(app, dict(message="Ещё вопрос", request_id=str(uuid4())))[0] == 429
    assert sender.call_count == 10


def test_client_requires_configured_https_and_confirmation(monkeypatch) -> None:
    monkeypatch.setenv("SCHOOL_CONTESTS_FEEDBACK_URL", "")
    with pytest.raises(FeedbackError, match="пока недоступна"):
        send_feedback(Feedback("Вопрос"), str(uuid4()))
    monkeypatch.setenv("SCHOOL_CONTESTS_FEEDBACK_URL", "http://example.org/feedback")
    with pytest.raises(FeedbackError, match="настроен некорректно"):
        send_feedback(Feedback("Вопрос"), str(uuid4()))
    monkeypatch.setenv("SCHOOL_CONTESTS_FEEDBACK_URL", "https://example.org/feedback")
    opener = MagicMock()
    monkeypatch.setattr("school_contests.feedback.build_opener", lambda *args: opener)
    opener.open.side_effect = URLError("offline")
    with pytest.raises(FeedbackError, match="Не получено подтверждение"):
        send_feedback(Feedback("Вопрос"), str(uuid4()))
    opener.open.side_effect = None
    response = opener.open.return_value.__enter__.return_value
    response.status = 200
    response.read.return_value = b'{"sent": true, "request_id": "wrong"}'
    request_id = str(uuid4())
    with pytest.raises(FeedbackError, match="не подтвердил"):
        send_feedback(Feedback("Вопрос"), request_id)
    response.read.return_value = json.dumps(dict(sent=True, request_id=request_id)).encode()
    send_feedback(Feedback("Вопрос"), request_id)


def test_form_requires_only_message_and_keeps_draft_on_error(qtbot, monkeypatch) -> None:
    calls = []

    def fail(feedback: Feedback, request_id: str) -> None:
        calls.append((feedback, request_id))
        raise FeedbackError("Нет соединения")

    monkeypatch.setattr("school_contests.ui.feedback.send_feedback", fail)
    dialog = FeedbackDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.mouseClick(dialog.send_button, Qt.MouseButton.LeftButton)
    assert "Опишите" in dialog.status.text() and not calls
    dialog.message.setPlainText("Вопрос без имени и контакта")
    qtbot.mouseClick(dialog.send_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: dialog.worker is None)
    assert calls[0][0].name == "" and calls[0][0].contact == ""
    assert dialog.message.toPlainText() == "Вопрос без имени и контакта"
    assert dialog.isVisible() and dialog.status.text() == "Нет соединения"
    qtbot.mouseClick(dialog.send_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: dialog.worker is None)
    assert calls[0][1] == calls[1][1]
    dialog.close()


def test_form_success_only_after_worker_finishes(qtbot, monkeypatch) -> None:
    import threading

    gate = threading.Event()
    notices = []
    monkeypatch.setattr("school_contests.ui.feedback.send_feedback", lambda *args: gate.wait(2))
    monkeypatch.setattr(QMessageBox, "information", lambda *args: notices.append(args[2]))
    dialog = FeedbackDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.message.setPlainText("Пожелание")
    qtbot.mouseClick(dialog.send_button, Qt.MouseButton.LeftButton)
    assert not dialog.send_button.isEnabled()
    assert not notices
    dialog.reject()
    assert dialog.isVisible()
    QTimer.singleShot(50, gate.set)
    qtbot.waitUntil(lambda: dialog.result() == dialog.DialogCode.Accepted)
    assert notices == ["Сообщение успешно отправлено разработчику."]
