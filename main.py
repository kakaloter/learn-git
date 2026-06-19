"""
值班闹钟 - 程序入口
"""
import sys
import os

# 确保项目根目录在 sys.path 中
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.task_manager import TaskManager
from core.scheduler import Scheduler
from core.reminder import ReminderManager
from ui.main_window import MainWindow
from ui.reminder_window import ReminderWindow
from ui.tray_icon import TrayIcon


class DutyAlarmApp:
    def __init__(self):
        self.task_manager = TaskManager()
        self.reminder_manager = None
        self.scheduler = None
        self.tray_icon = None
        self.main_window = None

    def run(self):
        """启动应用"""
        # 初始化任务会话
        try:
            self.task_manager.init_session()
        except Exception as e:
            import tkinter.messagebox as mb
            mb.showerror("启动错误", f"加载任务模板失败:\n{e}")
            return

        # 创建主窗口（MainWindow 继承自 tk.Tk，它自己就是 root）
        self.main_window = MainWindow(
            self.task_manager,
            None,  # reminder_manager 稍后设置
            on_quit_callback=self._quit
        )

        # 创建提醒管理器
        self.reminder_manager = ReminderManager(
            self.main_window,
            self.task_manager,
            MainWindow,
            ReminderWindow
        )
        self.main_window.reminder_manager = self.reminder_manager

        # 创建调度器
        self.scheduler = Scheduler(
            self.task_manager,
            on_reminder_callback=self._on_reminder
        )
        self.scheduler.start(self.main_window)

        # 创建系统托盘
        self.tray_icon = TrayIcon(
            self.main_window,
            self.task_manager,
            on_quit_callback=self._quit
        )
        self.tray_icon.run()

        # 启动主循环
        self.main_window.mainloop()

        # 退出清理
        self._cleanup()

    def _on_reminder(self, shift_index):
        """调度器触发提醒的回调"""
        shift = self.task_manager.shifts[shift_index]
        print(f"[提醒触发] {shift['label']} ({shift['time']})")
        self.reminder_manager.trigger(shift_index)
        # 刷新主窗口
        if self.main_window:
            self.main_window.refresh()
        # 更新托盘提示
        if self.tray_icon:
            self.tray_icon.update_tooltip()

    def _quit(self):
        """退出程序"""
        self._cleanup()
        self.main_window.destroy()

    def _cleanup(self):
        """清理资源"""
        if self.scheduler:
            self.scheduler.stop()
        if self.reminder_manager:
            self.reminder_manager.cleanup()
        if self.tray_icon:
            self.tray_icon.stop()


if __name__ == "__main__":
    app = DutyAlarmApp()
    app.run()
