
import tkinter as tk
from tkinter import ttk
import json
import urllib.request
import urllib.error

API_URL = "http://127.0.0.1:5000/results"
REFRESH_INTERVAL = 5000  # 5 seconds

root = tk.Tk()
root.title("Mini-Ookla - Results Dashboard")
root.geometry("1100x600")
root.minsize(900, 450)

# ---------- Heading ----------

heading = tk.Label(
    root,
    text="Mini-Ookla Results Dashboard",
    font=("Arial", 20, "bold")
)
heading.pack(pady=12)

status_label = tk.Label(
    root,
    text="Connecting to API...",
    font=("Arial", 10),
    fg="gray"
)
status_label.pack()

# ---------- Latest Results ----------

summary_frame = tk.LabelFrame(
    root,
    text="Latest Test Results",
    font=("Arial", 11, "bold"),
    padx=10,
    pady=10
)
summary_frame.pack(fill="x", padx=15, pady=10)

summary_labels = {}

summary_fields = [
    ("download_mbps", "Download (Mbps)"),
    ("upload_mbps", "Upload (Mbps)"),
    ("latency_ms", "Latency (ms)"),
    ("jitter_ms", "Jitter (ms)"),
    ("packet_loss_percent", "Packet Loss (%)")
]

for column, (field, title) in enumerate(summary_fields):
    frame = tk.Frame(summary_frame, padx=10, pady=5)
    frame.grid(row=0, column=column, sticky="nsew")

    tk.Label(
        frame,
        text=title,
        font=("Arial", 10)
    ).pack()

    value_label = tk.Label(
        frame,
        text="--",
        font=("Arial", 16, "bold")
    )
    value_label.pack(pady=5)

    summary_labels[field] = value_label
    summary_frame.grid_columnconfigure(column, weight=1)

# ---------- Results Table ----------

table_frame = tk.LabelFrame(
    root,
    text="Test History",
    font=("Arial", 11, "bold")
)
table_frame.pack(fill="both", expand=True, padx=15, pady=5)

columns = (
    "id",
    "server_id",
    "download_mbps",
    "upload_mbps",
    "latency_ms",
    "jitter_ms",
    "packet_loss_percent",
    "streams",
    "duration_sec",
    "timestamp"
)

table = ttk.Treeview(
    table_frame,
    columns=columns,
    show="headings"
)

column_titles = {
    "id": "ID",
    "server_id": "Server",
    "download_mbps": "Download",
    "upload_mbps": "Upload",
    "latency_ms": "Latency",
    "jitter_ms": "Jitter",
    "packet_loss_percent": "Packet Loss",
    "streams": "Streams",
    "duration_sec": "Duration (s)",
    "timestamp": "Timestamp"
}

column_widths = {
    "id": 45,
    "server_id": 85,
    "download_mbps": 90,
    "upload_mbps": 90,
    "latency_ms": 75,
    "jitter_ms": 75,
    "packet_loss_percent": 90,
    "streams": 65,
    "duration_sec": 85,
    "timestamp": 155
}

for column in columns:
    table.heading(column, text=column_titles[column])
    table.column(
        column,
        width=column_widths[column],
        minwidth=45,
        anchor="center"
    )

vertical_scrollbar = ttk.Scrollbar(
    table_frame,
    orient="vertical",
    command=table.yview
)

horizontal_scrollbar = ttk.Scrollbar(
    table_frame,
    orient="horizontal",
    command=table.xview
)

table.configure(
    yscrollcommand=vertical_scrollbar.set,
    xscrollcommand=horizontal_scrollbar.set
)

table.grid(row=0, column=0, sticky="nsew")
vertical_scrollbar.grid(row=0, column=1, sticky="ns")
horizontal_scrollbar.grid(row=1, column=0, sticky="ew")

table_frame.grid_rowconfigure(0, weight=1)
table_frame.grid_columnconfigure(0, weight=1)

# ---------- Buttons ----------

button_frame = tk.Frame(root)
button_frame.pack(pady=10)

refresh_button = tk.Button(
    button_frame,
    text="Refresh Results",
    width=18,
    command=lambda: refresh_results(True)
)
refresh_button.pack(side="left", padx=5)

# ---------- Data Handling ----------

def format_value(value):
    if value is None:
        return "--"

    if isinstance(value, float):
        return f"{value:.2f}"

    return str(value)


def get_result_list(data):
    """Accept common JSON response formats from the API."""
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        if isinstance(data.get("results"), list):
            return data["results"]

        if isinstance(data.get("data"), list):
            return data["data"]

        # Handle a response containing one result
        if "server_id" in data:
            return [data]

    return []


def refresh_results(manual=False):
    """Fetch results from the Flask API."""
    try:
        request = urllib.request.Request(
            API_URL,
            headers={"Accept": "application/json"}
        )

        with urllib.request.urlopen(request, timeout=3) as response:
            data = json.loads(response.read().decode("utf-8"))

        results = get_result_list(data)

        # Clear the old table
        for item in table.get_children():
            table.delete(item)

        # Insert the latest API response
        for result in results:
            values = [
                result.get("id", ""),
                result.get("server_id", ""),
                format_value(result.get("download_mbps")),
                format_value(result.get("upload_mbps")),
                format_value(result.get("latency_ms")),
                format_value(result.get("jitter_ms")),
                format_value(result.get("packet_loss_percent")),
                result.get("streams", ""),
                result.get("duration_sec", ""),
                result.get("timestamp", "")
            ]

            table.insert("", "end", values=values)

        # Update the summary using the first returned result
        if results:
            latest = results[0]

            for field, label in summary_labels.items():
                label.config(
                    text=format_value(latest.get(field))
                )

            status_label.config(
                text=f"Connected | {len(results)} result(s) loaded",
                fg="green"
            )
        else:
            for label in summary_labels.values():
                label.config(text="--")

            status_label.config(
                text="Connected | No results returned by API",
                fg="orange"
            )

    except (urllib.error.URLError, TimeoutError, OSError) as error:
        status_label.config(
            text="API unavailable. Start the API and refresh.",
            fg="red"
        )

    except (json.JSONDecodeError, TypeError, ValueError):
        status_label.config(
            text="Could not read the API response. Check its JSON format.",
            fg="red"
        )

    except Exception as error:
        status_label.config(
            text=f"Error: {error}",
            fg="red"
        )

    # Schedule the next automatic refresh
    root.after(REFRESH_INTERVAL, refresh_results)


root.after(500, refresh_results)
root.mainloop()
