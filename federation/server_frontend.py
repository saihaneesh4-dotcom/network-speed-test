import tkinter as tk
from tkinter import messagebox
import socket
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

servers = {
    5001: "test_server_5001.py",
    5002: "test_server_5002.py",
    5003: "test_server_5003.py"
}

processes = {}


def get_ip_address():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
    except:
        ip = "Unable to detect IP"
    finally:
        sock.close()

    return ip


def start_server(port):
    if port in processes and processes[port].poll() is None:
        messagebox.showinfo("Server", f"Server on port {port} is already running")
        return

    file = BASE_DIR / servers[port]

    process = subprocess.Popen(
        [sys.executable, str(file)]
    )

    processes[port] = process

    status_labels[port].config(
        text=f"Running on {ip_address}:{port}"
    )


def stop_server(port):
    if port in processes and processes[port].poll() is None:
        processes[port].terminate()
        status_labels[port].config(text="Stopped")
    else:
        status_labels[port].config(text="Stopped")


def refresh_ip():
    global ip_address

    ip_address = get_ip_address()

    ip_label.config(
        text=f"Your IP Address: {ip_address}"
    )


def close_application():
    for process in processes.values():
        if process.poll() is None:
            process.terminate()

    root.destroy()


root = tk.Tk()
root.title("Network Speed Test - Server")
root.geometry("600x450")

ip_address = get_ip_address()

title = tk.Label(
    root,
    text="Network Speed Test Server",
    font=("Arial", 20, "bold")
)

title.pack(pady=20)

ip_label = tk.Label(
    root,
    text=f"Your IP Address: {ip_address}",
    font=("Arial", 14)
)

ip_label.pack(pady=10)

refresh_button = tk.Button(
    root,
    text="Refresh IP",
    command=refresh_ip,
    width=20
)

refresh_button.pack(pady=5)

status_labels = {}

for port in servers:
    frame = tk.Frame(root)

    frame.pack(pady=10)

    start_button = tk.Button(
        frame,
        text=f"Start Server {port}",
        command=lambda p=port: start_server(p),
        width=20
    )

    start_button.pack(side="left", padx=5)

    stop_button = tk.Button(
        frame,
        text="Stop",
        command=lambda p=port: stop_server(p),
        width=10
    )

    stop_button.pack(side="left", padx=5)

    status_label = tk.Label(
        frame,
        text="Stopped",
        width=30
    )

    status_label.pack(side="left", padx=5)

    status_labels[port] = status_label

root.protocol("WM_DELETE_WINDOW", close_application)

root.mainloop()