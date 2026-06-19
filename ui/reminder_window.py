"""
提醒弹窗 - 置顶弹出，显示当前时段任务清单
"""
import tkinter as tk
from tkinter import font as tkfont


class ReminderWindow(tk.Toplevel):
    def __init__(self, parent, reminder_manager, task_manager, shift_index):
        super().__init__(parent)
        self.reminder_manager = reminder_manager
        self.task_manager = task_manager
        self.shift_index = shift_index
        self._countdown_id = None
        self._countdown_seconds = 0

        shift = task_manager.shifts[shift_index]
        self.title(f"提醒 - {shift['label']} ({shift['time']})")

        # 置顶设置
        self.attributes("-topmost", True)
        self.focus_force()

        # 窗口大小和居中
        self.geometry("420x380")
        self._center_window()

        # 不允许通过X按钮关闭（只能点"完成"）
        self.protocol("WM_DELETE_WINDOW", self._on_close_attempt)

        self._build_ui(shift)

    def _center_window(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"+{x}+{y}")

    def _build_ui(self, shift):
        # 标题区域
        title_frame = tk.Frame(self, bg="#FF6B6B", height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)

        title_label = tk.Label(
            title_frame,
            text=f"  {shift['label']}  ",
            font=tkfont.Font(size=18, weight="bold"),
            bg="#FF6B6B", fg="white"
        )
        title_label.pack(expand=True)

        time_label = tk.Label(
            title_frame,
            text=f"提醒时间: {shift['time']}",
            font=tkfont.Font(size=10),
            bg="#FF6B6B", fg="#FFE0E0"
        )
        time_label.pack(side=tk.BOTTOM, pady=(0, 5))

        # 倒计时标签（初始隐藏）
        self.countdown_label = tk.Label(
            self,
            text="",
            font=tkfont.Font(size=9),
            fg="#888888"
        )
        self.countdown_label.pack(fill=tk.X, padx=10, pady=(5, 0))

        # 任务列表区域
        task_frame = tk.Frame(self)
        task_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        tk.Label(
            task_frame, text="任务清单：",
            font=tkfont.Font(size=11, weight="bold"),
            anchor=tk.W
        ).pack(fill=tk.X)

        self._task_vars = []
        for i, task_text in enumerate(shift["tasks"]):
            var = tk.BooleanVar(value=shift["task_states"][i])
            cb = tk.Checkbutton(
                task_frame,
                text=task_text,
                variable=var,
                font=tkfont.Font(size=10),
                command=lambda idx=i, v=var: self._on_task_toggle(idx, v)
            )
            cb.pack(anchor=tk.W, padx=10, pady=2)
            self._task_vars.append(var)

        # 按钮区域
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=15, pady=(5, 15))

        ack_btn = tk.Button(
            btn_frame,
            text="知道了",
            font=tkfont.Font(size=11),
            bg="#4ECDC4", fg="white",
            activebackground="#45B7AA",
            width=10,
            command=self._on_acknowledge
        )
        ack_btn.pack(side=tk.LEFT, expand=True, padx=5)

        self.complete_btn = tk.Button(
            btn_frame,
            text="完成",
            font=tkfont.Font(size=11, weight="bold"),
            bg="#FF6B6B", fg="white",
            activebackground="#E55A5A",
            width=10,
            command=self._on_complete
        )
        self.complete_btn.pack(side=tk.LEFT, expand=True, padx=5)

        open_main_btn = tk.Button(
            btn_frame,
            text="打开主窗口",
            font=tkfont.Font(size=10),
            width=10,
            command=self._on_open_main
        )
        open_main_btn.pack(side=tk.LEFT, expand=True, padx=5)

        # 初始检查完成按钮状态
        self._update_complete_btn_state()

    def _on_task_toggle(self, task_index, var):
        """切换任务完成状态"""
        self.task_manager.toggle_task(self.shift_index, task_index)
        self._update_complete_btn_state()

    def _on_acknowledge(self):
        """点击"知道了"：停止声音，5分钟后再响"""
        self.reminder_manager.on_acknowledge(self.shift_index)

    def _on_complete(self):
        """点击"完成"：停止声音 + 关闭弹窗"""
        self.reminder_manager.on_complete(self.shift_index)

    def _on_open_main(self):
        """打开主窗口"""
        main_win = self.reminder_manager.root
        if main_win:
            main_win.deiconify()
            main_win.focus_force()
            main_window_attr = getattr(main_win, 'reminder_manager', None)
            if main_window_attr is None:
                # root 就是 MainWindow 本身
                pass

    def _update_complete_btn_state(self):
        """根据任务勾选状态更新完成按钮"""
        all_checked = all(v.get() for v in self._task_vars)
        if all_checked:
            self.complete_btn.config(state=tk.NORMAL)
        else:
            self.complete_btn.config(state=tk.DISABLED)

    def _on_close_attempt(self):
        """禁止直接关闭，提示用户点 完成"""
        pass  # 不做任何事，阻止关闭

    def start_countdown(self, seconds):
        """开始倒计时显示"""
        self._countdown_seconds = seconds
        self._update_countdown()

    def _update_countdown(self):
        """更新倒计时显示"""
        if self._countdown_seconds <= 0:
            self.countdown_label.config(text="")
            return
        minutes = self._countdown_seconds // 60
        secs = self._countdown_seconds % 60
        self.countdown_label.config(
            text=f"下次声音提醒: {minutes}:{secs:02d}"
        )
        self._countdown_seconds -= 1
        self._countdown_id = self.after(1000, self._update_countdown)

    def stop_countdown(self):
        """停止倒计时"""
        if self._countdown_id is not None:
            try:
                self.after_cancel(self._countdown_id)
            except Exception:
                pass
            self._countdown_id = None
        self.countdown_label.config(text="")

    def destroy(self):
        """重写destroy，清理倒计时"""
        self.stop_countdown()
        super().destroy()
