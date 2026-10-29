
import tkinter as tk
from tkinter import messagebox
import subprocess
import sys
import socket
import json
import uuid
import threading
import time
import urllib.request
import urllib.error
from pathlib import Path

# ---------------- PROJECT PATHS ----------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

API_FILE = PROJECT_ROOT / "backend" / "api.py"
RESULTS_DASHBOARD = PROJECT_ROOT / "federation" / "results_dashboard.py"
IPERF3_DISCOVERY_SERVER = PROJECT_ROOT / "federation" / "iperf3_discovery_server.py"
if not IPERF3_DISCOVERY_SERVER.exists():
    IPERF3_DISCOVERY_SERVER = PROJECT_ROOT / "federation" / "iperf3_discovery_server"

IPERF3_EXE = Path(
    r"C:\Users\P Santosh\Downloads\iperf-3.22-win64\iperf3.exe"
)

API_BASE_URL = "http://127.0.0.1:5000"
IPERF3_RESULTS_URL = API_BASE_URL + "/iperf3/results"

IPERF3_DURATION = 5
IPERF3_STREAMS = 4
IPERF3_PROCESS_TIMEOUT = 20

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# Public servers may be unavailable or restrict access.
# The frontend tries these candidates in order.
IPERF3_SERVERS = [
    ("iperf.biznetnetworks.com", 5201),
    ("iperf.biznetnetworks.com", 5202),
    ("iperf.biznetnetworks.com", 5203),
    ("speedtest.host-palace.com", 5202),
    ("iperf3.moji.fr", 5200),
]

# ---------------- SERVER CONFIGURATION ----------------

SERVERS = {
    5001: {
        "server_file": "test_server_5001.py",
        "discovery_file": "server_discovery_1.py",
        "udp_port": 6000,
    },
    5002: {
        "server_file": "test_server_5002.py",
        "discovery_file": "server_discovery_2.py",
        "udp_port": 6001,
    },
    5003: {
        "server_file": "test_server_5003.py",
        "discovery_file": "server_discovery_3.py",
        "udp_port": 6002,
    },
}

running_processes = {}
closing = False

iperf3_running = False
iperf3_process = None  # Active iperf3 client/test process, if any
iperf3_server_process = None  # Persistent local iperf3 server process
iperf3_lock = threading.Lock()
iperf3_cancel_event = threading.Event()


# ---------------- NETWORK FUNCTIONS ----------------

def get_local_ip():
    sock = None

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]

    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "Unavailable"

    finally:
        if sock:
            sock.close()


def refresh_ip():
    ip_label.config(text="Local IP: " + get_local_ip())


def get_pids_on_port(port, protocol="tcp"):
    pids = set()

    try:
        result = subprocess.run(
            ["netstat", "-ano", "-p", protocol],
            capture_output=True,
            text=True,
            creationflags=NO_WINDOW
        )

        for line in result.stdout.splitlines():
            parts = line.split()

            if protocol == "tcp":
                if len(parts) < 5:
                    continue

                local_address = parts[1]
                state = parts[3].upper()
                pid_text = parts[4]

                if state != "LISTENING":
                    continue
            else:
                if len(parts) < 4:
                    continue

                local_address = parts[1]
                pid_text = parts[-1]

            if not local_address.endswith(":" + str(port)):
                continue

            try:
                pids.add(int(pid_text))
            except ValueError:
                pass

    except Exception:
        pass

    return pids


# ---------------- PROCESS MANAGEMENT ----------------

def terminate_pid(pid):
    try:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            creationflags=NO_WINDOW,
            timeout=5
        )
    except Exception:
        pass


def start_process(key, file_path):
    if closing:
        return False

    process = running_processes.get(key)

    if process is not None and process.poll() is None:
        return True

    if not file_path.exists():
        messagebox.showerror(
            "File Not Found",
            f"Cannot find:\n{file_path}"
        )
        return False

    try:
        process = subprocess.Popen(
            [sys.executable, "-u", str(file_path)],
            cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=NO_WINDOW
        )

        running_processes[key] = process
        return True

    except Exception as error:
        messagebox.showerror(
            "Start Error",
            f"Could not start {file_path.name}.\n\n{error}"
        )
        return False


