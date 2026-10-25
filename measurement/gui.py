
import sys
import os
import json
import threading
import subprocess
from datetime import datetime
from pathlib import Path

import requests
import tkinter as tk

# Allow imports from the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from measurement.measurement_engine import run_test
from federation.server_selector import select_best_server
from federation.iperf3_discovery import discover_iperf3_server


# ================= CONFIGURATION =================

# Santosh's existing Mini-Ookla backend
BACKEND_URL = "http://10.56.66.133:5000/results"

# iperf3 configuration
IPERF3_DURATION = 5
IPERF3_STREAMS = 4
IPERF3_OMIT = 2

# Santosh's separate iperf3 validation API (POST only from this GUI).
# 127.0.0.1 works ONLY if Flask is running on this same Mac.
IPERF3_API_BASE = "http://10.56.66.133:5000/iperf3/results"
IPERF3_CLIENT_ID = "aarav-mac"


# ================= MINI-OOKLA TEST =================

def start_test():
    start_button.config(state="disabled")
    status_label.config(text="Running Mini-Ookla test...")

    threading.Thread(
        target=run_measurement,
        daemon=True
    ).start()


def run_measurement():
    try:
        # Existing Mini-Ookla server discovery
        server = select_best_server()

        if server is None:
            root.after(
                0,
                lambda: finish_with_message("No server available")
            )
            return

        result = run_test(
            host=server["host"],
            port=server["port"],
            duration_sec=5,
            streams=4,
            ramp_up_sec=2
        )

        if result is None:
            root.after(
                0,
                lambda: finish_with_message("Measurement failed")
            )
            return

        payload = {
            "server_id": server["server_id"],
            "latency_ms": result["latency_ms"],
            "jitter_ms": result["jitter_ms"],
            "packet_loss_percent": result["packet_loss_percent"],
            "download_mbps": result["download_mbps"],
            "upload_mbps": result["upload_mbps"],
            "streams": result["streams"],
            "duration_sec": result["duration_sec"]
        }

        message = "Mini-Ookla test completed"

        # Existing Flask backend integration
        try:
            response = requests.post(
                BACKEND_URL,
                json=payload,
                timeout=5
            )

            if response.ok:
                message += " — backend accepted results"
            else:
                message += f" — backend error {response.status_code}"

            print("Mini-Ookla backend response:", response.status_code)
            print(response.text)

        except requests.exceptions.RequestException as error:
            message += " — backend connection failed"
            print("Mini-Ookla backend request failed:", repr(error))

        root.after(
            0,
            lambda: update_results(server, result, message)
        )

    except Exception as error:
        print("Mini-Ookla measurement error:", repr(error))
        root.after(
            0,
            lambda: finish_with_message(
                "Mini-Ookla failed — check terminal"
            )
        )


def finish_with_message(message):
    status_label.config(text=message)
    start_button.config(state="normal")


def update_results(server, result, message="Test completed"):
    server_value.config(text=server["server_id"])
    latency_value.config(text=f'{result["latency_ms"]:.2f} ms')
    jitter_value.config(text=f'{result["jitter_ms"]:.2f} ms')
    loss_value.config(
        text=f'{result["packet_loss_percent"]:.2f} %'
    )
    download_value.config(text=f'{result["download_mbps"]:.2f} Mbps')
    upload_value.config(text=f'{result["upload_mbps"]:.2f} Mbps')
    streams_value.config(text=str(result["streams"]))
    duration_value.config(text=f'{result["duration_sec"]} sec')

    status_label.config(text=message)
    start_button.config(state="normal")


# ================= IPERF3 TEST =================

def start_iperf3_test():
    iperf3_button.config(state="disabled")
    status_label.config(text="Discovering iperf3 server...")

    threading.Thread(
        target=run_iperf3_test,
        daemon=True
    ).start()


