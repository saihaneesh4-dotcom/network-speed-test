import sqlite3
import os
import json
import uuid
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "results.db")

VALIDATION_STATUSES = {"running", "completed", "partial", "failed"}
TEST_STATUSES = {"pending", "running", "completed", "failed"}


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def current_utc_timestamp():
    return datetime.now(timezone.utc).isoformat()


def create_table():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id TEXT,
            latency_ms REAL,
            jitter_ms REAL,
            packet_loss_percent REAL,
            download_mbps REAL,
            upload_mbps REAL,
            streams INTEGER,
            duration_sec INTEGER,
            timestamp TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS servers (
            server_id TEXT PRIMARY KEY,
            host TEXT NOT NULL,
            port INTEGER NOT NULL,
            location TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'online',
            last_heartbeat TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS iperf3_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id TEXT,
            server_id TEXT,
            host TEXT,
            port INTEGER,
            download_mbps REAL NOT NULL,
            upload_mbps REAL NOT NULL,
            duration_sec REAL,
            streams INTEGER,
            raw_output TEXT,
            metrics_json TEXT NOT NULL DEFAULT '{}',
            timestamp TEXT NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS validation_sessions (
            session_id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'running',
            mini_ookla_status TEXT NOT NULL DEFAULT 'pending',
            iperf3_status TEXT NOT NULL DEFAULT 'pending',
            mini_ookla_error TEXT,
            iperf3_error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)

        # Safely migrate existing databases without deleting records.
        for table_name in ("results", "iperf3_results"):
            cursor.execute(f"PRAGMA table_info({table_name})")
            existing_columns = {
                row["name"] for row in cursor.fetchall()
            }

            if "session_id" not in existing_columns:
                cursor.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN session_id TEXT"
                )

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_results_session_id
            ON results(session_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_iperf3_session_id
            ON iperf3_results(session_id)
        """)

        connection.commit()

    finally:
        connection.close()


def create_validation_session():
    connection = get_connection()

    try:
        cursor = connection.cursor()
        session_id = "VAL-" + uuid.uuid4().hex.upper()
        timestamp = current_utc_timestamp()

        cursor.execute("""
            INSERT INTO validation_sessions (
                session_id, status, mini_ookla_status,
                iperf3_status, created_at, updated_at
            )
            VALUES (?, 'running', 'pending', 'pending', ?, ?)
        """, (session_id, timestamp, timestamp))

        connection.commit()

        return get_validation_session(session_id)

    finally:
        connection.close()

def calculate_validation_status(mini_ookla_status, iperf3_status):
    statuses = (mini_ookla_status, iperf3_status)

    # The session is still active if either test is running.
    if "running" in statuses:
        return "running"

    # Both tests succeeded.
    if statuses == ("completed", "completed"):
        return "completed"

    # Neither test succeeded.
    if statuses == ("failed", "failed"):
        return "failed"

    # At least one succeeded, but the other has not succeeded.
    if "failed" in statuses and "completed" in statuses:
        return "partial"

    # A pending test means the session is not finalized yet.
    return "running"

def update_validation_session(
    session_id,
    mini_ookla_status=None,
    iperf3_status=None,
    mini_ookla_error=None,
    iperf3_error=None,
    status=None
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT *
            FROM validation_sessions
            WHERE session_id = ?
        """, (session_id,))

        current = cursor.fetchone()

        if current is None:
            return None

        current_mini_status = current["mini_ookla_status"]
        current_iperf_status = current["iperf3_status"]

        new_mini_status = (
            mini_ookla_status
            if mini_ookla_status is not None
            else current_mini_status
        )

        new_iperf_status = (
            iperf3_status
            if iperf3_status is not None
            else current_iperf_status
        )

        if new_mini_status not in TEST_STATUSES:
            raise ValueError(
                f"Invalid mini_ookla_status: {new_mini_status}"
            )

        if new_iperf_status not in TEST_STATUSES:
            raise ValueError(
                f"Invalid iperf3_status: {new_iperf_status}"
            )

        calculated_status = calculate_validation_status(
            new_mini_status,
            new_iperf_status
        )

        # An explicit status may not contradict the calculated status.
        if status is not None and status != calculated_status:
            raise ValueError(
                f"Session status must be '{calculated_status}' "
                "for the supplied test statuses"
            )

        cursor.execute("""
            UPDATE validation_sessions
            SET mini_ookla_status = ?,
                iperf3_status = ?,
                mini_ookla_error = ?,
                iperf3_error = ?,
                status = ?,
                updated_at = ?
            WHERE session_id = ?
        """, (
            new_mini_status,
            new_iperf_status,
            (
                mini_ookla_error
                if mini_ookla_error is not None
                else current["mini_ookla_error"]
            ),
            (
                iperf3_error
                if iperf3_error is not None
                else current["iperf3_error"]
            ),
            calculated_status,
            current_utc_timestamp(),
            session_id
        ))

        connection.commit()

    finally:
        connection.close()

    return get_validation_session(session_id)


