"""
提醒管理器 - 弹出提醒窗口 + 播放声音 + 5分钟循环提醒
"""
import winsound
import threading


class ReminderManager:
    SOUND_REPEAT_INTERVAL = 5 * 60 * 1000  # 5分钟（毫秒）

    def __init__(self, root, task_manager, main_window_class, reminder_window_class):
        self.root = root
        self.task_manager = task_manager
        self.main_window_class = main_window_class
        self.reminder_window_class = reminder_window_class
        self._sound_playing = False
        self._sound_thread = None
        self._stop_sound_event = threading.Event()
        self._active_reminder = None  # 当前活跃的提醒窗口
        self._snooze_timer_id = None  # 贪睡计时器

    def trigger(self, shift_index):
        """触发提醒：弹窗 + 声音"""
        shift = self.task_manager.shifts[shift_index]
        self._play_alarm_sound()
        self._show_reminder_window(shift_index)

    def _play_alarm_sound(self):
        """播放提示音（循环，直到手动停止）"""
        self.stop_sound()
        self._stop_sound_event.clear()
        self._sound_playing = True
        self._sound_thread = threading.Thread(target=self._sound_loop, daemon=True)
        self._sound_thread.start()

    def _sound_loop(self):
        """在子线程中循环播放提示音"""
        try:
            while not self._stop_sound_event.is_set():
                winsound.Beep(1000, 500)  # 频率1000Hz，持续500ms
                winsound.Beep(800, 500)   # 频率800Hz，持续500ms
                # 短暂停顿
                if self._stop_sound_event.wait(0.5):
                    break
        except Exception:
            pass
        finally:
            self._sound_playing = False

    def stop_sound(self):
        """停止声音播放"""
        self._stop_sound_event.set()
        self._sound_playing = False
        if self._sound_thread and self._sound_thread.is_alive():
            self._sound_thread.join(timeout=2)
        self._sound_thread = None

    def _show_reminder_window(self, shift_index):
        """显示提醒弹窗"""
        if self._active_reminder:
            try:
                self._active_reminder.destroy()
            except Exception:
                pass
        self._active_reminder = self.reminder_window_class(
            self.root, self, self.task_manager, shift_index
        )

    def on_acknowledge(self, shift_index):
        """用户点击"知道了"：停止声音，5分钟后再响"""
        self.stop_sound()
        self._cancel_snooze_timer()
        # 5分钟后再次播放声音
        self._snooze_timer_id = self.root.after(
            self.SOUND_REPEAT_INTERVAL,
            lambda: self._on_snooze(shift_index)
        )
        # 更新窗口标题显示倒计时
        if self._active_reminder:
            self._active_reminder.start_countdown(5 * 60)

    def _on_snooze(self, shift_index):
        """5分钟贪睡结束，再次播放声音"""
        self._snooze_timer_id = None
        self._play_alarm_sound()
        if self._active_reminder:
            self._active_reminder.stop_countdown()

    def on_complete(self, shift_index):
        """用户点击"完成"：停止声音 + 关闭弹窗"""
        self.stop_sound()
        self._cancel_snooze_timer()
        self.task_manager.mark_completed(shift_index)
        if self._active_reminder:
            try:
                self._active_reminder.destroy()
            except Exception:
                pass
            self._active_reminder = None

        # 如果是最后一个时段（次日早班），确认后退出整个程序
        if self.task_manager.is_last_shift(shift_index):
            self.root.after(300, lambda: self._confirm_and_quit())

    def _confirm_and_quit(self):
        """最后时段完成后，确认并退出程序"""
        import tkinter.messagebox as mb
        result = mb.showinfo(
            "值班完成",
            "本次值班所有任务已完成，值班闹钟将关闭。",
            parent=self.root
        )
        # 关闭整个应用
        self.root.after(100, self._do_full_quit)

    def _do_full_quit(self):
        """执行完整退出"""
        # 通过 root (MainWindow) 触发退出回调
        quit_cb = getattr(self.root, '_on_quit_callback', None)
        if quit_cb:
            quit_cb()
        else:
            self.cleanup()
            self.root.destroy()

    def _cancel_snooze_timer(self):
        """取消贪睡计时器"""
        if self._snooze_timer_id is not None:
            try:
                self.root.after_cancel(self._snooze_timer_id)
            except Exception:
                pass
            self._snooze_timer_id = None

    def cleanup(self):
        """清理资源"""
        self.stop_sound()
        self._cancel_snooze_timer()
        if self._active_reminder:
            try:
                self._active_reminder.destroy()
            except Exception:
                pass
            self._active_reminder = None
