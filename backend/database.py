import sqlite3

def create_table():
    connection = sqlite3.connect("results.db")
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

    connection.commit()
    connection.close()


def save_result(server_id, latency_ms, jitter_ms, packet_loss_percent,
                download_mbps, upload_mbps, streams, duration_sec, timestamp):

    connection = sqlite3.connect("results.db")
    cursor = connection.cursor()

    cursor.execute("""
    INSERT INTO results (
        server_id,
        latency_ms,
        jitter_ms,
        packet_loss_percent,
        download_mbps,
        upload_mbps,
        streams,
        duration_sec,
        timestamp
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        server_id,
        latency_ms,
        jitter_ms,
        packet_loss_percent,
        download_mbps,
        upload_mbps,
        streams,
        duration_sec,
        timestamp
    ))

    connection.commit()
    connection.close()


def get_results():
    connection = sqlite3.connect("results.db")
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM results")

    results = cursor.fetchall()

    connection.close()

    return results

def get_results_by_server(server_id):
    connection = sqlite3.connect("results.db")
    cursor = connection.cursor()

    cursor.execute(
        "SELECT * FROM results WHERE server_id = ?",
        (server_id,)
    )

    results = cursor.fetchall()

    connection.close()

    return results

def get_latest_result():
    connection = sqlite3.connect("results.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT * FROM results
        ORDER BY id DESC
        LIMIT 1
    """)

    result = cursor.fetchone()

    connection.close()

    return result

create_table()