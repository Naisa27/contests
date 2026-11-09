"""SQLite, транзакции и прикладные операции. ORM не используется."""

from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
import json
import sqlite3
from typing import Any, Iterator

from sqlalchemy import (Column, Integer, String, Table, MetaData, ForeignKey,
                        ForeignKeyConstraint, UniqueConstraint, CheckConstraint,
                        create_engine, event, select, delete, insert, update)
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from .domain import calculate, integer

metadata = MetaData()
events = Table("events", metadata, Column("id", Integer, primary_key=True),
               Column("name", String, nullable=False), Column("start_date", String, nullable=False),
               Column("organizer", String, nullable=False))
teams = Table("teams", metadata, Column("id", Integer, primary_key=True),
              Column("event_id", ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
              Column("number", Integer, nullable=False), Column("name", String, nullable=False, default=""),
              UniqueConstraint("event_id", "number"), UniqueConstraint("id", "event_id"),
              CheckConstraint("typeof(number) = 'integer' AND number > 0"))
participants = Table("participants", metadata, Column("id", Integer, primary_key=True),
                     Column("event_id", ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
                     Column("name", String, nullable=False), Column("school", String, nullable=False),
                     Column("class_name", String, nullable=False), Column("category", Integer, nullable=False),
                     Column("team_id", Integer), UniqueConstraint("id", "event_id"),
                     ForeignKeyConstraint(["team_id", "event_id"], ["teams.id", "teams.event_id"]),
                     CheckConstraint("typeof(category) = 'integer' AND category BETWEEN 1 AND 11"))
contests = Table("contests", metadata, Column("id", Integer, primary_key=True),
                 Column("event_id", ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
                 Column("name", String, nullable=False), Column("position", Integer, nullable=False),
                 UniqueConstraint("id", "event_id"))
scores = Table("scores", metadata, Column("participant_id", Integer, primary_key=True),
               Column("contest_id", Integer, primary_key=True), Column("event_id", Integer, nullable=False),
               Column("points", Integer, nullable=False),
               ForeignKeyConstraint(["participant_id", "event_id"], ["participants.id", "participants.event_id"], ondelete="CASCADE"),
               ForeignKeyConstraint(["contest_id", "event_id"], ["contests.id", "contests.event_id"], ondelete="CASCADE"),
               CheckConstraint("typeof(points) = 'integer' AND points >= 0 AND points <= 2147483647"))
results = Table("results", metadata, Column("event_id", ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
                Column("payload", String, nullable=False))


class Store:
    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        existed = self.path.exists() and self.path.stat().st_size > 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{self.path.as_posix()}")
        event.listen(self.engine, "connect", self._connect)
        with self.engine.connect() as connection:
            version = connection.exec_driver_sql("PRAGMA user_version").scalar_one()
            if version not in (0, 1):
                raise ValueError("Эта база создана более новой версией приложения.")
        if existed and version == 0:
            self.backup(self.path.with_name(f"before-migration-{datetime.now():%Y%m%d-%H%M%S-%f}.sqlite3"))
        metadata.create_all(self.engine)
        with self.engine.begin() as connection:
            # Ограничения действуют даже при записи в обход прикладного слоя.
            connection.exec_driver_sql("""CREATE TRIGGER IF NOT EXISTS score_requires_team
                BEFORE INSERT ON scores WHEN (SELECT team_id FROM participants WHERE id=NEW.participant_id) IS NULL
                BEGIN SELECT RAISE(ABORT, 'participant requires team'); END""")
            connection.exec_driver_sql("""CREATE TRIGGER IF NOT EXISTS scored_participant_keeps_team
                BEFORE UPDATE OF team_id ON participants WHEN NEW.team_id IS NULL
                AND EXISTS(SELECT 1 FROM scores WHERE participant_id=NEW.id)
                BEGIN SELECT RAISE(ABORT, 'scored participant requires team'); END""")
            connection.exec_driver_sql("PRAGMA user_version=1")

    @staticmethod
    def _connect(connection: Any, record: Any) -> None:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")

    @contextmanager
    def transaction(self) -> Iterator[Connection]:
        try:
            with self.engine.begin() as connection:
                yield connection
        except IntegrityError as exc:
            raise ValueError("Данные не сохранены: проверьте уникальность номера команды и принадлежность данных мероприятию.") from exc

    @staticmethod
    def required(value: Any, label: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError(f"Заполните поле «{label}».")
        return text

    def list_events(self) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            return [dict(row) for row in connection.execute(select(events).order_by(events.c.start_date.desc(), events.c.id.desc())).mappings()]

    def save_event(self, name: str, start_date: str, organizer: str, event_id: int | None = None) -> int:
        values = dict(name=self.required(name, "Название"), start_date=date.fromisoformat(start_date).isoformat(),
                      organizer=self.required(organizer, "Организатор"))
        with self.transaction() as connection:
            if event_id is None:
                return connection.execute(insert(events).values(**values)).inserted_primary_key[0]
            connection.execute(update(events).where(events.c.id == event_id).values(**values))
            return event_id

    def snapshot(self, event_id: int, connection: Connection | None = None) -> dict[str, Any]:
        if connection is None:
            with self.engine.begin() as opened:
                return self.snapshot(event_id, opened)
        data: dict[str, Any] = {}
        data["event"] = dict(connection.execute(select(events).where(events.c.id == event_id)).mappings().one())
        for table in (teams, participants, contests):
            order = {"teams": teams.c.number, "participants": participants.c.name, "contests": contests.c.position}[table.name]
            data[table.name] = [dict(row) for row in connection.execute(select(table).where(table.c.event_id == event_id).order_by(order, table.c.id)).mappings()]
        data["scores"] = {(row.participant_id, row.contest_id): row.points for row in connection.execute(select(scores).where(scores.c.event_id == event_id))}
        return data

    def refresh(self, connection: Connection, event_id: int) -> None:
        from dataclasses import asdict
        payload = json.dumps([asdict(row) for row in calculate(self.snapshot(event_id, connection))], ensure_ascii=False)
        connection.execute(delete(results).where(results.c.event_id == event_id))
        connection.execute(insert(results).values(event_id=event_id, payload=payload))

    def save_team(self, event_id: int, number: Any, name: str = "", team_id: int | None = None) -> int:
        values = dict(event_id=event_id, number=integer(number, "Номер команды", 1), name=name.strip())
        with self.transaction() as connection:
            if team_id is None:
                team_id = connection.execute(insert(teams).values(**values)).inserted_primary_key[0]
            else:
                connection.execute(update(teams).where(teams.c.id == team_id, teams.c.event_id == event_id).values(**values))
            self.refresh(connection, event_id)
        return team_id

    def _participant_values(self, event_id: int, name: str, school: str, class_name: str,
                            category: Any, team_id: int | None) -> dict[str, Any]:
        return dict(event_id=event_id, name=self.required(name, "ФИО"), school=self.required(school, "Школа"),
                    class_name=self.required(class_name, "Класс"), category=integer(category, "Категория", 1, 11), team_id=team_id)

    def save_participant(self, event_id: int, name: str, school: str, class_name: str,
                         category: Any, team_id: int | None = None, participant_id: int | None = None) -> int:
        values = self._participant_values(event_id, name, school, class_name, category, team_id)
        with self.transaction() as connection:
            if participant_id is None:
                participant_id = connection.execute(insert(participants).values(**values)).inserted_primary_key[0]
            else:
                if team_id is None and connection.execute(select(scores).where(scores.c.participant_id == participant_id)).first():
                    raise ValueError("У участника есть оценки: выберите команду.")
                connection.execute(update(participants).where(participants.c.id == participant_id, participants.c.event_id == event_id).values(**values))
            self.refresh(connection, event_id)
        return participant_id

    def save_contest(self, event_id: int, name: str, contest_id: int | None = None) -> int:
        name = self.required(name, "Название конкурса")
        with self.transaction() as connection:
            if contest_id is None:
                ids = connection.execute(select(contests.c.position).where(contests.c.event_id == event_id)).scalars().all()
                contest_id = connection.execute(insert(contests).values(event_id=event_id, name=name, position=max(ids, default=-1) + 1)).inserted_primary_key[0]
            else:
                connection.execute(update(contests).where(contests.c.id == contest_id, contests.c.event_id == event_id).values(name=name))
            self.refresh(connection, event_id)
        return contest_id

    def remove_contest(self, event_id: int, contest_id: int) -> None:
        with self.transaction() as connection:
            connection.execute(delete(contests).where(contests.c.id == contest_id, contests.c.event_id == event_id))
            self.refresh(connection, event_id)

    def save_score(self, event_id: int, participant_id: int, contest_id: int, value: Any,
                   team_id: int | None = None) -> None:
        points = None if value is None or str(value).strip() == "" else integer(value, "Баллы")
        with self.transaction() as connection:
            participant = connection.execute(select(participants).where(participants.c.id == participant_id, participants.c.event_id == event_id)).mappings().one()
            if points is not None and participant["team_id"] is None:
                if team_id is None:
                    raise ValueError("Перед вводом баллов выберите команду участника.")
                connection.execute(update(participants).where(participants.c.id == participant_id).values(team_id=team_id))
            connection.execute(delete(scores).where(scores.c.participant_id == participant_id, scores.c.contest_id == contest_id))
            if points is not None:
                connection.execute(insert(scores).values(event_id=event_id, participant_id=participant_id, contest_id=contest_id, points=points))
            self.refresh(connection, event_id)

    def import_participants(self, event_id: int, rows: list[dict[str, Any]]) -> None:
        """Все участники и команды добавляются одной транзакцией."""
        from .excel import validate_rows
        with self.transaction() as connection:
            snapshot = self.snapshot(event_id, connection)
            rows, errors, _ = validate_rows(rows, snapshot)
            if errors:
                raise ValueError("Исправьте ошибки импорта: " + "; ".join(message for messages in errors.values() for message in messages))
            known = {t["number"]: t for t in snapshot["teams"]}
            for row in rows:
                team_id = None
                if row.get("team_number") is not None:
                    number = integer(row["team_number"], "Номер команды", 1)
                    name = row.get("team_name", "").strip()
                    if number in known:
                        team_id = known[number]["id"]
                        if name and known[number]["name"] != name:
                            connection.execute(update(teams).where(teams.c.id == team_id).values(name=name))
                            known[number]["name"] = name
                    else:
                        team_id = connection.execute(insert(teams).values(event_id=event_id, number=number, name=name)).inserted_primary_key[0]
                        known[number] = dict(id=team_id, name=name)
                connection.execute(insert(participants).values(**self._participant_values(
                    event_id, row["name"], row["school"], row["class_name"], row["category"], team_id)))
            self.refresh(connection, event_id)

    def backup(self, destination: Path) -> None:
        if destination.resolve() == self.path:
            raise ValueError("Выберите другой файл для резервной копии.")
        with sqlite3.connect(self.path) as source, sqlite3.connect(destination) as target:
            source.backup(target)

    def restore(self, source: Path) -> Path:
        if source.resolve() == self.path:
            raise ValueError("Выберите файл резервной копии.")
        with sqlite3.connect(f"file:{source.resolve().as_posix()}?mode=ro", uri=True) as candidate:
            if candidate.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Файл резервной копии повреждён.")
            if candidate.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise ValueError("Неподдерживаемая версия базы.")
            existing = {row[0] for row in candidate.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not set(metadata.tables).issubset(existing) or candidate.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("Файл не является корректной базой приложения.")
            for table in metadata.tables.values():
                columns = {row[1] for row in candidate.execute(f'PRAGMA table_info("{table.name}")')}
                if not set(table.columns.keys()).issubset(columns):
                    raise ValueError("В резервной копии отсутствуют обязательные поля.")
            backup_path = self.path.with_name(f"before-restore-{datetime.now():%Y%m%d-%H%M%S-%f}.sqlite3")
            self.backup(backup_path)
            self.engine.dispose()
            with sqlite3.connect(self.path) as target:
                candidate.backup(target)
        return backup_path

    def close(self) -> None:
        self.engine.dispose()