def _save_result_and_complete_session(session_id, test_name, insert_sql, values):
    """Atomically save a session-linked result and complete its test."""
    connection = get_connection()

    status_column = (
        "mini_ookla_status" if test_name == "mini_ookla"
        else "iperf3_status"
    )
    error_column = (
        "mini_ookla_error" if test_name == "mini_ookla"
        else "iperf3_error"
    )

    try:
        # Acquire the write lock before checking status to avoid a race
        # with a concurrent failure update.
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.cursor()
        cursor.execute("""
            SELECT mini_ookla_status, iperf3_status
            FROM validation_sessions
            WHERE session_id = ?
        """, (session_id,))
        session = cursor.fetchone()

        if session is None:
            raise ValueError("Validation session not found")

        if session[status_column] == "failed":
            raise ValueError(
                f"Cannot save result: {test_name} test has already failed"
            )

        cursor.execute(insert_sql, values)
        result_id = cursor.lastrowid

        mini_status = (
            "completed" if test_name == "mini_ookla"
            else session["mini_ookla_status"]
        )
        iperf_status = (
            "completed" if test_name == "iperf3"
            else session["iperf3_status"]
        )
        overall_status = calculate_validation_status(
            mini_status, iperf_status
        )

        cursor.execute(f"""
            UPDATE validation_sessions
            SET {status_column} = 'completed',
                {error_column} = '',
                mini_ookla_status = ?,
                iperf3_status = ?,
                status = ?,
                updated_at = ?
            WHERE session_id = ?
        """, (
            mini_status,
            iperf_status,
            overall_status,
            current_utc_timestamp(),
            session_id
        ))

        connection.commit()
        return result_id
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def save_validation_result(
    server_id, latency_ms, jitter_ms, packet_loss_percent,
    download_mbps, upload_mbps, streams, duration_sec,
    timestamp, session_id
):
    return _save_result_and_complete_session(
        session_id,
        "mini_ookla",
        """
            INSERT INTO results (
                server_id, latency_ms, jitter_ms, packet_loss_percent,
                download_mbps, upload_mbps, streams, duration_sec,
                timestamp, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            server_id, latency_ms, jitter_ms, packet_loss_percent,
            download_mbps, upload_mbps, streams, duration_sec,
            timestamp, session_id
        )
    )


def save_validation_iperf3_result(
    test_id, server_id, host, port, download_mbps, upload_mbps,
    duration_sec, streams, raw_output, metrics, timestamp, session_id
):
    return _save_result_and_complete_session(
        session_id,
        "iperf3",
        """
            INSERT INTO iperf3_results (
                test_id, server_id, host, port, download_mbps,
                upload_mbps, duration_sec, streams, raw_output,
                metrics_json, timestamp, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            test_id, server_id, host, port, download_mbps,
            upload_mbps, duration_sec, streams, raw_output,
            json.dumps(metrics, ensure_ascii=False), timestamp, session_id
        )
    )


def get_validation_sessions():
    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT *
            FROM validation_sessions
            ORDER BY created_at DESC
        """)

        return [dict(row) for row in cursor.fetchall()]

    finally:
        connection.close()


def get_validation_session(session_id):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT *
            FROM validation_sessions
            WHERE session_id = ?
        """, (session_id,))

        row = cursor.fetchone()

        if row is None:
            return None

        session = dict(row)

        cursor.execute("""
            SELECT *
            FROM results
            WHERE session_id = ?
            ORDER BY id DESC
        """, (session_id,))

        session["mini_ookla_results"] = [
            dict(item) for item in cursor.fetchall()
        ]

        cursor.execute("""
            SELECT id, test_id, server_id, host, port,
                   download_mbps, upload_mbps, duration_sec,
                   streams, raw_output, metrics_json, timestamp,
                   session_id
            FROM iperf3_results
            WHERE session_id = ?
            ORDER BY id DESC
        """, (session_id,))

        iperf3_results = []

        for item in cursor.fetchall():
            result = dict(item)
            result["metrics"] = json.loads(result.pop("metrics_json"))
            iperf3_results.append(result)

        session["iperf3_results"] = iperf3_results

        return session

    finally:
        connection.close()


