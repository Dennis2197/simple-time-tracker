import tkinter as tk
from tkinter import ttk
import datetime
from db import (
    init_db,
    add_session,
    stop_session,
    fetch_sessions,
    fetch_daily_totals,
    get_background_color,
)
from time_utils import format_datetime, format_duration
from ui_modals import (
    open_edit_modal,
    confirm_delete,
    open_all_sessions_window,
    open_all_daily_totals_window,
    open_settings_window,
)


import os, sys


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    try:
        base_path = sys._MEIPASS  # PyInstaller's temporary folder
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# Simple tooltip class for showing text on hover
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x, y, _, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 25
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # no window decorations
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("tahoma", "8", "normal"),
        )
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


class TimeTrackerApp:
    def __init__(self, root):
        init_db()
        self.root = root
        self.root.title("Clocker")
        self.root.geometry("1080x720")
        self.root.resizable(True, True)
        self.root.configure(background=get_background_color())

        self.start_icon = tk.PhotoImage(file=resource_path("icons/start.png"))
        self.stop_icon = tk.PhotoImage(file=resource_path("icons/stop.png"))
        self.refresh_icon = tk.PhotoImage(file=resource_path("icons/refresh.png"))
        self.view_icon = tk.PhotoImage(file=resource_path("icons/view.png"))
        self.settings_icon = tk.PhotoImage(file=resource_path("icons/settings.png"))

        style = ttk.Style()
        style.configure("btn.TFrame", background=get_background_color())

        btn_frame = ttk.Frame(root, style="btn.TFrame")
        btn_frame.pack()

        self.start_button = ttk.Button(
            btn_frame,
            image=self.start_icon,
            command=self.start_tracking,
            width=5,
            compound="left",
        )
        self.start_button.grid(row=0, column=0, padx=5)
        ToolTip(self.start_button, "Start")

        self.stop_button = ttk.Button(
            btn_frame,
            image=self.stop_icon,
            command=self.stop_tracking,
            width=5,
            state=tk.DISABLED,
            compound="left",
        )
        self.stop_button.grid(row=0, column=1, padx=5, pady=15, ipady=0, ipadx=0)
        ToolTip(self.stop_button, "Stop")

        self.refresh_button = ttk.Button(
            btn_frame,
            image=self.refresh_icon,
            command=self.refresh_all,
            width=5,
            compound="left",
        )
        self.refresh_button.grid(row=0, column=2, padx=5)
        ToolTip(self.refresh_button, "Refresh")

        self.view_all_button = ttk.Button(
            btn_frame,
            image=self.view_icon,
            command=lambda: open_all_sessions_window(self.root),
            width=5,
            compound="left",
        )
        self.view_all_button.grid(row=0, column=3, padx=5)
        ToolTip(self.view_all_button, "View All Sessions")

        self.settings_button = ttk.Button(
            btn_frame,
            image=self.settings_icon,
            command=lambda: open_settings_window(self.root, style),
            width=0,
            compound="left",
        )
        self.settings_button.grid(row=0, column=4, padx=5, pady=0, ipadx=5)
        ToolTip(self.settings_button, "Open Settings")

        # --- Live Timer ---
        self.timer_label = ttk.Label(
            root, text="00:00:00", font=("Helvetica", 18, "bold")
        )
        self.timer_label.pack(pady=10)

        # --- Sessions Table ---
        ttk.Label(root, text="Tracked Sessions", font=("Helvetica", 12, "bold")).pack()
        self.tree = ttk.Treeview(
            root,
            columns=("id", "start_time", "end_time", "actions"),
            show="headings",
            height=8,
        )
        for col, name in zip(
            ("id", "start_time", "end_time", "actions"),
            ["ID", "Start Time", "End Time", "Actions"],
        ):
            self.tree.heading(col, text=name)
        self.tree.column("id", width=40, anchor="center")
        self.tree.column("start_time", width=230)
        self.tree.column("end_time", width=230)
        self.tree.column("actions", width=120, anchor="center")
        self.tree.pack(pady=5)

        # --- Daily Totals ---
        daily_label_frame = ttk.Frame(root, style="btn.TFrame")
        daily_label_frame.pack(pady=5)
        ttk.Label(
            daily_label_frame, text="Daily Totals", font=("Helvetica", 12, "bold")
        ).grid(row=0, column=0)
        ttk.Button(
            daily_label_frame,
            text="View All",
            command=lambda: open_all_daily_totals_window(self.root),
        ).grid(row=0, column=1, padx=10)

        self.daily_tree = ttk.Treeview(
            root, columns=("date", "total"), show="headings", height=4
        )
        self.daily_tree.heading("date", text="Date (DD.MM.YYYY)")
        self.daily_tree.heading("total", text="Total Time")
        self.daily_tree.column("date", width=150, anchor="center")
        self.daily_tree.column("total", width=100, anchor="center")
        self.daily_tree.pack(pady=5)

        # --- Snackbar / Status ---
        self.status_label = ttk.Label(root, text="", relief="sunken", anchor="w")
        self.status_label.pack(fill=tk.X, side=tk.BOTTOM, ipady=2)

        # Bind actions
        self.tree.bind("<Double-1>", self.handle_table_click)

        self.is_tracking = False
        self.start_time = None

        self.check_running_session()
        self.refresh_all()

    def check_running_session(self):
        # Look for a session with no end time:
        sessions = fetch_sessions()
        for sid, start, end in sessions:
            if end is None or end == "":
                # Resume tracking this session
                import datetime

                self.is_tracking = True
                self.start_time = datetime.datetime.fromisoformat(start)
                self.start_button.config(state=tk.DISABLED)
                self.stop_button.config(state=tk.NORMAL)
                self.update_timer()
                self.show_snackbar(
                    f"Resumed session started at {self.start_time.strftime('%H:%M:%S')}"
                )
                break

    def start_tracking(self):
        if self.is_tracking:
            self.show_snackbar("Already tracking.")
            return

        self.start_time = datetime.datetime.now()
        add_session(self.start_time.isoformat())
        self.is_tracking = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.update_timer()
        self.show_snackbar(f"Started at {self.start_time.strftime('%H:%M:%S')}")

    def stop_tracking(self):
        if not self.is_tracking:
            self.show_snackbar("No active tracking.")
            return

        end_time = datetime.datetime.now()
        stop_session(end_time.isoformat())
        self.is_tracking = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.timer_label.config(text="00:00:00")
        self.show_snackbar(f"Stopped at {end_time.strftime('%H:%M:%S')}")
        self.refresh_all()

    def refresh_all(self):
        self.load_sessions()
        self.load_daily_totals()

    def load_sessions(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for sid, start, end in fetch_sessions()[:10]:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    sid,
                    format_datetime(start),
                    format_datetime(end),
                    "✏ Edit   🗑 Delete",
                ),
            )

    def load_daily_totals(self):
        for row in self.daily_tree.get_children():
            self.daily_tree.delete(row)
        for date, total in sorted(fetch_daily_totals().items(), reverse=True)[:5]:
            self.daily_tree.insert("", tk.END, values=(date, format_duration(total)))

    def handle_table_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        col = self.tree.identify_column(event.x)
        values = self.tree.item(item, "values")
        session_id = values[0]
        if col == "#4":
            x_offset = event.x - self.tree.bbox(item, "actions")[0]
            if x_offset < 60:
                open_edit_modal(self.root, session_id, self.refresh_all)
            else:
                confirm_delete(self.root, session_id, self.refresh_all)

    def show_snackbar(self, message):
        self.status_label.config(text=message)
        self.root.after(3000, lambda: self.status_label.config(text=""))

    def update_timer(self):
        if self.is_tracking and self.start_time:
            elapsed = datetime.datetime.now() - self.start_time
            self.timer_label.config(text=format_duration(elapsed.total_seconds()))
            self.root.after(1000, self.update_timer)
