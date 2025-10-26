import tkinter as tk
from tkinter import ttk, messagebox
import datetime
from db import (
    fetch_sessions,
    update_session,
    delete_session,
    delete_sessions_by_day,
    get_background_color,
    get_daily_goal,
    get_weekly_goal,
    update_settings,
)
from time_utils import format_datetime, format_duration
import re


# -------------------------
# Edit Session Modal
# -------------------------
def open_edit_modal(parent, session_id, refresh_callback):
    import sqlite3
    from db import DB_FILE
    import tkinter as tk
    from tkinter import ttk, messagebox
    import datetime

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT start_time, end_time FROM sessions WHERE id=?", (session_id,))
    result = c.fetchone()
    conn.close()
    if not result:
        return
    start_time, end_time = result

    # Helper to cleanly format datetime strings without microseconds
    def format_dt(iso_str):
        if not iso_str:
            return ""
        dt = datetime.datetime.fromisoformat(iso_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    win = tk.Toplevel(parent)
    win.title("Edit Session")
    win.geometry("350x200")
    win.resizable(False, False)

    ttk.Label(win, text="Start Time (YYYY-MM-DD HH:MM:SS)").pack(pady=5)
    start_entry = ttk.Entry(win, width=30)
    start_entry.insert(0, format_dt(start_time))
    start_entry.pack()

    ttk.Label(win, text="End Time (YYYY-MM-DD HH:MM:SS or empty)").pack(pady=5)
    end_entry = ttk.Entry(win, width=30)
    end_entry.insert(0, format_dt(end_time))
    end_entry.pack()

    def save_changes():
        try:
            new_start_str = start_entry.get().strip()
            new_end_str = end_entry.get().strip()

            new_start = datetime.datetime.strptime(new_start_str, "%Y-%m-%d %H:%M:%S")
            new_end = None
            if new_end_str:
                new_end = datetime.datetime.strptime(new_end_str, "%Y-%m-%d %H:%M:%S")

            # Validate that start < end if end provided
            if new_end and new_start >= new_end:
                messagebox.showerror(
                    "Invalid Time", "Start time must be before end time."
                )
                return

            update_session(
                session_id,
                new_start.isoformat(),
                new_end.isoformat() if new_end else None,
            )
            win.destroy()
            refresh_callback()
        except ValueError:
            messagebox.showerror(
                "Invalid Format",
                "Please enter date/time in YYYY-MM-DD HH:MM:SS format.",
            )

    ttk.Button(win, text="Save", command=save_changes).pack(pady=10)


# -------------------------
# Confirm Delete Modal
# -------------------------
def confirm_delete(parent, session_id, refresh_callback):
    confirm = tk.Toplevel(parent)
    confirm.title("Confirm Delete")
    confirm.geometry("300x130")
    confirm.resizable(False, False)

    ttk.Label(
        confirm, text="Are you sure you want to delete this entry?", wraplength=280
    ).pack(pady=10)

    btns = ttk.Frame(confirm)
    btns.pack(pady=10)
    ttk.Button(btns, text="Cancel", command=confirm.destroy).grid(
        row=0, column=0, padx=5
    )
    ttk.Button(
        btns,
        text="Delete",
        command=lambda: _delete_and_refresh(session_id, confirm, refresh_callback),
    ).grid(row=0, column=1, padx=5)


def _delete_and_refresh(session_id, modal, refresh_callback):
    delete_session(session_id)
    modal.destroy()
    refresh_callback()


# -------------------------
# View All Sessions Window
# -------------------------
def open_all_sessions_window(parent):
    win = tk.Toplevel(parent)
    win.title("All Sessions")
    win.geometry("720x420")

    ttk.Label(win, text="All Sessions", font=("Helvetica", 12, "bold")).pack(pady=5)

    frame = ttk.Frame(win)
    frame.pack(fill="both", expand=True)

    cols = ("id", "start_time", "end_time", "actions")
    tree = ttk.Treeview(frame, columns=cols, show="headings")
    for col, name in zip(cols, ["ID", "Start Time", "End Time", "Actions"]):
        tree.heading(col, text=name)
    tree.column("id", width=40, anchor="center")
    tree.column("start_time", width=230)
    tree.column("end_time", width=230)
    tree.column("actions", width=120, anchor="center")

    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)

    def refresh():
        for row in tree.get_children():
            tree.delete(row)
        for sid, start, end in fetch_sessions():
            tree.insert(
                "",
                tk.END,
                values=(
                    sid,
                    format_datetime(start),
                    format_datetime(end),
                    "✏ Edit   🗑 Delete",
                ),
            )

    def on_click(event):
        item = tree.identify_row(event.y)
        if not item:
            return
        col = tree.identify_column(event.x)
        values = tree.item(item, "values")
        session_id = values[0]
        if col == "#4":
            x_offset = event.x - tree.bbox(item, "actions")[0]
            if x_offset < 60:
                open_edit_modal(win, session_id, refresh)
            else:
                confirm_delete(win, session_id, refresh)

    tree.bind("<Double-1>", on_click)
    refresh()