def save_result(
    server_id,
    latency_ms,
    jitter_ms,
    packet_loss_percent,
    download_mbps,
    upload_mbps,
    streams,
    duration_sec,
    timestamp,
    session_id=None
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO results (
                server_id, latency_ms, jitter_ms, packet_loss_percent,
                download_mbps, upload_mbps, streams, duration_sec,
                timestamp, session_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            server_id,
            latency_ms,
            jitter_ms,
            packet_loss_percent,
            download_mbps,
            upload_mbps,
            streams,
            duration_sec,
            timestamp,
            session_id
        ))

        connection.commit()
        return cursor.lastrowid

    finally:
        connection.close()


def save_iperf3_result(
    test_id,
    server_id,
    host,
    port,
    download_mbps,
    upload_mbps,
    duration_sec,
    streams,
    raw_output,
    metrics,
    timestamp,
    session_id=None
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO iperf3_results (
                test_id, server_id, host, port, download_mbps,
                upload_mbps, duration_sec, streams, raw_output,
                metrics_json, timestamp, session_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            test_id,
            server_id,
            host,
            port,
            download_mbps,
            upload_mbps,
            duration_sec,
            streams,
            raw_output,
            json.dumps(metrics, ensure_ascii=False),
            timestamp,
            session_id
        ))

        connection.commit()
        return cursor.lastrowid

    finally:
        connection.close()


def get_iperf3_results():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT id, test_id, server_id, host, port,
                   download_mbps, upload_mbps, duration_sec,
                   streams, raw_output, metrics_json, timestamp,
                   session_id
            FROM iperf3_results
            ORDER BY id DESC
        """)

        return cursor.fetchall()

    finally:
        connection.close()


def get_results():
    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM results ORDER BY id DESC")
        return cursor.fetchall()

    finally:
        connection.close()


def get_results_by_server(server_id):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT * FROM results WHERE server_id = ? ORDER BY id DESC",
            (server_id,)
        )

        return cursor.fetchall()

    finally:
        connection.close()


def get_latest_result():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT * FROM results
            ORDER BY id DESC
            LIMIT 1
        """)

        return cursor.fetchone()

    finally:
        connection.close()


def register_server(server_id, host, port, location):
    timestamp = current_utc_timestamp()
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT server_id FROM servers WHERE server_id = ?",
            (server_id,)
        )

        is_new = cursor.fetchone() is None

        cursor.execute("""
            INSERT INTO servers (
                server_id, host, port, location, status, last_heartbeat
            )
            VALUES (?, ?, ?, ?, 'online', ?)
            ON CONFLICT(server_id) DO UPDATE SET
                host = excluded.host,
                port = excluded.port,
                location = excluded.location,
                status = 'online',
                last_heartbeat = excluded.last_heartbeat
        """, (server_id, host, port, location, timestamp))

        connection.commit()
        return is_new

    finally:
        connection.close()


def record_heartbeat(server_id):
    timestamp = current_utc_timestamp()
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE servers
            SET last_heartbeat = ?, status = 'online'
            WHERE server_id = ?
        """, (timestamp, server_id))

        connection.commit()
        return cursor.rowcount > 0

    finally:
        connection.close()


def get_registered_servers(timeout_seconds):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT server_id, host, port, location, status, last_heartbeat
            FROM servers
            ORDER BY server_id
        """)

        rows = cursor.fetchall()
        now = datetime.now(timezone.utc)
        servers = []

        for row in rows:
            server_id = row["server_id"]
            host = row["host"]
            port = row["port"]
            location = row["location"]
            last_heartbeat = row["last_heartbeat"]

            status = "offline"

            if last_heartbeat:
                try:
                    heartbeat_time = datetime.fromisoformat(
                        last_heartbeat.replace("Z", "+00:00")
                    )

                    if heartbeat_time.tzinfo is None:
                        heartbeat_time = heartbeat_time.replace(
                            tzinfo=timezone.utc
                        )

                    age = (now - heartbeat_time).total_seconds()

                    if 0 <= age <= timeout_seconds:
                        status = "online"

                except ValueError:
                    status = "offline"

            cursor.execute("""
                UPDATE servers
                SET status = ?
                WHERE server_id = ?
            """, (status, server_id))

            servers.append({
                "server_id": server_id,
                "host": host,
                "port": port,
                "location": location,
                "status": status,
                "last_heartbeat": last_heartbeat
            })

        connection.commit()
        return servers

    finally:
        connection.close()


def deregister_server(server_id):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            "DELETE FROM servers WHERE server_id = ?",
            (server_id,)
        )

        connection.commit()
        return cursor.rowcount > 0

    finally:
        connection.close()


create_table()
