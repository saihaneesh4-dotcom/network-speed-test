
import tkinter as tk
from tkinter import messagebox
import subprocess
import sys
import socket
from pathlib import Path

# ---------------- PROJECT PATHS ----------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

API_FILE = PROJECT_ROOT / "backend" / "api.py"
RESULTS_DASHBOARD = (
    PROJECT_ROOT / "federation" / "results_dashboard.py"
)

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

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
    """Find processes using a configured port on Windows."""
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

def start_process(key, file_path):
    """Start a script in the background without a terminal."""
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


def terminate_pid(pid):
    """Terminate a process and its child processes silently."""
    try:
        subprocess.run(
            [
                "taskkill",
                "/PID",
                str(pid),
                "/T",
                "/F"
            ],
            capture_output=True,
            text=True,
            creationflags=NO_WINDOW
        )
    except Exception:
        pass


def stop_process(key):
    """Stop a process managed by this frontend."""
    process = running_processes.pop(key, None)

    if process is not None and process.poll() is None:
        terminate_pid(process.pid)


def stop_port(port, protocol="tcp"):
    """Stop processes listening on a configured project port."""
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
    """Open the separate results dashboard without a terminal."""
    if closing:
        return

    if not RESULTS_DASHBOARD.exists():
        messagebox.showerror(
            "File Not Found",
            "Cannot find the results dashboard:\n"
            f"{RESULTS_DASHBOARD}"
        )
        return

    process = running_processes.get("results_dashboard")

    if process is not None and process.poll() is None:
        return

    if start_process("results_dashboard", RESULTS_DASHBOARD):
        pass


# ---------------- MEASUREMENT SERVERS ----------------

def start_server(port):
    if closing:
        return

    config = SERVERS[port]

    server_file = (
        PROJECT_ROOT / "federation" / config["server_file"]
    )

    discovery_file = (
        PROJECT_ROOT / "federation" / config["discovery_file"]
    )

    udp_port = config["udp_port"]

    # Start TCP measurement server
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

    # Start UDP discovery server
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
    """Stop the API, dashboard, measurement and discovery servers."""
    global closing

    if closing:
        return

    closing = True

    # Stop all processes launched by this frontend.
    for key in list(running_processes.keys()):
        stop_process(key)

    # Also stop any remaining processes on the project's ports.
    for port in [5000, 5001, 5002, 5003]:
        stop_port(port, "tcp")

    for port in [6000, 6001, 6002]:
        stop_port(port, "udp")

    root.destroy()


# ---------------- GUI ----------------

root = tk.Tk()
root.title("Mini-Ookla Server Manager")
root.geometry("650x610")
root.resizable(True, True)

title_label = tk.Label(
    root,
    text="Mini-Ookla Server Manager",
    font=("Arial", 18, "bold")
)
title_label.pack(pady=12)

# IP address
ip_frame = tk.Frame(root)
ip_frame.pack(pady=5)

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
    pady=10
)
api_frame.pack(fill="x", padx=20, pady=10)

api_status = tk.Label(
    api_frame,
    text="API: Not checked",
    fg="gray",
    font=("Arial", 10)
)
api_status.grid(row=0, column=0, columnspan=3, pady=5)

tk.Button(
    api_frame,
    text="Start API",
    width=15,
    command=start_api
).grid(row=1, column=0, padx=5, pady=5)

tk.Button(
    api_frame,
    text="Stop API",
    width=15,
    command=stop_api
).grid(row=1, column=1, padx=5, pady=5)

tk.Button(
    api_frame,
    text="Results",
    width=15,
    command=open_results
).grid(row=1, column=2, padx=5, pady=5)

# Measurement server section
servers_frame = tk.LabelFrame(
    root,
    text="Measurement Servers and UDP Discovery",
    font=("Arial", 11, "bold"),
    padx=10,
    pady=8
)
servers_frame.pack(fill="both", expand=True, padx=20, pady=10)

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
        pady=4
    )

    tk.Button(
        servers_frame,
        text="Start",
        width=9,
        command=lambda p=port: start_server(p)
    ).grid(
        row=row_number * 2,
        column=1,
        padx=3,
        pady=4
    )

    tk.Button(
        servers_frame,
        text="Stop",
        width=9,
        command=lambda p=port: stop_server(p)
    ).grid(
        row=row_number * 2,
        column=2,
        padx=3,
        pady=4
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
        pady=(0, 5)
    )

# Close immediately and shut down the project's processes.
root.protocol("WM_DELETE_WINDOW", close_frontend)

root.mainloop()
