"""
任务管理器 - 加载模板、管理运行时任务状态
"""
import json
import copy
import os
from datetime import datetime, timedelta


class TaskManager:
    def __init__(self, config_dir=None):
        if config_dir is None:
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
        self.config_dir = config_dir
        self.template_path = os.path.join(config_dir, "tasks_template.json")
        self.session_path = os.path.join(config_dir, "session_state.json")
        self.shifts = []  # 运行时的任务实例
        self.start_date = None  # 程序启动日期

    def load_template(self):
        """从 tasks_template.json 加载任务模板"""
        if not os.path.exists(self.template_path):
            raise FileNotFoundError(f"任务模板文件不存在: {self.template_path}")
        with open(self.template_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._validate_template(data)
        return data["shifts"]

    def _validate_template(self, data):
        """校验模板格式"""
        if "shifts" not in data:
            raise ValueError("模板缺少 'shifts' 字段")
        for i, shift in enumerate(data["shifts"]):
            if "time" not in shift:
                raise ValueError(f"第{i+1}个时段缺少 'time' 字段")
            if "label" not in shift:
                raise ValueError(f"第{i+1}个时段缺少 'label' 字段")
            if "tasks" not in shift or not isinstance(shift["tasks"], list):
                raise ValueError(f"第{i+1}个时段缺少 'tasks' 字段或格式不正确")
            # 校验时间格式
            try:
                datetime.strptime(shift["time"], "%H:%M")
            except ValueError:
                raise ValueError(f"第{i+1}个时段时间格式错误: {shift['time']}，应为 HH:MM")

    def init_session(self):
        """初始化或恢复会话，生成运行时任务实例"""
        self.start_date = datetime.now().date()
        # 尝试恢复会话
        if self._try_restore_session():
            return
        # 从模板创建新会话
        template_shifts = self.load_template()
        self.shifts = self._create_session_from_template(template_shifts)
        self.save_session()

    def _create_session_from_template(self, template_shifts):
        """从模板创建运行时任务实例"""
        now = datetime.now()
        shifts = []
        for t in template_shifts:
            shift = copy.deepcopy(t)
            # 计算实际提醒时间
            hour, minute = map(int, shift["time"].split(":"))
            is_next_day = shift.get("next_day", False)
            reminder_date = now.date() + timedelta(days=1) if is_next_day else now.date()
            reminder_dt = datetime(reminder_date.year, reminder_date.month, reminder_date.day, hour, minute)
            shift["reminder_datetime"] = reminder_dt
            shift["reminded"] = False  # 是否已提醒
            shift["completed"] = False  # 时段任务是否已完成（用户点"完成"）
            # 为每个任务添加完成状态
            shift["task_states"] = [False] * len(shift["tasks"])
            shifts.append(shift)
        # 按时间排序
        shifts.sort(key=lambda s: s["reminder_datetime"])
        return shifts

    def _try_restore_session(self):
        """尝试恢复上次会话"""
        if not os.path.exists(self.session_path):
            return False
        try:
            with open(self.session_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            saved_date = datetime.strptime(data.get("start_date", ""), "%Y-%m-%d").date()
            # 如果是同一天启动，恢复会话
            if saved_date == datetime.now().date():
                self.shifts = []
                for s in data["shifts"]:
                    shift = copy.deepcopy(s)
                    # 恢复 datetime 对象
                    shift["reminder_datetime"] = datetime.strptime(
                        shift["reminder_datetime"], "%Y-%m-%d %H:%M:%S"
                    )
                    self.shifts.append(shift)
                self.start_date = saved_date
                return True
        except (json.JSONDecodeError, KeyError, ValueError):
            return False
        return False

    def save_session(self):
        """保存当前会话状态"""
        data = {
            "start_date": self.start_date.strftime("%Y-%m-%d"),
            "shifts": []
        }
        for s in self.shifts:
            shift_copy = copy.deepcopy(s)
            shift_copy["reminder_datetime"] = shift_copy["reminder_datetime"].strftime("%Y-%m-%d %H:%M:%S")
            data["shifts"].append(shift_copy)
        with open(self.session_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_pending_shifts(self):
        """获取尚未提醒的时段"""
        now = datetime.now()
        return [s for s in self.shifts if not s["reminded"] and s["reminder_datetime"] <= now]

    def get_next_reminder(self):
        """获取下一个提醒时间"""
        now = datetime.now()
        pending = [s for s in self.shifts if not s["reminded"] and s["reminder_datetime"] > now]
        if pending:
            return min(pending, key=lambda s: s["reminder_datetime"])
        return None

    def mark_reminded(self, shift_index):
        """标记时段已提醒"""
        self.shifts[shift_index]["reminded"] = True
        self.save_session()

    def mark_completed(self, shift_index):
        """标记时段已处理（用户点"完成"）"""
        self.shifts[shift_index]["completed"] = True
        self.save_session()

    def toggle_task(self, shift_index, task_index):
        """切换任务完成状态"""
        self.shifts[shift_index]["task_states"][task_index] = not self.shifts[shift_index]["task_states"][task_index]
        self.save_session()

    def add_task(self, shift_index, task_text):
        """为指定时段添加任务"""
        self.shifts[shift_index]["tasks"].append(task_text)
        self.shifts[shift_index]["task_states"].append(False)
        self.save_session()

    def remove_task(self, shift_index, task_index):
        """删除指定时段的任务"""
        self.shifts[shift_index]["tasks"].pop(task_index)
        self.shifts[shift_index]["task_states"].pop(task_index)
        self.save_session()

    def update_task(self, shift_index, task_index, new_text):
        """修改任务内容"""
        self.shifts[shift_index]["tasks"][task_index] = new_text
        self.save_session()

    def is_last_shift_completed(self):
        """检查次日早班（最后一个时段）任务是否全部完成"""
        if not self.shifts:
            return False
        last_shift = self.shifts[-1]
        return all(last_shift["task_states"])

    def is_last_shift(self, shift_index):
        """判断是否为最后一个时段"""
        return shift_index == len(self.shifts) - 1

    def clear_session(self):
        """清除会话文件"""
        if os.path.exists(self.session_path):
            os.remove(self.session_path)
