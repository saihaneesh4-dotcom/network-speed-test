
import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "results.db")


def get_connection():
    return sqlite3.connect(DB_PATH)


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

        connection.commit()
    finally:
        connection.close()


def save_result(server_id, latency_ms, jitter_ms, packet_loss_percent,
                download_mbps, upload_mbps, streams, duration_sec, timestamp):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
        INSERT INTO results (
            server_id, latency_ms, jitter_ms, packet_loss_percent,
            download_mbps, upload_mbps, streams, duration_sec, timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            server_id, latency_ms, jitter_ms, packet_loss_percent,
            download_mbps, upload_mbps, streams, duration_sec, timestamp
        ))
        connection.commit()
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


def current_utc_timestamp():
    return datetime.now(timezone.utc).isoformat()


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
            server_id, host, port, location, _, last_heartbeat = row

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
