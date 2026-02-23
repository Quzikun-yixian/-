import tkinter as tk
from tkinter import ttk
import math

TYPE_MAP = {
    "专业核心课": "core",
    "专业基础课": "basic",
    "通识基础课": "general_core",
    "专业选修课": "elective",
    "通识选修课": "general_elective"
}

def calculate_bid_interval(
    total_score: float,
    desire: float,
    capacity: int,
    selected: int,
    course_type: str,
    offered: int,
    teacher: float,
    grading: float,
    content: float,
    trend: float = 1.0
) -> dict:
    R = (selected) / capacity
    
    type_base = {
        "core": 1,
        "basic": 1.1,
        "general_core": 1.1,
        "elective": 0.85,
        "general_elective": 0.9
    }.get(course_type, 0.5)
    
    I_raw = type_base * (1 + 5 / max(offered, 1))
    I = min(I_raw / 3, 1.0)
    
    H_raw = ((teacher + grading + content) / 30) * trend
    H = min(max(H_raw, 0), 1.5)
    
    # 核心思想：基础分数完全由竞争比R决定（非线性）
    if R <= 1:
        # 冷门课：几乎没人选，1分就够
        base_score = 1.0
    else:
        # R>1时指数增长：R=1时1分，R=2时约15分，R=3时约40分（封顶）
        base_score = 1.0 + (4 ** (R - 1) - 1) * 40
        base_score = min(base_score, total_score * 0.5)
    
    # 根据课程质量微调（±15%）
    quality_factor = 0.8 + H * 0.15  # H=0时0.85，H=1.5时1.0
    base_score = base_score * quality_factor
    
    # 根据课程类型微调（±10%）
    type_factor = {
        "core": 1,
        "basic": 1.1,
        "general_core": 1.1,
        "elective": 0.85,
        "general_elective": 0.9
    }.get(course_type, 1.0)
    base_score = base_score * type_factor
    
    # 最终约束
    base_score = max(1.0, min(base_score, total_score * 1))
    
    # 计算三个分数
    mid = base_score
    
    # 冲：欲望越高，冲越高！
    chong_factor = max(0.5, desire * 0.5)
    low = base_score * chong_factor
    low = max(1.0, low)
    
    # 保：欲望越高，加成越多（最多+15%总分）
    desire_bonus = total_score * (0.02*R) * ((desire+1) ** 1.1)  # 非线性欲望加成
    high = base_score + desire_bonus
    high = min(high, total_score)
    
    # 确保顺序
    low = min(low, mid)
    high = max(high, mid)
    
    return {
        "冲": round(low, 1),
        "稳": round(mid, 1),
        "保": round(high, 1)
    }

class BidCalculatorUI:
    def __init__(self, root):
        self.root = root
        self.root.title("南科大选课投分计算器（连续版）")
        self.root.geometry("380x700")
        self.root.resizable(False, False)
        
        self.vars = {}
        self.create_ui()
        self.bind_events()
        self.calculate()
        
    def create_ui(self):
        tk.Label(self.root, text="🎓 南科大选课投分计算器", 
                font=("微软雅黑", 16, "bold")).pack(pady=15)
        
        frame = tk.Frame(self.root)
        frame.pack(padx=25, pady=10)
        
        fields = [
            ("总分", "total_score", "150"),
            ("期望系数 (0-1)", "desire", "0.9"),
            ("课程容量", "capacity", "40"),
            ("已选人数", "selected", "50"),  # 默认 R=1
            ("开设班次", "offered", "1"),
            ("教师评价 (1-10)", "teacher", "10"),
            ("给分好坏 (1-10)", "grading", "10"),
            ("内容质量 (1-10)", "content", "10"),
            ("热度趋势 (0.5-1.5)", "trend", "1.2"),
        ]
        
        for i, (label, key, default) in enumerate(fields):
            tk.Label(frame, text=label+":", anchor="w", width=18).grid(
                row=i, column=0, sticky="w", pady=6)
            var = tk.StringVar(value=default)
            entry = tk.Entry(frame, textvariable=var, width=12)
            entry.grid(row=i, column=1, pady=6)
            self.vars[key] = var
        
        i = len(fields)
        tk.Label(frame, text="课程类型:", anchor="w", width=18).grid(
            row=i, column=0, sticky="w", pady=6)
        self.course_type = ttk.Combobox(frame, values=[
            "专业核心课", "专业基础课", "通识基础课", "专业选修课", "通识选修课"
        ], width=11, state="readonly")
        self.course_type.set("通识选修课")
        self.course_type.grid(row=i, column=1, pady=6)
        
        result_frame = tk.Frame(self.root, bg="#f5f5f5", bd=2, relief="groove")
        result_frame.pack(padx=25, pady=10, fill="x")
        
        tk.Label(result_frame, text="投分区间", font=("微软雅黑", 12, "bold"),
                bg="#f5f5f5").pack(pady=12)
        
        colors = {"保": "#27ae60", "稳": "#f39c12", "冲": "#e74c3c"}
        self.result_labels = {}
        
        for key in ["保", "稳", "冲"]:
            row = tk.Frame(result_frame, bg="#f5f5f5")
            row.pack(pady=8)
            tk.Label(row, text=key, font=("微软雅黑", 14), 
                    bg="#f5f5f5", fg=colors[key], width=3).pack(side="left")
            lbl = tk.Label(row, text="0", font=("微软雅黑", 20, "bold"),
                          bg="#f5f5f5", fg=colors[key])
            lbl.pack(side="left", padx=15)
            self.result_labels[key] = lbl
        
        tk.Label(self.root, 
                text="冲=低分试试 | 稳=正常投入 | 保=高分确保",
                font=("微软雅黑", 9), fg="gray").pack(pady=15)
        
    def bind_events(self):
        for var in self.vars.values():
            var.trace("w", lambda *args: self.calculate())
        self.course_type.bind("<<ComboboxSelected>>", lambda e: self.calculate())
        
    def get_val(self, key, default=0, type_func=float):
        try:
            return type_func(self.vars[key].get())
        except:
            return default
            
    def calculate(self, *args):
        try:
            result = calculate_bid_interval(
                total_score=self.get_val("total_score", 150),
                desire=self.get_val("desire", 0.8),
                capacity=self.get_val("capacity", 60, int),
                selected=self.get_val("selected", 60, int),
                course_type=TYPE_MAP.get(self.course_type.get(), "general_elective"),
                offered=self.get_val("offered", 1, int),
                teacher=self.get_val("teacher", 9),
                grading=self.get_val("grading", 9),
                content=self.get_val("content", 9),
                trend=self.get_val("trend", 1.2)
            )
            for key in ["冲", "稳", "保"]:
                self.result_labels[key].config(text=str(result[key]))
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = BidCalculatorUI(root)
    root.mainloop()