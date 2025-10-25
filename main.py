import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock
import json
import re
import threading
from datetime import datetime
from typing import List, Dict, Any

kivy.require('2.1.0')


class XMLToTavoConverter:
    """将伪XML转换为Tavo格式JSON的转换器"""

    @staticmethod
    def parse_xml_content(content: str) -> List[Dict[str, Any]]:
        """解析伪XML内容为结构化数据"""
        entries = []
        entry_pattern = r'<startl>(.*?)<endl>'
        field_pattern = r'<(\w+)>(.*?)</\1>'

        for i, entry_text in enumerate(re.findall(entry_pattern, content, re.DOTALL)):
            fields = dict(re.findall(field_pattern, entry_text, re.DOTALL))

            entry = {
                "id": i + 1,
                "metadata": {
                    "name": fields.get('comment', '未命名'),
                    "position": fields.get('position', '未知'),
                    "type": fields.get('constant', '未知'),
                    "scan_depth": fields.get('scanDep', ''),
                    "sticky": fields.get('sticky', ''),
                    "cooldown": fields.get('cooldown', ''),
                    "delay": fields.get('delay', '')
                },
                "content": {
                    "keywords": fields.get('keyPositif', ''),
                    "negative_keywords": fields.get('keyAdverse', ''),
                    "main_content": fields.get('content', ''),
                    "annotation": fields.get('CN_annotation', ''),
                    "development": fields.get('development', '')
                }
            }
            entries.append(entry)

        return entries

    @staticmethod
    def generate_tavo_json(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成Tavo格式的JSON"""
        return {
            "tavo_format": {
                "version": "1.0",
                "generator": "长天快速世界书",
                "timestamp": datetime.now().isoformat(),
                "statistics": {
                    "total_entries": len(entries),
                    "entry_types": XMLToTavoConverter._count_entry_types(entries)
                },
                "entries": entries
            }
        }

    @staticmethod
    def _count_entry_types(entries: List[Dict[str, Any]]) -> Dict[str, int]:
        """统计条目类型"""
        type_count = {}
        for entry in entries:
            entry_type = entry["metadata"]["type"]
            type_count[entry_type] = type_count.get(entry_type, 0) + 1
        return type_count


class ChangtianWorldBook(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 15
        self.spacing = 10
        self.converter = XMLToTavoConverter()
        self.setup_ui()

    def setup_ui(self):
        # 标题
        title = Label(
            text='长天快速世界书 - XML转Tavo格式',
            size_hint_y=None,
            height=70,
            font_size='20sp',
            bold=True,
            color=(0.1, 0.3, 0.6, 1)
        )
        self.add_widget(title)

        # 输入区域
        input_label = Label(
            text='输入伪XML内容:',
            size_hint_y=None,
            height=30,
            font_size='14sp'
        )
        self.add_widget(input_label)

        self.input_text = TextInput(
            multiline=True,
            size_hint_y=0.4,
            hint_text='粘贴伪XML内容...\n示例: <startl><comment>条目</comment><position>Char↑</position>...<endl>',
            background_color=(0.95, 0.95, 0.98, 1)
        )
        self.add_widget(self.input_text)

        # 按钮区域
        self.setup_buttons()

        # 进度显示
        self.setup_progress()

        # 结果区域
        self.setup_results()

    def setup_buttons(self):
        button_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=50,
            spacing=10
        )

        buttons = [
            ('转换为Tavo', (0.2, 0.6, 0.8, 1), self.convert_to_tavo),
            ('清空', (0.8, 0.4, 0.4, 1), self.clear_all),
            ('示例', (0.3, 0.7, 0.3, 1), self.load_example),
        ]

        for text, color, callback in buttons:
            btn = Button(text=text, background_color=color, font_size='12sp')
            btn.bind(on_press=callback)
            button_layout.add_widget(btn)

        self.add_widget(button_layout)

    def setup_progress(self):
        self.status_label = Label(
            text='就绪 - 输入XML内容并转换为Tavo格式',
            size_hint_y=None,
            height=30,
            font_size='12sp'
        )
        self.add_widget(self.status_label)

    def setup_results(self):
        result_label = Label(
            text='Tavo格式JSON输出:',
            size_hint_y=None,
            height=30,
            font_size='14sp'
        )
        self.add_widget(result_label)

        self.result_text = TextInput(
            multiline=True,
            size_hint_y=0.4,
            readonly=True,
            background_color=(0.98, 0.98, 1, 1)
        )
        self.add_widget(self.result_text)

    def update_status(self, message):
        self.status_label.text = message

    def convert_to_tavo(self, instance):
        content = self.input_text.text.strip()
        if not content:
            self.show_popup('提示', '请输入XML内容')
            return

        thread = threading.Thread(target=self._convert_in_thread, args=(content,))
        thread.daemon = True
        thread.start()

    def _convert_in_thread(self, content):
        try:
            Clock.schedule_once(lambda dt: self.update_status('解析XML内容...'), 0)
            entries = self.converter.parse_xml_content(content)

            if not entries:
                Clock.schedule_once(lambda dt: self.show_popup('错误', '未找到有效的XML条目'), 0)
                return

            Clock.schedule_once(lambda dt: self.update_status('生成Tavo JSON...'), 0)
            tavo_json = self.converter.generate_tavo_json(entries)
            json_output = json.dumps(tavo_json, ensure_ascii=False, indent=2)

            Clock.schedule_once(lambda dt: self.update_status('转换完成!'), 0)
            Clock.schedule_once(lambda dt: self.show_result(json_output, len(entries)), 0.1)

        except Exception as e:
            error_msg = f"转换失败: {str(e)}"
            Clock.schedule_once(lambda dt: self.show_popup('错误', error_msg), 0)
            Clock.schedule_once(lambda dt: self.update_status('转换出错'), 0)

    def show_result(self, result, entry_count):
        self.result_text.text = result
        self.update_status(f'转换完成! 共{entry_count}个条目')

    def clear_all(self, instance):
        self.input_text.text = ''
        self.result_text.text = ''
        self.update_status('已清空')

    def load_example(self, instance):
        example = """<startl><comment>认知权限总纲</comment><position>Char↑</position><constant>常驻</constant><keyPositif></keyPositif><keyAdverse></keyAdverse><scanDep>0</scanDep><sticky>0</sticky><cooldown>0</cooldown><delay>0</delay><content>Cognition Matrix</content><CN_annotation>维度：总纲</CN_annotation><development>扩展方向</development><endl>"""
        self.input_text.text = example
        self.update_status('示例已加载')

    def show_popup(self, title, message):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text=message))
        btn = Button(text='确定', size_hint_y=None, height=40)
        popup = Popup(title=title, content=content, size_hint=(0.7, 0.4))
        btn.bind(on_press=popup.dismiss)
        content.add_widget(btn)
        popup.open()


class ChangtianWorldBookApp(App):
    def build(self):
        self.title = "长天快速世界书 - XML转Tavo"
        return ChangtianWorldBook()


if __name__ == '__main__':
    ChangtianWorldBookApp().run()