def stop_process(key):
    process = running_processes.pop(key, None)

    if process is not None and process.poll() is None:
        terminate_pid(process.pid)


def stop_port(port, protocol="tcp"):
    for pid in get_pids_on_port(port, protocol):
        terminate_pid(pid)


# ---------------- API CONTROLS ----------------

def start_api():
    if get_pids_on_port(5000, "tcp"):
        api_status.config(text="API: Running", fg="green")
        return

    if start_process("api", API_FILE):
        api_status.config(text="API: Starting...", fg="green")
        root.after(1000, check_api_status)


def check_api_status():
    if closing:
        return

    if get_pids_on_port(5000, "tcp"):
        api_status.config(text="API: Running", fg="green")
    else:
        process = running_processes.get("api")

        if process is not None and process.poll() is not None:
            api_status.config(text="API: Failed to start", fg="red")
        else:
            api_status.config(text="API: Starting...", fg="orange")
            root.after(1500, check_api_status)


def stop_api():
    stop_process("api")
    stop_port(5000, "tcp")
    api_status.config(text="API: Stopped", fg="red")


# ---------------- RESULTS DASHBOARD ----------------

def open_results():
    if closing:
        return

    if not RESULTS_DASHBOARD.exists():
        messagebox.showerror(
            "File Not Found",
            f"Cannot find the results dashboard:\n{RESULTS_DASHBOARD}"
        )
        return

    process = running_processes.get("results_dashboard")

    if process is not None and process.poll() is None:
        return

    start_process("results_dashboard", RESULTS_DASHBOARD)


# ---------------- IPERF3 OUTPUT ----------------

def append_iperf3_output(message):
    if closing:
        return

    def update():
        if closing:
            return

        iperf3_output.config(state="normal")
        iperf3_output.insert(tk.END, message + "\n")
        iperf3_output.see(tk.END)
        iperf3_output.config(state="disabled")

    root.after(0, update)


def clear_iperf3_output():
    iperf3_output.config(state="normal")
    iperf3_output.delete("1.0", tk.END)
    iperf3_output.config(state="disabled")


def set_iperf3_running(running):
    global iperf3_running
    iperf3_running = running

    if closing:
        return

    def update():
        if closing:
            return

        if running:
            run_iperf3_button.config(state="disabled")
            abort_iperf3_button.config(state="normal")
            iperf3_status.config(text="iperf3 server: Running on port 5201", fg="green")
        else:
            run_iperf3_button.config(state="normal")
            abort_iperf3_button.config(state="disabled")
            iperf3_status.config(text="iperf3 server: Stopped", fg="gray")

    root.after(0, update)


# ---------------- IPERF3 SERVER CONTROL ----------------

def start_iperf3_server():
    global iperf3_server_process

    if iperf3_running:
        return

    if not IPERF3_EXE.exists():
        messagebox.showerror(
            "iperf3 Not Found",
            "Cannot find iperf3.exe at:\n" + str(IPERF3_EXE)
        )
        return

    try:
        existing = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        existing.settimeout(1)
        try:
            if existing.connect_ex(("127.0.0.1", 5201)) == 0:
                messagebox.showerror(
                    "Port Already In Use",
                    "Something is already listening on TCP port 5201.\n\n"
                    "Stop the existing iperf3 server first, or close the terminal\n"
                    "where you started: .\\iperf3.exe -s -p 5201"
                )
                return
        finally:
            existing.close()

        iperf3_cancel_event.clear()
        clear_iperf3_output()
        append_iperf3_output("Starting iperf3 discovery responder on UDP port 6100...")

        if not start_process("iperf3_discovery", IPERF3_DISCOVERY_SERVER):
            append_iperf3_output("Could not start iperf3 discovery responder. iperf3 server was not started.")
            return

        append_iperf3_output("iperf3 discovery responder is running.")
        append_iperf3_output("Starting local iperf3 server on TCP port 5201...")

        process = subprocess.Popen(
            [str(IPERF3_EXE), "-s", "-p", "5201"],
            cwd=str(IPERF3_EXE.parent),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=NO_WINDOW
        )

        with iperf3_lock:
            iperf3_server_process = process

        time.sleep(0.4)
        if process.poll() is not None:
            with iperf3_lock:
                iperf3_server_process = None
            stop_process("iperf3_discovery")
            append_iperf3_output(
                "iperf3 server exited immediately. Port 5201 may be unavailable."
            )
            set_iperf3_running(False)
            messagebox.showerror(
                "iperf3 Server Failed",
                "The iperf3 server could not stay running. Check whether port 5201 is in use."
            )
            return

        append_iperf3_output("iperf3 server is running on port 5201.")
        append_iperf3_output("The server has no automatic time limit. Click Stop iperf3 Server to stop it.")
        set_iperf3_running(True)
        root.after(1000, check_iperf3_server)

    except Exception as error:
        stop_process("iperf3_discovery")
        append_iperf3_output(f"Could not start iperf3 server: {error}")
        messagebox.showerror("iperf3 Server Error", str(error))


