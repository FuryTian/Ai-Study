"""
AI Study Assistant Application
==============================

This script implements a minimal graphical prototype of the AI Study Assistant
outlined in the provided pitch deck. The goal of this prototype is not to
deliver a production‑ready mobile application but rather to demonstrate how
the core concepts—personalised study plans, focus reminders and simple
gamification—could be stitched together into a working program. The
implementation uses Python's built‑in `tkinter` library, which means the
application can run on most platforms without additional dependencies.

Key features:

* **Task management** – users can enter study tasks along with an estimated
  number of hours required and a due date. Tasks are stored in memory.

* **Automatic scheduling** – a basic scheduler allocates the required
  study time across the days leading up to each task's due date. Users can
  specify how many hours per day they are able to study, and the schedule
  distributes work accordingly.

* **Focus sessions** – inspired by Pomodoro timers, the focus session tool
  allows a user to start a timed study block. When the timer counts down to
  zero, the user is awarded points as part of a rudimentary gamification
  system.

* **Gamification** – each completed focus session awards points. A small
  scoreboard is displayed within the application window.

While this prototype uses simple algorithms and does not employ machine
learning, it reflects the core concepts described in the original deck:
personalised planning, focus reminders and gamified motivation. In a
full‑fledged version one might integrate calendar APIs, adaptive scheduling
models and robust user data storage; however, this simplified implementation
provides a solid foundation to build upon.
"""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from datetime import datetime, timedelta
import threading
import time


class Task:
    """Simple data structure to hold task information."""

    def __init__(self, name: str, hours: float, due_date: datetime):
        self.name = name
        self.hours = hours
        self.due_date = due_date
        self.completed_hours = 0.0

    @property
    def remaining_hours(self) -> float:
        """Return how many hours of work remain for this task."""
        return max(self.hours - self.completed_hours, 0.0)


