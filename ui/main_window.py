"""
主窗口 - 展示所有时段的任务总览
"""
import tkinter as tk
from tkinter import font as tkfont, messagebox, simpledialog
from datetime import datetime


class MainWindow(tk.Tk):
    def __init__(self, task_manager, reminder_manager, on_quit_callback=None):
        super().__init__()
        self.task_manager = task_manager
        self.reminder_manager = reminder_manager
        self.on_quit_callback = on_quit_callback
        self._on_quit_callback = on_quit_callback  # 供 reminder_manager 调用

        self.title("值班闹钟")
        self.geometry("480x520")
        self.minsize(400, 400)

        # 关闭按钮最小化到托盘
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._start_clock_update()

    def _build_ui(self):
        # 顶部标题栏
        header = tk.Frame(self, bg="#2C3E50", height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(
            header, text="值班闹钟 - 任务总览",
            font=tkfont.Font(size=16, weight="bold"),
            bg="#2C3E50", fg="white"
        ).pack(side=tk.LEFT, padx=15)

        self.clock_label = tk.Label(
            header, text="",
            font=tkfont.Font(size=12),
            bg="#2C3E50", fg="#BDC3C7"
        )
        self.clock_label.pack(side=tk.RIGHT, padx=15)

        # 可滚动区域
        container = tk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self._canvas_window = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor=tk.NW)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # 让 scroll_frame 宽度跟随 canvas 宽度
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self._canvas_window, width=e.width)
        )

        # 绑定鼠标滚轮
        self.canvas.bind("<Enter>", lambda e: self._bind_mousewheel())
        self.canvas.bind("<Leave>", lambda e: self._unbind_mousewheel())

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 为每个时段创建卡片
        self._shift_widgets = []
        for i, shift in enumerate(self.task_manager.shifts):
            frame = self._create_shift_card(self.scroll_frame, shift, i)
            frame.pack(fill=tk.X, padx=5, pady=3)
            self._shift_widgets.append(frame)

        # 底部状态栏
        status_frame = tk.Frame(self, bg="#ECF0F1", height=30)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        status_frame.pack_propagate(False)

        self.status_label = tk.Label(
            status_frame, text="",
            font=tkfont.Font(size=9),
            bg="#ECF0F1", fg="#7F8C8D"
        )
        self.status_label.pack(side=tk.LEFT, padx=10)
        self._update_status()

    def _create_shift_card(self, parent, shift, shift_index):
        """创建单个时段的任务卡片"""
        is_completed = shift.get("completed", False)
        is_reminded = shift.get("reminded", False)
        is_next_day = shift.get("next_day", False)

        # 卡片边框颜色
        if is_completed:
            border_color = "#27AE60"
        elif is_reminded:
            border_color = "#E67E22"
        else:
            border_color = "#3498DB"

        card = tk.Frame(parent, bg=border_color, padx=2, pady=2)
        inner = tk.Frame(card, bg="white")
        inner.pack(fill=tk.BOTH, expand=True)

        # 标题行
        title_row = tk.Frame(inner, bg="white")
        title_row.pack(fill=tk.X, padx=8, pady=(5, 2))

        day_label = " (次日)" if is_next_day else ""
        status_icon = " [已完成]" if is_completed else (" [已提醒]" if is_reminded else "")
        tk.Label(
            title_row,
            text=f"{shift['label']}{day_label} - {shift['time']}{status_icon}",
            font=tkfont.Font(size=11, weight="bold"),
            bg="white", fg=border_color
        ).pack(side=tk.LEFT)

        # 添加任务按钮
        add_btn = tk.Button(
            title_row, text="+", font=tkfont.Font(size=10, weight="bold"),
            width=3, bg="white", fg="#27AE60", bd=0,
            activebackground="#F0F0F0",
            command=lambda idx=shift_index: self._add_task(idx)
        )
        add_btn.pack(side=tk.RIGHT)

        # 任务列表
        task_frame = tk.Frame(inner, bg="white")
        task_frame.pack(fill=tk.X, padx=8, pady=(0, 5))

        task_widgets = []
        for j, task_text in enumerate(shift["tasks"]):
            row = self._create_task_row(task_frame, shift_index, j, task_text, shift["task_states"][j])
            row.pack(fill=tk.X)
            task_widgets.append(row)

        # 保存引用以便后续更新
        card._task_frame = task_frame
        card._task_widgets = task_widgets
        card._inner = inner
        card._border_color = border_color

        return card

    def _create_task_row(self, parent, shift_index, task_index, task_text, is_done):
        """创建单行任务"""
        row = tk.Frame(parent, bg="white")

        var = tk.BooleanVar(value=is_done)
        fg_color = "#95A5A6" if is_done else "#2C3E50"
        font_opts = {"size": 10}
        if is_done:
            font_opts["overstrike"] = True

        cb = tk.Checkbutton(
            row, variable=var,
            command=lambda: self._on_task_toggle(shift_index, task_index, var, task_label)
        )
        cb.pack(side=tk.LEFT)

        task_label = tk.Label(
            row, text=task_text,
            font=tkfont.Font(**font_opts),
            fg=fg_color, bg="white"
        )
        task_label.pack(side=tk.LEFT, padx=5)

        # 右键菜单
        menu = tk.Menu(row, tearoff=0)
        menu.add_command(label="编辑", command=lambda: self._edit_task(shift_index, task_index, task_label))
        menu.add_command(label="删除", command=lambda: self._remove_task(shift_index, task_index))
        task_label.bind("<Button-3>", lambda e, m=menu: m.post(e.x_root, e.y_root))
        cb.bind("<Button-3>", lambda e, m=menu: m.post(e.x_root, e.y_root))

        # 双击编辑
        task_label.bind("<Double-Button-1>", lambda e: self._edit_task(shift_index, task_index, task_label))

        return row

    def _on_task_toggle(self, shift_index, task_index, var, label):
        """切换任务完成状态"""
        self.task_manager.toggle_task(shift_index, task_index)
        is_done = var.get()
        if is_done:
            label.config(fg="#95A5A6", font=tkfont.Font(size=10, overstrike=True))
        else:
            label.config(fg="#2C3E50", font=tkfont.Font(size=10))
        self._update_status()

    def _add_task(self, shift_index):
        """添加任务"""
        text = simpledialog.askstring("添加任务", "请输入任务内容:", parent=self)
        if text and text.strip():
            self.task_manager.add_task(shift_index, text.strip())
            self.refresh()

    def _edit_task(self, shift_index, task_index, label):
        """编辑任务"""
        current = self.task_manager.shifts[shift_index]["tasks"][task_index]
        new_text = simpledialog.askstring("编辑任务", "修改任务内容:", initialvalue=current, parent=self)
        if new_text is not None and new_text.strip():
            self.task_manager.update_task(shift_index, task_index, new_text.strip())
            label.config(text=new_text.strip())

    def _remove_task(self, shift_index, task_index):
        """删除任务"""
        if messagebox.askyesno("确认删除", "确定要删除这个任务吗？", parent=self):
            self.task_manager.remove_task(shift_index, task_index)
            self.refresh()

    def refresh(self):
        """刷新整个界面"""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self._shift_widgets = []
        for i, shift in enumerate(self.task_manager.shifts):
            frame = self._create_shift_card(self.scroll_frame, shift, i)
            frame.pack(fill=tk.X, padx=5, pady=3)
            self._shift_widgets.append(frame)
        self._update_status()

    def _update_status(self):
        """更新状态栏"""
        next_reminder = self.task_manager.get_next_reminder()
        if next_reminder:
            delta = next_reminder["reminder_datetime"] - datetime.now()
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            self.status_label.config(
                text=f"下次提醒: {next_reminder['label']} ({next_reminder['time']})  "
                     f"剩余: {hours}小时{minutes}分钟"
            )
        else:
            # 检查是否所有任务已完成
            all_done = all(s.get("completed", False) for s in self.task_manager.shifts)
            if all_done:
                self.status_label.config(text="所有时段任务已完成，可以关闭程序")
            else:
                self.status_label.config(text="等待提醒...")

    def _start_clock_update(self):
        """每秒更新时钟和状态"""
        now = datetime.now()
        self.clock_label.config(text=now.strftime("%Y-%m-%d %H:%M:%S"))
        self._update_status()
        self.after(1000, self._start_clock_update)

    def _on_close(self):
        """关闭按钮 -> 最小化到托盘"""
        self.withdraw()

    def _bind_mousewheel(self):
        """绑定鼠标滚轮事件"""
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux_up)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux_down)

    def _unbind_mousewheel(self):
        """解绑鼠标滚轮事件"""
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        """Windows 鼠标滚轮"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux_up(self, event):
        """Linux 鼠标滚轮上"""
        self.canvas.yview_scroll(-1, "units")

    def _on_mousewheel_linux_down(self, event):
        """Linux 鼠标滚轮下"""
        self.canvas.yview_scroll(1, "units")
