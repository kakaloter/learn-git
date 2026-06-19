"""
定时调度器 - 每秒轮询当前时间，匹配提醒时间点
"""
from datetime import datetime


class Scheduler:
    def __init__(self, task_manager, on_reminder_callback, poll_interval_ms=1000):
        self.task_manager = task_manager
        self.on_reminder_callback = on_reminder_callback
        self.poll_interval_ms = poll_interval_ms
        self._timer_id = None
        self._running = False
        self._last_triggered = set()  # 防止同一分钟重复触发

    def start(self, root):
        """启动调度器（使用 tkinter 的 after 方法）"""
        self._running = True
        self._root = root
        # 启动时将所有已过时的时段标记为已触发，避免启动时立即提醒
        now = datetime.now()
        for shift in self.task_manager.shifts:
            if not shift["reminded"] and shift["reminder_datetime"] <= now:
                shift["reminded"] = True
                trigger_key = f"{shift['reminder_datetime'].strftime('%Y-%m-%d %H:%M')}"
                self._last_triggered.add(trigger_key)
        self.task_manager.save_session()
        self._poll()

    def stop(self):
        """停止调度器"""
        self._running = False
        if self._timer_id is not None:
            try:
                self._root.after_cancel(self._timer_id)
            except Exception:
                pass
            self._timer_id = None

    def _poll(self):
        """轮询检查是否到达提醒时间"""
        if not self._running:
            return

        now = datetime.now()
        # 检查所有已到时间但未提醒的时段
        pending = self.task_manager.get_pending_shifts()
        for shift in pending:
            shift_index = self.task_manager.shifts.index(shift)
            # 用时间戳的唯一键防止重复触发
            trigger_key = f"{shift['reminder_datetime'].strftime('%Y-%m-%d %H:%M')}"
            if trigger_key not in self._last_triggered:
                self._last_triggered.add(trigger_key)
                self.task_manager.mark_reminded(shift_index)
                # 触发回调
                if self.on_reminder_callback:
                    self.on_reminder_callback(shift_index)

        # 继续下一次轮询
        self._timer_id = self._root.after(self.poll_interval_ms, self._poll)
