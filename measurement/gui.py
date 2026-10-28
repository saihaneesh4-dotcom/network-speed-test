
import sys
import json
import threading
import subprocess
from datetime import datetime
from pathlib import Path

import requests
import tkinter as tk

# Allow imports from the project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from measurement.measurement_engine import run_test
from federation.server_selector import select_best_server
from federation.iperf3_discovery import discover_iperf3_server


# ================= CONFIGURATION =================
BACKEND_BASE = "http://10.113.250.133:5000"
BACKEND_URL = f"{BACKEND_BASE}/results"
IPERF3_API_URL = f"{BACKEND_BASE}/iperf3/results"
VALIDATION_SESSIONS_URL = f"{BACKEND_BASE}/validation/sessions"

IPERF3_CLIENT_ID = "aarav-mac"
IPERF3_DURATION = 5
IPERF3_STREAMS = 4
IPERF3_OMIT = 2

MINI_OOKLA_DURATION = 5
MINI_OOKLA_STREAMS = 4
MINI_OOKLA_RAMP_UP = 2
REQUEST_TIMEOUT = 10


# ================= VALIDATION SESSION API =================
def create_validation_session():
    response = requests.post(
        VALIDATION_SESSIONS_URL,
        json={},
        headers={"Content-Type": "application/json"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    session_id = data.get("session_id")

    if not session_id:
        raise RuntimeError(f"Backend did not return session_id: {data}")

    print("Created validation session:", session_id)
    return session_id


def update_validation_session(session_id, **fields):
    response = requests.patch(
        f"{VALIDATION_SESSIONS_URL}/{session_id}",
        json=fields,
        headers={"Content-Type": "application/json"},
        timeout=REQUEST_TIMEOUT,
    )
    print("Session PATCH:", response.status_code, response.text[:1000])
    response.raise_for_status()
    return response.json() if response.content else {}


def fetch_validation_session(session_id):
    response = requests.get(
        f"{VALIDATION_SESSIONS_URL}/{session_id}",
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


# ================= MINI-OOKLA TEST =================
def measure_mini_ookla(session_id=None):
    server = select_best_server()

    if server is None:
        raise RuntimeError("No Mini-Ookla server available")

    result = run_test(
        host=server["host"],
        port=server["port"],
        duration_sec=MINI_OOKLA_DURATION,
        streams=MINI_OOKLA_STREAMS,
        ramp_up_sec=MINI_OOKLA_RAMP_UP,
    )

    if result is None:
        raise RuntimeError("Mini-Ookla measurement returned no result")

    payload = {
        "server_id": server["server_id"],
        "latency_ms": result["latency_ms"],
        "jitter_ms": result["jitter_ms"],
        "packet_loss_percent": result["packet_loss_percent"],
        "download_mbps": result["download_mbps"],
        "upload_mbps": result["upload_mbps"],
        "streams": result["streams"],
        "duration_sec": result["duration_sec"],
    }

    if session_id:
        payload["session_id"] = session_id

    response = requests.post(
        BACKEND_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=REQUEST_TIMEOUT,
    )

    print(
        "Mini-Ookla backend response:",
        response.status_code,
        response.text[:1000],
    )

    if not response.ok:
        raise RuntimeError(
            f"Mini-Ookla result rejected (HTTP {response.status_code})"
        )

    return server, result, "Mini-Ookla completed — result saved to backend"


def start_test():
    set_test_buttons("disabled")
    status_label.config(text="Running Mini-Ookla test...")
    threading.Thread(target=run_mini_ookla_button, daemon=True).start()


def run_mini_ookla_button():
    try:
        server, result, message = measure_mini_ookla()
        root.after(
            0,
            lambda s=server, r=result, m=message: update_results(s, r, m),
        )
    except Exception as error:
        print("Mini-Ookla error:", repr(error))
        message = f"Mini-Ookla failed: {error}"
        root.after(0, lambda msg=message: finish_with_message(msg))


def update_results(server, result, message="Test completed", enable_buttons=True):
    server_value.config(text=server["server_id"])
    latency_value.config(text=f'{result["latency_ms"]:.2f} ms')
    jitter_value.config(text=f'{result["jitter_ms"]:.2f} ms')
    loss_value.config(text=f'{result["packet_loss_percent"]:.2f} %')
    download_value.config(text=f'{result["download_mbps"]:.2f} Mbps')
    upload_value.config(text=f'{result["upload_mbps"]:.2f} Mbps')
    streams_value.config(text=str(result["streams"]))
    duration_value.config(text=f'{result["duration_sec"]} sec')
    status_label.config(text=message)

    if enable_buttons:
        set_test_buttons("normal")


# ================= IPERF3 TEST =================
def run_iperf3_direction(server_ip, server_port, reverse=False):
    command = [
        "iperf3", "-J", "-c", server_ip,
        "-p", str(server_port),
        "-t", str(IPERF3_DURATION),
        "-P", str(IPERF3_STREAMS),
        "-O", str(IPERF3_OMIT),
    ]

    if reverse:
        command.append("-R")

    print("Running:", " ".join(command))

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )

    if completed.returncode != 0:
        raise RuntimeError(
            completed.stderr.strip()
            or f"iperf3 exited with code {completed.returncode}"
        )

    try:
        output = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        print("Raw iperf3 stdout:", completed.stdout[:1000])
        raise RuntimeError("iperf3 returned invalid JSON") from error

    end_data = output.get("end", {})

    for summary in (
        end_data.get("sum_received"),
        end_data.get("sum_sent"),
        end_data.get("sum"),
    ):
        if isinstance(summary, dict) and summary.get("bits_per_second") is not None:
            return float(summary["bits_per_second"]) / 1_000_000

    stream_rates = []

    for stream in end_data.get("streams", []):
        for side in ("receiver", "sender"):
            rate = stream.get(side, {}).get("bits_per_second")
            if rate is not None:
                stream_rates.append(float(rate))
                break

    if stream_rates:
        return sum(stream_rates) / 1_000_000

    raise RuntimeError("Could not find throughput in iperf3 JSON output")


def measure_iperf3(session_id=None):
    server = discover_iperf3_server()

    if server is None:
        raise RuntimeError("iperf3 server not found")

    server_ip = server["host"]
    server_port = int(server["port"])

    print(f"Discovered iperf3 server: {server_ip}:{server_port}")

    set_status_from_worker("Measuring iperf3 upload...")
    upload_mbps = run_iperf3_direction(
        server_ip, server_port, reverse=False
    )

    set_status_from_worker("Measuring iperf3 download...")
    download_mbps = run_iperf3_direction(
        server_ip, server_port, reverse=True
    )

    if upload_mbps < 0 or download_mbps < 0:
        raise RuntimeError("Invalid negative throughput")

    trial = {
        "client_id": IPERF3_CLIENT_ID,
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "server_ip": server_ip,
        "server_port": server_port,
        "protocol": "TCP",
        "streams": IPERF3_STREAMS,
        "duration_sec": IPERF3_DURATION,
        "omit_sec": IPERF3_OMIT,
        "upload_mbps": round(upload_mbps, 3),
        "download_mbps": round(download_mbps, 3),
        "trial_id": int(datetime.now().timestamp() * 1000),
    }

    if session_id:
        trial["session_id"] = session_id

    post_iperf3_trial(trial)

    message = (
        f"iperf3 — Down: {download_mbps:.2f} Mbps ,"
        f"Up: {upload_mbps:.2f} Mbps — saved to backend "
    )

    return trial, message


def post_iperf3_trial(trial):
    response = requests.post(
        IPERF3_API_URL,
        json=trial,
        headers={"Content-Type": "application/json"},
        timeout=REQUEST_TIMEOUT,
    )

    print("iperf3 API POST URL:", response.request.url)
    print("iperf3 API POST body:", response.request.body)
    print("iperf3 API POST status:", response.status_code)
    print("iperf3 API response:", response.text[:1000])

    if not response.ok:
        raise RuntimeError(
            f"iperf3 result rejected (HTTP {response.status_code})"
        )


def start_iperf3_test():
    set_test_buttons("disabled")
    status_label.config(text="Discovering iperf3 server...")
    threading.Thread(target=run_iperf3_button, daemon=True).start()


def run_iperf3_button():
    try:
        _trial, message = measure_iperf3()
        root.after(0, lambda msg=message: finish_with_message(msg))
    except Exception as error:
        print("iperf3 error:", repr(error))
        message = f"iperf3 failed: {error}"
        root.after(0, lambda msg=message: finish_with_message(msg))


# ================= COMBINED VALIDATION =================
def start_combined_validation():
    set_test_buttons("disabled")
    iperf3_result_label.config(text="")
    status_label.config(text="Creating validation session...")
    threading.Thread(target=run_combined_validation, daemon=True).start()


def run_combined_validation():
    try:
        session_id = create_validation_session()
    except Exception as error:
        print("Could not create validation session:", repr(error))
        message = f"Could not create validation session: {error}"
        root.after(0, lambda msg=message: finish_with_message(msg))
        return

    root.after(
        0,
        lambda sid=session_id: status_label.config(
            text=f"Validation {sid}: running Mini-Ookla..."
        ),
    )

    mini_status, mini_error = "failed", None
    iperf3_status, iperf3_error = "failed", None

    try:
        server, result, mini_message = measure_mini_ookla(
            session_id=session_id
        )
        mini_status = "completed"

        root.after(
            0,
            lambda s=server, r=result, m=mini_message: update_results(
                s, r, m, enable_buttons=False
            ),
        )
    except Exception as error:
        mini_error = str(error)
        print("Combined validation: Mini-Ookla failed:", repr(error))

    try:
        update_validation_session(
            session_id,
            mini_ookla_status=mini_status,
            mini_ookla_error=mini_error,
        )
    except Exception as error:
        print("Could not update Mini-Ookla session status:", repr(error))
        mini_error = mini_error or f"Session update failed: {error}"

    root.after(
        0,
        lambda sid=session_id: status_label.config(
            text=f"Validation {sid}: running iperf3..."
        ),
    )

    try:
        trial, iperf3_message = measure_iperf3(session_id=session_id)
        iperf3_status = "completed"

        # Display iperf3 results at the top ONLY for combined validation.
        root.after(
            0,
            lambda msg=iperf3_message: iperf3_result_label.config(text=msg),
        )

        print(iperf3_message)

    except Exception as error:
        iperf3_error = str(error)
        print("Combined validation: iperf3 failed:", repr(error))

    try:
        update_validation_session(
            session_id,
            iperf3_status=iperf3_status,
            iperf3_error=iperf3_error,
        )
    except Exception as error:
        print("Could not update iperf3 session status:", repr(error))
        iperf3_error = iperf3_error or f"Session update failed: {error}"

    try:
        session_data = fetch_validation_session(session_id)
        overall_status = session_data.get("status", "unknown")
    except Exception as error:
        print("Could not fetch final validation session:", repr(error))
        session_data = None
        overall_status = "unknown"

    if mini_status == "completed" and iperf3_status == "completed":
        detail = "Both tests completed."
    elif mini_status == "completed" or iperf3_status == "completed":
        detail = "Partial validation: one test completed and one failed."
    else:
        detail = "Validation failed: both tests failed."

    message = f"Validation {session_id}: {overall_status}. {detail}"

    print("Final validation session:", session_data)
    root.after(0, lambda msg=message: finish_with_message(msg))


# ================= SHARED GUI HELPERS =================
def set_status_from_worker(message):
    root.after(0, lambda msg=message: status_label.config(text=msg))


def set_test_buttons(state):
    start_button.config(state=state)
    iperf3_button.config(state=state)
    combined_button.config(state=state)


def finish_with_message(message):
    status_label.config(text=message)
    set_test_buttons("normal")


# ================= GUI =================
root = tk.Tk()
root.title("Mini Ookla")
root.geometry("560x700")
root.resizable(False, False)

title = tk.Label(root, text="MINI OOKLA", font=("Arial", 24, "bold"))
title.pack(pady=20)

start_button = tk.Button(
    root,
    text="START TEST",
    font=("Arial", 14, "bold"),
    command=start_test,
    width=24,
)
start_button.pack(pady=6)

iperf3_button = tk.Button(
    root,
    text="RUN IPERF3 TEST",
    font=("Arial", 12, "bold"),
    command=start_iperf3_test,
    width=24,
)
iperf3_button.pack(pady=6)

combined_button = tk.Button(
    root,
    text="RUN COMBINED VALIDATION",
    font=("Arial", 12, "bold"),
    command=start_combined_validation,
    width=24,
)
combined_button.pack(pady=6)

status_label = tk.Label(
    root,
    text="Ready",
    font=("Arial", 10),
    wraplength=510,
)
status_label.pack(pady=10)

# Dedicated iperf3 result banner.
# It remains blank unless Combined Validation succeeds for iperf3.
iperf3_result_label = tk.Label(
    root,
    text="",
    font=("Arial", 10, "bold"),
    wraplength=510,
    justify="center",
)
iperf3_result_label.pack(pady=4)

frame = tk.Frame(root)
frame.pack(pady=10)


def add_row(row, name):
    label = tk.Label(
        frame,
        text=name,
        font=("Arial", 12),
        anchor="w",
        width=18,
    )
    label.grid(row=row, column=0, padx=10, pady=7)

    value = tk.Label(
        frame,
        text="--",
        font=("Arial", 12, "bold"),
        anchor="e",
        width=20,
    )
    value.grid(row=row, column=1, padx=10, pady=7)

    return value


server_value = add_row(0, "Selected Server")
latency_value = add_row(1, "Latency")
jitter_value = add_row(2, "Jitter")
loss_value = add_row(3, "Packet Loss")
download_value = add_row(4, "Download")
upload_value = add_row(5, "Upload")
streams_value = add_row(6, "Streams")
duration_value = add_row(7, "Duration")

root.mainloop()