# -------------------------
# Settings Window
# -------------------------
def open_settings_window(parent, style):
    win = tk.Toplevel(parent)
    win.title("Settings")
    win.geometry("720x420")
    win.configure(background=get_background_color())

    frame = ttk.Frame(win)
    style = ttk.Style()
    style.configure("TFrame", background=get_background_color())
    frame.pack(fill="both", expand=True)

    def validate_daily_hours(value):
        # Validate 0-24, supports float
        if not value:
            save_button.config(state=tk.DISABLED)
            return True
        pattern = r"^(?:24(?:\.0+)?|(?:[0-9]|1[0-9]|2[0-3])(?:\.\d+)?|0?\.\d+)$"
        if re.fullmatch(pattern, value) is None:
            save_button.config(state=tk.DISABLED)
            return False
        save_button.config(state=tk.ACTIVE)
        return True

    def validate_weekly_hours(value):
        # Validate 0-40, supports float
        if not value:
            save_button.config(state=tk.DISABLED)
            return True
        pattern = r"^(?:40(?:\.0+)?|(?:[0-9]|1[0-9]|2[0-9]|3[0-9])(?:\.\d+)?|0?\.\d+)$"
        if re.fullmatch(pattern, value) is None:
            save_button.config(state=tk.DISABLED)
            return False
        save_button.config(state=tk.ACTIVE)
        return True

    def on_cancel():
        win.destroy()
        win.update()

    def validate_hex_color(value):
        pattern = r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"
        if re.fullmatch(pattern, value):
            return True
        return False

    def validate_color_string(value):
        try:
            tk.Color(value)  # Done by ChatGPT, needs to be tested carefully
            return True
        except tk.TclError:
            return False

    def validate_hours_on_save(weekly, daily):
        try:
            return float(daily if daily else get_daily_goal()) <= float(
                weekly if weekly else get_weekly_goal()
            )
        except Exception as e:
            print("Error occured validating hours", e)
            return False

    def on_save():
        updated_background = new_color.get() or None
        updated_weekly_goal = new_weekly.get() or None
        updated_daily_goal = new_daily.get() or None
        save_new_color = False
        save_new_weekly = False
        save_new_daily = False

        if updated_background and updated_background.startswith("#"):
            save_new_color = validate_hex_color(updated_background)
        elif updated_background:
            save_new_color = validate_color_string()

        if updated_weekly_goal:
            save_new_weekly = validate_hours_on_save(
                updated_weekly_goal, updated_daily_goal
            )

        if updated_daily_goal:
            save_new_daily = validate_hours_on_save(
                updated_daily_goal, updated_weekly_goal
            )

        # Create Fallbacks for each setting to not overwrite current settings in case of no valid values
        if not save_new_color:
            updated_background = get_background_color()

        if not save_new_weekly:
            updated_weekly_goal = get_weekly_goal()

        if not save_new_daily:
            updated_daily_goal = get_daily_goal()

        if save_new_color or save_new_weekly or save_new_daily:
            update_settings(
                updated_background,
                updated_weekly_goal,
                updated_daily_goal,
            )

        win.destroy()
        win.update()
        parent.configure(background=get_background_color())
        style.configure("btn.TFrame", background=get_background_color())

    background_label = ttk.Label(frame, text="Current Background Color: ")
    background_label.grid(row=0, column=0, padx=5, pady=10)
    background_value_label = ttk.Label(frame, text=get_background_color())
    background_value_label.grid(row=0, column=1, padx=5)
    new_background_label = ttk.Label(frame, text="Enter new Color: ")
    new_background_label.grid(row=0, column=2, padx=10)
    new_color = ttk.Entry(frame)
    new_color.grid(row=0, column=3, padx=5)

    weekly_label = ttk.Label(frame, text="Current Weekly Goal (h): ")
    weekly_label.grid(row=1, column=0, padx=5, pady=10)
    weekly_value_label = ttk.Label(frame, text=get_weekly_goal())
    weekly_value_label.grid(row=1, column=1, padx=5)
    new_weekly_label = ttk.Label(frame, text="Enter new Goal: ")
    new_weekly_label.grid(row=1, column=2, padx=10)
    validate_weekly = (win.register(validate_weekly_hours), "%P")
    new_weekly = ttk.Entry(frame, validate="key", validatecommand=validate_weekly)
    new_weekly.grid(row=1, column=3, padx=5)

    daily_label = ttk.Label(frame, text="Current Daily Goal (h): ")
    daily_label.grid(row=2, column=0, padx=5, pady=10)
    daily_value_label = ttk.Label(frame, text=get_daily_goal())
    daily_value_label.grid(row=2, column=1, padx=5)
    new_daily_label = ttk.Label(frame, text="Enter new Goal: ")
    new_daily_label.grid(row=2, column=2, padx=10)
    validate_daily = (win.register(validate_daily_hours), "%P")
    new_daily = ttk.Entry(
        frame,
        validate="key",
        validatecommand=validate_daily,
    )
    new_daily.grid(row=2, column=3, padx=5)

    style = ttk.Style()
    style.configure("Blue.TButton", background="#3487FF")
    style.map("Blue.TButton", background=[("active", "#00A2E8")])

    cancel_button = ttk.Button(frame, text="Cancel", command=on_cancel)
    cancel_button.grid(row=3, column=0, padx=10, pady=20)
    restore_button = ttk.Button(frame, text="Restore defaults")
    restore_button.grid(row=3, column=1, padx=10)
    save_button = ttk.Button(
        frame, text="Save", default="disabled", command=on_save, style="Blue.TButton"
    )
    save_button.grid(row=3, column=2, padx=10)