def run_iperf3_test():
    """Measure upload + download and send the trial directly to Santosh's API."""
    try:
        server = discover_iperf3_server()
        if server is None:
            root.after(0, lambda: finish_iperf3("iperf3 server not found"))
            return

        server_ip = server["host"]
        server_port = int(server["port"])
        print(f"Discovered iperf3 server: {server_ip}:{server_port}")

        def run_direction(reverse=False):
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
                command, capture_output=True, text=True,
                timeout=45, check=False
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    completed.stderr.strip() or
                    f"iperf3 exited with code {completed.returncode}"
                )
            try:
                output = json.loads(completed.stdout)
            except json.JSONDecodeError as error:
                print("Raw iperf3 stdout:", completed.stdout[:1000])
                raise RuntimeError("iperf3 returned invalid JSON") from error

            end_data = output.get("end", {})
            # Prefer aggregate receiver throughput; use sender summary as fallback.
            summaries = [
                end_data.get("sum_received"),
                end_data.get("sum_sent"),
                end_data.get("sum"),
            ]
            for summary in summaries:
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

        root.after(0, lambda: status_label.config(text="Measuring upload..."))
        upload_mbps = run_direction(reverse=False)
        root.after(0, lambda: status_label.config(text="Measuring download..."))
        download_mbps = run_direction(reverse=True)

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
        }

        # No local JSON storage: send the measured trial directly to the dedicated API.
        # Timestamp-derived ID avoids needing a local counter/file.
        trial["trial_id"] = int(datetime.now().timestamp() * 1000)
        root.after(0, lambda: status_label.config(text="Sending iperf3 result to backend..."))
        upload_status = post_iperf3_trial(trial)
        message = (
            f"iperf3 Trial {trial['trial_id']} — Up: {upload_mbps:.2f} Mbps, "
            f"Down: {download_mbps:.2f} Mbps — {upload_status}"
        )
        print(message)
        root.after(0, lambda: finish_iperf3(message))

    except FileNotFoundError:
        print("Error: iperf3 executable or required file was not found.")
        root.after(0, lambda: finish_iperf3("iperf3 or required file not found — check terminal"))
    except subprocess.TimeoutExpired:
        print("Error: iperf3 test timed out.")
        root.after(0, lambda: finish_iperf3("iperf3 test timed out"))
    except Exception as error:
        print("iperf3 error:", repr(error))
        root.after(0, lambda: finish_iperf3("iperf3 failed — check terminal"))


def post_iperf3_trial(trial):
    """POST one real iperf3 trial to Santosh's isolated endpoint."""
    try:
        # The backend expects download_mbps and upload_mbps at the top level.
        # Send the measured trial directly, not wrapped in {"result": ...}.
        response = requests.post(
            IPERF3_API_BASE,
            json=trial,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        print("iperf3 API POST URL:", response.request.url)
        print("iperf3 API POST headers:", dict(response.request.headers))
        print("iperf3 API POST body:", response.request.body)
        print("iperf3 API POST status:", response.status_code)
        print("iperf3 API response:", response.text[:1000])
        if response.status_code in (200, 201):
            return "saved to backend"
        return f"backend rejected result (HTTP {response.status_code})"
    except requests.exceptions.RequestException as error:
        print("iperf3 API POST failed:", repr(error))
        return "backend connection failed; result was not saved"


def finish_iperf3(message):
    status_label.config(text=message)
    iperf3_button.config(state="normal")


# ================= GUI =================

root = tk.Tk()
root.title("Mini Ookla")
root.geometry("520x650")
root.resizable(False, False)

title = tk.Label(
    root,
    text="MINI OOKLA",
    font=("Arial", 24, "bold")
)
title.pack(pady=20)

start_button = tk.Button(
    root,
    text="START TEST",
    font=("Arial", 14, "bold"),
    command=start_test,
    width=20
)
start_button.pack(pady=6)

iperf3_button = tk.Button(
    root,
    text="RUN IPERF3 TEST",
    font=("Arial", 12, "bold"),
    command=start_iperf3_test,
    width=20
)
iperf3_button.pack(pady=6)

status_label = tk.Label(
    root,
    text="Ready",
    font=("Arial", 10),
    wraplength=470
)
status_label.pack(pady=10)

frame = tk.Frame(root)
frame.pack(pady=10)


def add_row(row, name):
    label = tk.Label(
        frame,
        text=name,
        font=("Arial", 12),
        anchor="w",
        width=18
    )
    label.grid(row=row, column=0, padx=10, pady=7)

    value = tk.Label(
        frame,
        text="--",
        font=("Arial", 12, "bold"),
        anchor="e",
        width=20
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
