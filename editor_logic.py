import json
import tkinter as tk
import re
from ui_shared import show_msg

class EditorManager:
    def __init__(self, text_widget):
        self.text = text_widget

    def get_content_snapshot(self):
        text = self.text.get("1.0", "end-1c")
        tags_data = []
        for tag in ["bold", "italic", "heading"]:
            ranges = self.text.tag_ranges(tag)
            if ranges:
                tags_data.append({
                    "name": tag,
                    "ranges": [str(r) for r in ranges]
                })
        return json.dumps({"text": text, "tags": tags_data})

    def apply_content_snapshot(self, json_str):
        self.text.delete("1.0", "end")
        try:
            data = json.loads(json_str)
            self.text.insert("1.0", data.get("text", ""))
            for tag_info in data.get("tags", []):
                tag_name = tag_info["name"]
                ranges = tag_info["ranges"]
                for i in range(0, len(ranges), 2):
                    self.text.tag_add(tag_name, ranges[i], ranges[i+1])
        except (json.JSONDecodeError, TypeError):
            self.text.insert("1.0", json_str)

    def insert_smart_list(self, list_type):
        try:
            start = self.text.index("sel.first")
            end = self.text.index("sel.last")
        except:
            start = self.text.index("insert")
            end = start
            
        start_line = f"{start} linestart"
        end_line = f"{end} lineend"
        content = self.text.get(start_line, end_line)
        lines = content.split('\n')
        new_lines = []
        prefix_pattern = r"^\s*(•|\d+\.|[A-Za-z]\.)\s*"

        for i, line in enumerate(lines):
            clean_text = re.sub(prefix_pattern, "", line)
            if not clean_text.strip() and len(lines) > 1:
                new_lines.append("")
                continue
            
            if list_type == "bullet": new_prefix = "• "
            elif list_type == "number": new_prefix = f"{i+1}. "
            elif list_type == "alpha_upper": new_prefix = f"{chr(65 + i)}. "
            elif list_type == "alpha_lower": new_prefix = f"{chr(97 + i)}. "
            else: new_prefix = ""
            new_lines.append(f"{new_prefix}{clean_text}")

        self.text.delete(start_line, end_line)
        self.text.insert(start_line, "\n".join(new_lines))