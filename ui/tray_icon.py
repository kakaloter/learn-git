"""
系统托盘图标 - 后台运行，右键菜单
"""
import threading
from PIL import Image, ImageDraw
import pystray


class TrayIcon:
    def __init__(self, main_window, task_manager, on_quit_callback):
        self.main_window = main_window
        self.task_manager = task_manager
        self.on_quit_callback = on_quit_callback
        self._icon = None
        self._thread = None

    def run(self):
        """在子线程中启动托盘图标"""
        icon_image = self._create_icon_image()
        next_info = self._get_next_reminder_text()

        self._icon = pystray.Icon(
            "duty_alarm",
            icon_image,
            f"值班闹钟{next_info}",
            menu=self._create_menu()
        )
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()

    def _create_icon_image(self):
        """创建托盘图标（时钟图标）"""
        size = 64
        image = Image.new("RGB", (size, size), "white")
        draw = ImageDraw.Draw(image)

        # 画圆形时钟
        margin = 4
        draw.ellipse([margin, margin, size - margin, size - margin], outline="#2C3E50", width=3)

        # 画时钟指针（8点方向）
        center = size // 2
        # 时针
        draw.line([(center, center), (center - 8, center + 14)], fill="#2C3E50", width=3)
        # 分针
        draw.line([(center, center), (center + 14, center - 4)], fill="#E74C3C", width=2)
        # 中心点
        draw.ellipse([center - 3, center - 3, center + 3, center + 3], fill="#2C3E50")

        return image

    def _create_menu(self):
        """创建右键菜单"""
        return pystray.Menu(
            pystray.MenuItem("显示主窗口", self._show_main),
            pystray.MenuItem(self._next_reminder_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._quit),
        )

    def _next_reminder_text(self, item=None):
        """动态获取下次提醒文本"""
        return self._get_next_reminder_text()

    def _get_next_reminder_text(self):
        """获取下次提醒信息"""
        next_shift = self.task_manager.get_next_reminder()
        if next_shift:
            return f"下次提醒: {next_shift['label']} ({next_shift['time']})"
        return "无待提醒时段"

    def _show_main(self, icon=None, item=None):
        """显示主窗口"""
        if self.main_window:
            self.main_window.after(0, self._deiconify_main)

    def _deiconify_main(self):
        """在主线程中恢复窗口"""
        self.main_window.deiconify()
        self.main_window.focus_force()

    def _quit(self, icon=None, item=None):
        """退出程序"""
        # 检查最后一个时段任务是否完成
        if not self.task_manager.is_last_shift_completed():
            # 需要在主线程中弹确认框
            self.main_window.after(0, self._confirm_quit)
        else:
            self._do_quit()

    def _confirm_quit(self):
        """确认退出弹窗"""
        import tkinter.messagebox as mb
        if mb.askyesno("确认退出", "次日早班任务尚未全部完成，确定退出吗？", parent=self.main_window):
            self._do_quit()

    def _do_quit(self):
        """执行退出"""
        if self._icon:
            self._icon.stop()
        if self.on_quit_callback:
            self.on_quit_callback()

    def update_tooltip(self):
        """更新托盘提示文本"""
        if self._icon:
            try:
                next_info = self._get_next_reminder_text()
                self._icon.title = f"值班闹钟 - {next_info}"
            except Exception:
                pass

    def stop(self):
        """停止托盘图标"""
        if self._icon:
            self._icon.stop()