# -------------------------
# View All Daily Totals Window
# -------------------------
def open_all_daily_totals_window(parent):
    from db import fetch_daily_totals

    win = tk.Toplevel(parent)
    win.title("All Daily Totals")
    win.geometry("500x400")

    ttk.Label(win, text="All Daily Totals", font=("Helvetica", 12, "bold")).pack(pady=5)

    frame = ttk.Frame(win)
    frame.pack(fill="both", expand=True)

    cols = ("date", "total", "actions")
    tree = ttk.Treeview(frame, columns=cols, show="headings")
    for col, name in zip(cols, ["Date (DD.MM.YYYY)", "Total", "Actions"]):
        tree.heading(col, text=name)
    tree.column("date", width=150, anchor="center")
    tree.column("total", width=120, anchor="center")
    tree.column("actions", width=120, anchor="center")

    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)

    def refresh():
        for row in tree.get_children():
            tree.delete(row)
        for date, total in sorted(fetch_daily_totals().items(), reverse=True):
            tree.insert(
                "", tk.END, values=(date, format_duration(total), "🗑 Delete All")
            )

    def on_click(event):
        item = tree.identify_row(event.y)
        if not item:
            return
        col = tree.identify_column(event.x)
        if col == "#3":
            values = tree.item(item, "values")
            date_str = values[0]
            if messagebox.askyesno(
                "Confirm Delete", f"Delete all entries for {date_str}?"
            ):
                # convert DD.MM.YYYY → YYYY-MM-DD
                d = datetime.datetime.strptime(date_str, "%d.%m.%Y").strftime(
                    "%Y-%m-%d"
                )
                delete_sessions_by_day(d)
                refresh()

    tree.bind("<Double-1>", on_click)
    refresh()