class AiStudyApp(tk.Tk):
    """
    Main application class for the AI Study Assistant.

    This class manages the graphical user interface as well as the
    underlying data structures for tasks, schedules and gamification.
    """

    def __init__(self):
        super().__init__()
        self.title("AI Study Assistant")
        self.geometry("600x600")

        # Data
        self.tasks: list[Task] = []
        self.daily_hours: float | None = None
        self.schedule: list[tuple[str, str]] = []  # List of (date_str, task_description)
        self.focus_thread: threading.Thread | None = None
        self.timer_running: bool = False
        self.points: int = 0

        # Build UI
        self._build_widgets()

    def _build_widgets(self) -> None:
        """Set up all the GUI components."""
        # Top frame for task entry
        entry_frame = ttk.Frame(self)
        entry_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(entry_frame, text="任务名称:").grid(row=0, column=0, sticky="w")
        self.task_name_var = tk.StringVar()
        ttk.Entry(entry_frame, textvariable=self.task_name_var, width=20).grid(row=0, column=1)

        ttk.Label(entry_frame, text="预估小时数:").grid(row=0, column=2, sticky="w")
        self.task_hours_var = tk.StringVar()
        ttk.Entry(entry_frame, textvariable=self.task_hours_var, width=10).grid(row=0, column=3)

        ttk.Label(entry_frame, text="截止日期 (YYYY-MM-DD):").grid(row=0, column=4, sticky="w")
        self.task_due_var = tk.StringVar()
        ttk.Entry(entry_frame, textvariable=self.task_due_var, width=12).grid(row=0, column=5)

        add_button = ttk.Button(entry_frame, text="添加任务", command=self.add_task)
        add_button.grid(row=0, column=6, padx=5)

        # Middle frame for task list and schedule
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        ttk.Label(list_frame, text="任务列表:").pack(anchor="w")
        self.task_listbox = tk.Listbox(list_frame, height=8)
        self.task_listbox.pack(fill="x")

        ttk.Label(list_frame, text="生成的学习计划:").pack(anchor="w", pady=(10, 0))
        self.schedule_text = tk.Text(list_frame, height=10)
        self.schedule_text.pack(fill="both", expand=True)

        # Bottom frame for controls
        control_frame = ttk.Frame(self)
        control_frame.pack(fill="x", padx=10, pady=10)

        generate_button = ttk.Button(control_frame, text="生成学习计划", command=self.generate_schedule)
        generate_button.grid(row=0, column=0, padx=5)

        focus_button = ttk.Button(control_frame, text="开始专注学习", command=self.start_focus_session)
        focus_button.grid(row=0, column=1, padx=5)

        self.points_label = ttk.Label(control_frame, text="积分: 0")
        self.points_label.grid(row=0, column=2, padx=5)

        # Timer display
        self.timer_label = ttk.Label(control_frame, text="")
        self.timer_label.grid(row=0, column=3, padx=5)

    def add_task(self) -> None:
        """Add a new task based on the user's input."""
        name = self.task_name_var.get().strip()
        hours_str = self.task_hours_var.get().strip()
        due_str = self.task_due_var.get().strip()

        if not name or not hours_str or not due_str:
            messagebox.showwarning("输入不完整", "请填写所有字段。")
            return
        try:
            hours = float(hours_str)
        except ValueError:
            messagebox.showwarning("格式错误", "预估小时数必须为数字。")
            return
        try:
            due_date = datetime.strptime(due_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("日期错误", "截止日期格式应为 YYYY-MM-DD。")
            return

        task = Task(name, hours, due_date)
        self.tasks.append(task)
        self.task_listbox.insert(tk.END, f"{task.name} - {task.hours}小时 - 截止: {task.due_date.strftime('%Y-%m-%d')}")
        # Clear fields
        self.task_name_var.set("")
        self.task_hours_var.set("")
        self.task_due_var.set("")

    def generate_schedule(self) -> None:
        """Generate a naive study schedule for the existing tasks."""
        if not self.tasks:
            messagebox.showinfo("提示", "请先添加任务。")
            return

        # Ask for daily study hours if not set
        if self.daily_hours is None:
            answer = simpledialog.askstring("每日学习时间", "请输入您每天可用的学习时间（小时，例如 2 或 3.5）:")
            if answer is None:
                return  # User cancelled
            try:
                self.daily_hours = float(answer)
                if self.daily_hours <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("输入错误", "请输入有效的小时数。")
                self.daily_hours = None
                return

        # Prepare schedule list
        self.schedule.clear()

        # Sort tasks by due date
        tasks_sorted = sorted(self.tasks, key=lambda t: t.due_date)
        today = datetime.today().date()

        for task in tasks_sorted:
            total_days = (task.due_date.date() - today).days + 1
            if total_days <= 0:
                total_days = 1  # If due date is today or past, allocate all work today
            daily_allocation = task.remaining_hours / total_days
            # For each day until due date, allocate hours
            current_date = today
            while current_date <= task.due_date.date():
                hours_today = min(daily_allocation, self.daily_hours)
                self.schedule.append((current_date.strftime("%Y-%m-%d"), f"{task.name}: {hours_today:.2f}h"))
                current_date += timedelta(days=1)

        # Populate schedule_text
        self.schedule_text.delete("1.0", tk.END)
        if not self.schedule:
            self.schedule_text.insert(tk.END, "没有安排。")
        else:
            # Group schedule entries by date for clearer display
            grouped: dict[str, list[str]] = {}
            for date_str, desc in self.schedule:
                grouped.setdefault(date_str, []).append(desc)
            for date_str in sorted(grouped.keys()):
                self.schedule_text.insert(tk.END, f"{date_str}:\n")
                for d in grouped[date_str]:
                    self.schedule_text.insert(tk.END, f"  - {d}\n")
                self.schedule_text.insert(tk.END, "\n")

    def _countdown(self, seconds: int) -> None:
        """Run a countdown timer in a separate thread."""
        start_time = time.time()
        end_time = start_time + seconds
        while self.timer_running and time.time() < end_time:
            remaining = int(end_time - time.time())
            mins, secs = divmod(remaining, 60)
            time_str = f"剩余: {mins:02d}:{secs:02d}"
            self.timer_label.config(text=time_str)
            time.sleep(1)
        if self.timer_running:
            # Countdown finished normally
            self.timer_label.config(text="专注完成！")
            self.points += 10
            self.points_label.config(text=f"积分: {self.points}")
        # Reset flag
        self.timer_running = False

    def start_focus_session(self) -> None:
        """Initiate a focus session with a user‑specified duration."""
        if self.timer_running:
            messagebox.showinfo("提示", "已经在专注学习中。")
            return

        answer = simpledialog.askstring("专注时长", "请输入专注学习的时长（分钟，例如 25）:")
        if answer is None:
            return
        try:
            minutes = int(answer)
            if minutes <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的分钟数。")
            return

        seconds = minutes * 60
        self.timer_running = True
        # Start countdown in a separate thread to avoid blocking the UI
        self.focus_thread = threading.Thread(target=self._countdown, args=(seconds,), daemon=True)
        self.focus_thread.start()


if __name__ == "__main__":
    app = AiStudyApp()
    app.mainloop()