def check_iperf3_server():
    global iperf3_server_process

    if closing:
        return

    with iperf3_lock:
        process = iperf3_server_process

    if process is not None and process.poll() is None:
        root.after(1000, check_iperf3_server)
    elif iperf3_running:
        with iperf3_lock:
            if iperf3_server_process is process:
                iperf3_server_process = None
        append_iperf3_output("iperf3 server stopped unexpectedly.")
        set_iperf3_running(False)


def stop_iperf3_server():
    global iperf3_server_process

    with iperf3_lock:
        process = iperf3_server_process

    if process is not None and process.poll() is None:
        terminate_pid(process.pid)
        try:
            process.wait(timeout=3)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass

    with iperf3_lock:
        iperf3_server_process = None

    stop_process("iperf3_discovery")
    append_iperf3_output("iperf3 server and discovery responder stopped.")
    set_iperf3_running(False)


# ---------------- IPERF3 PROCESS CONTROL ----------------

def run_iperf3_command(host, port, reverse=False):
    global iperf3_process

    command = [
        str(IPERF3_EXE),
        "--json",
        "-c", host,
        "-p", str(port),
        "-t", str(IPERF3_DURATION),
        "-P", str(IPERF3_STREAMS),
    ]

    if reverse:
        command.append("-R")

    if iperf3_cancel_event.is_set():
        return None, None, "Test cancelled."

    try:
        process = subprocess.Popen(
            command,
            cwd=str(IPERF3_EXE.parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=NO_WINDOW
        )

        with iperf3_lock:
            iperf3_process = process

        start_time = time.monotonic()

        while process.poll() is None:
            if iperf3_cancel_event.is_set():
                terminate_pid(process.pid)

                try:
                    process.communicate(timeout=2)
                except Exception:
                    process.kill()

                return None, None, "Test cancelled."

            if time.monotonic() - start_time > IPERF3_PROCESS_TIMEOUT:
                terminate_pid(process.pid)

                try:
                    process.communicate(timeout=2)
                except Exception:
                    process.kill()

                return None, None, (
                    f"Timed out after {IPERF3_PROCESS_TIMEOUT} seconds."
                )

            time.sleep(0.1)

        stdout, stderr = process.communicate()

        if iperf3_cancel_event.is_set():
            return None, None, "Test cancelled."

        if process.returncode != 0:
            detail = (stderr or stdout or "No error details returned").strip()
            return None, None, detail[-1200:]

        try:
            result = json.loads(stdout)
        except json.JSONDecodeError:
            return None, None, (
                "iperf3 did not return valid JSON.\n"
                + (stdout or stderr or "")[-1200:]
            )

        if result.get("error"):
            return None, None, str(result["error"])

        return result, stdout, None

    except FileNotFoundError:
        return None, None, f"iperf3 executable not found: {IPERF3_EXE}"

    except Exception as error:
        return None, None, str(error)

    finally:
        with iperf3_lock:
            if iperf3_process is not None:
                iperf3_process = None


def extract_mbps(result, reverse=False):
    end = result.get("end", {})

    # Prefer the aggregate received rate. In reverse mode the client
    # receives the download data from the server.
    if reverse:
        summary = end.get("sum_received") or end.get("sum")
    else:
        summary = end.get("sum_sent") or end.get("sum")

    if not summary:
        summary = end.get("sum_received") or end.get("sum_sent") or end.get("sum")

    if not summary:
        raise ValueError("iperf3 JSON did not contain aggregate throughput.")

    bits_per_second = summary.get("bits_per_second")

    if bits_per_second is None:
        raise ValueError("iperf3 did not return a throughput value.")

    return float(bits_per_second) / 1_000_000


# ---------------- SAVE IPERF3 RESULTS ----------------

def save_iperf3_result(payload):
    request = urllib.request.Request(
        IPERF3_RESULTS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8", errors="replace")
            return True, f"HTTP {response.status}: {body[:500]}"

    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        return False, f"HTTP {error.code}: {body[:1000]}"

    except urllib.error.URLError as error:
        return False, f"Cannot reach the API: {error.reason}"

    except Exception as error:
        return False, str(error)


# ---------------- RUN IPERF3 TEST ----------------

def start_iperf3_test():
    global iperf3_running

    if iperf3_running:
        return

    if not IPERF3_EXE.exists():
        messagebox.showerror(
            "iperf3 Not Found",
            "Cannot find iperf3.exe at:\n"
            f"{IPERF3_EXE}\n\n"
            "Check the executable path at the top of server_frontend.py."
        )
        return

    iperf3_cancel_event.clear()
    clear_iperf3_output()

    append_iperf3_output("Starting real iperf3 client test.")
    append_iperf3_output("Trying public iperf3 servers in order.")
    append_iperf3_output(
        "Each attempt has a timeout. Press Abort iperf3 Test to stop."
    )

    set_iperf3_running(True)

    threading.Thread(
        target=iperf3_test_worker,
        daemon=True
    ).start()


def iperf3_test_worker():
    successful = False

    try:
        for host, port in IPERF3_SERVERS:
            if iperf3_cancel_event.is_set():
                break

            append_iperf3_output(f"\nTrying {host}:{port} ...")

            append_iperf3_output("Running upload test...")

            upload_json, upload_raw, upload_error = run_iperf3_command(
                host, port, reverse=False
            )

            if iperf3_cancel_event.is_set():
                break

            if upload_error:
                append_iperf3_output(
                    f"Upload failed on {host}:{port}: {upload_error}"
                )
                continue

            try:
                upload_mbps = extract_mbps(upload_json, reverse=False)
            except Exception as error:
                append_iperf3_output(f"Could not read upload result: {error}")
                continue

            append_iperf3_output(
                f"Upload: {upload_mbps:.2f} Mbps"
            )
            append_iperf3_output("Running reverse download test...")

            download_json, download_raw, download_error = run_iperf3_command(
                host, port, reverse=True
            )

            if iperf3_cancel_event.is_set():
                break

            if download_error:
                append_iperf3_output(
                    f"Download failed on {host}:{port}: {download_error}"
                )
                continue

            try:
                download_mbps = extract_mbps(
                    download_json, reverse=True
                )
            except Exception as error:
                append_iperf3_output(
                    f"Could not read download result: {error}"
                )
                continue

            payload = {
                "test_id": str(uuid.uuid4()),
                "server_id": f"public_iperf3_{host}_{port}",
                "host": host,
                "port": port,
                "download_mbps": round(download_mbps, 4),
                "upload_mbps": round(upload_mbps, 4),
                "duration_sec": IPERF3_DURATION,
                "streams": IPERF3_STREAMS,
                "raw_output": json.dumps({
                    "upload": upload_json,
                    "download": download_json
                }),
                "metrics": {
                    "download_mbps": round(download_mbps, 4),
                    "upload_mbps": round(upload_mbps, 4)
                }
            }

            append_iperf3_output("\n========== IPERF3 RESULT ==========")
            append_iperf3_output(f"Server: {host}:{port}")
            append_iperf3_output(f"Download: {download_mbps:.2f} Mbps")
            append_iperf3_output(f"Upload:   {upload_mbps:.2f} Mbps")
            append_iperf3_output("===================================")

            if iperf3_cancel_event.is_set():
                break

            append_iperf3_output("Saving result to /iperf3/results ...")
            saved, save_message = save_iperf3_result(payload)

            if saved:
                append_iperf3_output("Saved iperf3 result successfully.")
                append_iperf3_output(save_message)
            else:
                append_iperf3_output(
                    "The measurement completed, but the API did not save it."
                )
                append_iperf3_output(save_message)
                append_iperf3_output(
                    "Start the Flask API and check /iperf3/results."
                )

            successful = True
            break

        if iperf3_cancel_event.is_set():
            append_iperf3_output("\niperf3 test aborted by user.")
        elif not successful:
            append_iperf3_output(
                "\nNo public server completed both tests successfully."
            )
            append_iperf3_output(
                "Check the reported errors, your internet connection, "
                "firewall rules, and whether the public servers are online."
            )

    except Exception as error:
        append_iperf3_output(f"Unexpected iperf3 error: {error}")

    finally:
        set_iperf3_running(False)


def abort_iperf3_test():
    global iperf3_process

    if not iperf3_running:
        return

    iperf3_cancel_event.set()
    append_iperf3_output("Abort requested. Stopping the active iperf3 process...")

    with iperf3_lock:
        process = iperf3_process

    if process is not None and process.poll() is None:
        terminate_pid(process.pid)

        try:
            process.wait(timeout=2)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass

    iperf3_status.config(text="iperf3: Aborting...", fg="red")


# ---------------- VIEW SAVED IPERF3 RESULTS ----------------

def view_iperf3_results():
    append_iperf3_output("\nFetching saved iperf3 results from the API...")

    threading.Thread(
        target=fetch_iperf3_results_worker,
        daemon=True
    ).start()


def fetch_iperf3_results_worker():
    request = urllib.request.Request(
        IPERF3_RESULTS_URL,
        headers={"Accept": "application/json"},
        method="GET"
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8", errors="replace")

            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                append_iperf3_output(
                    f"Results API returned invalid JSON: {body[:1000]}"
                )
                return

        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            records = None

            for key in ("results", "data", "records", "iperf3_results"):
                if isinstance(data.get(key), list):
                    records = data[key]
                    break

            if records is None:
                # Handle an API that returns a single record.
                if any(
                    key in data
                    for key in (
                        "download_mbps",
                        "upload_mbps",
                        "test_id"
                    )
                ):
                    records = [data]
                else:
                    append_iperf3_output(
                        "The API responded, but its JSON format was not "
                        "recognized:\n" + json.dumps(data, indent=2)[:2000]
                    )
                    return
        else:
            append_iperf3_output(
                f"Unexpected results response type: {type(data).__name__}"
            )
            return

        if not records:
            append_iperf3_output(
                "The API returned no saved iperf3 results."
            )
            return

        append_iperf3_output(
            f"\nSaved iperf3 records returned: {len(records)}"
        )
        append_iperf3_output("Showing the latest 20 records:")

        for index, record in enumerate(reversed(records[-20:]), start=1):
            if not isinstance(record, dict):
                append_iperf3_output(f"\n{index}. {record}")
                continue

            append_iperf3_output(
                f"\n{index}. "
                f"Server: {record.get('server_id', record.get('host', 'Unknown'))}"
            )
            append_iperf3_output(
                f"   Download: {record.get('download_mbps', 'N/A')} Mbps"
            )
            append_iperf3_output(
                f"   Upload: {record.get('upload_mbps', 'N/A')} Mbps"
            )
            append_iperf3_output(
                f"   Time: {record.get('timestamp', record.get('created_at', 'N/A'))}"
            )
            append_iperf3_output(
                f"   Test ID: {record.get('test_id', record.get('id', 'N/A'))}"
            )

    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        append_iperf3_output(
            f"GET /iperf3/results failed with HTTP {error.code}.\n"
            f"Response: {body[:1500]}"
        )

    except urllib.error.URLError as error:
        append_iperf3_output(
            "Cannot connect to the Flask API at "
            f"{IPERF3_RESULTS_URL}\nReason: {error.reason}\n"
            "Click Start API and retry."
        )

    except Exception as error:
        append_iperf3_output(f"Could not fetch iperf3 results: {error}")


# ---------------- MEASUREMENT SERVERS ----------------

def start_server(port):
    if closing:
        return

    config = SERVERS[port]

    server_file = PROJECT_ROOT / "federation" / config["server_file"]
    discovery_file = PROJECT_ROOT / "federation" / config["discovery_file"]
    udp_port = config["udp_port"]

    if get_pids_on_port(port, "tcp"):
        server_status[port].config(
            text=f"TCP {port}: Running",
            fg="green"
        )
    elif start_process(f"server_{port}", server_file):
        server_status[port].config(
            text=f"TCP {port}: Started",
            fg="green"
        )

    if get_pids_on_port(udp_port, "udp"):
        discovery_status[port].config(
            text=f"UDP {udp_port}: Running",
            fg="green"
        )
    elif start_process(f"discovery_{port}", discovery_file):
        discovery_status[port].config(
            text=f"UDP {udp_port}: Started",
            fg="green"
        )


def stop_server(port):
    config = SERVERS[port]
    udp_port = config["udp_port"]

    stop_process(f"server_{port}")
    stop_process(f"discovery_{port}")

    stop_port(port, "tcp")
    stop_port(udp_port, "udp")

    server_status[port].config(
        text=f"TCP {port}: Stopped",
        fg="red"
    )

    discovery_status[port].config(
        text=f"UDP {udp_port}: Stopped",
        fg="red"
    )


# ---------------- AUTOMATIC SHUTDOWN ----------------

def close_frontend():
    global closing, iperf3_process, iperf3_server_process

    if closing:
        return

    closing = True
    iperf3_cancel_event.set()

    # Stop both the active iperf3 client test and the persistent local server.
    with iperf3_lock:
        test_process = iperf3_process
        server_process = iperf3_server_process
        iperf3_process = None
        iperf3_server_process = None

    for process in (test_process, server_process):
        if process is not None and process.poll() is None:
            terminate_pid(process.pid)
            try:
                process.wait(timeout=3)
            except Exception:
                try:
                    process.kill()
                    process.wait(timeout=2)
                except Exception:
                    pass

    for key in list(running_processes.keys()):
        stop_process(key)

    # Also stop any owned listeners as a fallback during shutdown.
    for port in [5000, 5001, 5002, 5003, 5201]:
        stop_port(port, "tcp")

    for port in [6000, 6001, 6002, 6100]:
        stop_port(port, "udp")

    root.destroy()


# ---------------- GUI ----------------

root = tk.Tk()
root.title("Mini-Ookla Server Manager")
root.geometry("850x850")
root.minsize(760, 700)
root.resizable(True, True)

title_label = tk.Label(
    root,
    text="Mini-Ookla Server Manager",
    font=("Arial", 18, "bold")
)
title_label.pack(pady=10)

# IP address

ip_frame = tk.Frame(root)
ip_frame.pack(pady=4)

ip_label = tk.Label(
    ip_frame,
    text="Local IP: " + get_local_ip(),
    font=("Arial", 11)
)
ip_label.pack(side="left", padx=8)

tk.Button(
    ip_frame,
    text="Refresh IP",
    command=refresh_ip
).pack(side="left")

# API section

api_frame = tk.LabelFrame(
    root,
    text="Flask API",
    font=("Arial", 11, "bold"),
    padx=10,
    pady=8
)
api_frame.pack(fill="x", padx=18, pady=7)

api_status = tk.Label(
    api_frame,
    text="API: Not checked",
    fg="gray",
    font=("Arial", 10)
)
api_status.grid(row=0, column=0, columnspan=3, pady=4)

tk.Button(
    api_frame,
    text="Start API",
    width=15,
    command=start_api
).grid(row=1, column=0, padx=5, pady=4)

tk.Button(
    api_frame,
    text="Stop API",
    width=15,
    command=stop_api
).grid(row=1, column=1, padx=5, pady=4)

tk.Button(
    api_frame,
    text="Results Dashboard",
    width=18,
    command=open_results
).grid(row=1, column=2, padx=5, pady=4)

# Measurement servers

servers_frame = tk.LabelFrame(
    root,
    text="Mini-Ookla Measurement Servers and UDP Discovery",
    font=("Arial", 11, "bold"),
    padx=8,
    pady=6
)
servers_frame.pack(fill="x", padx=18, pady=7)

server_status = {}
discovery_status = {}

for row_number, port in enumerate(SERVERS):
    udp_port = SERVERS[port]["udp_port"]

    tk.Label(
        servers_frame,
        text=f"Server TCP {port}",
        font=("Arial", 10, "bold")
    ).grid(
        row=row_number * 2,
        column=0,
        sticky="w",
        padx=5,
        pady=3
    )

    tk.Button(
        servers_frame,
        text="Start",
        width=8,
        command=lambda p=port: start_server(p)
    ).grid(
        row=row_number * 2,
        column=1,
        padx=3,
        pady=3
    )

    tk.Button(
        servers_frame,
        text="Stop",
        width=8,
        command=lambda p=port: stop_server(p)
    ).grid(
        row=row_number * 2,
        column=2,
        padx=3,
        pady=3
    )

    server_status[port] = tk.Label(
        servers_frame,
        text=f"TCP {port}: Not checked",
        fg="gray"
    )
    server_status[port].grid(
        row=row_number * 2,
        column=3,
        sticky="w",
        padx=5
    )

    discovery_status[port] = tk.Label(
        servers_frame,
        text=f"UDP {udp_port}: Not checked",
        fg="gray"
    )
    discovery_status[port].grid(
        row=row_number * 2 + 1,
        column=0,
        columnspan=4,
        sticky="w",
        padx=12,
        pady=(0, 4)
    )

# iperf3 section

iperf3_frame = tk.LabelFrame(
    root,
    text="Local iperf3 Server (TCP 5201)",
    font=("Arial", 11, "bold"),
    padx=8,
    pady=6
)
iperf3_frame.pack(fill="both", expand=True, padx=18, pady=7)

iperf3_status = tk.Label(
    iperf3_frame,
    text="iperf3: Idle",
    fg="gray",
    font=("Arial", 10, "bold")
)
iperf3_status.pack(pady=3)

iperf3_button_frame = tk.Frame(iperf3_frame)
iperf3_button_frame.pack(pady=4)

run_iperf3_button = tk.Button(
    iperf3_button_frame,
    text="Start iperf3 Server",
    width=20,
    command=start_iperf3_server
)
run_iperf3_button.pack(side="left", padx=4)

abort_iperf3_button = tk.Button(
    iperf3_button_frame,
    text="Stop iperf3 Server",
    width=20,
    state="disabled",
    command=stop_iperf3_server
)
abort_iperf3_button.pack(side="left", padx=4)

tk.Button(
    iperf3_button_frame,
    text="View iperf3 Results",
    width=20,
    command=view_iperf3_results
).pack(side="left", padx=4)

tk.Label(
    iperf3_frame,
    text="Starts iperf3 server on TCP 5201 and discovery responder on UDP 6100. Both stop when you stop them or close this frontend.",
    fg="gray",
    font=("Arial", 9)
).pack(pady=2)

output_frame = tk.Frame(iperf3_frame)
output_frame.pack(fill="both", expand=True, padx=4, pady=4)

output_scrollbar = tk.Scrollbar(output_frame)
output_scrollbar.pack(side="right", fill="y")

iperf3_output = tk.Text(
    output_frame,
    height=12,
    wrap="word",
    state="disabled",
    yscrollcommand=output_scrollbar.set
)
iperf3_output.pack(side="left", fill="both", expand=True)

output_scrollbar.config(command=iperf3_output.yview)

root.protocol("WM_DELETE_WINDOW", close_frontend)
root.mainloop()
