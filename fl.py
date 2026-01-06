import tkinter as tk
from tkinter import filedialog, ttk, messagebox, simpledialog, Menu
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.widgets import LassoSelector
from matplotlib.path import Path
import re
import os
import random
from matplotlib import font_manager


# ==========================================
# 🛑 1. 字体配置 (针对 Windows)
# ==========================================
def configure_styles_force():
    plt.rcParams['axes.unicode_minus'] = False
    font_paths = [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyh.ttf", r"C:\Windows\Fonts\simhei.ttf"]
    font_loaded = False
    for path in font_paths:
        if os.path.exists(path):
            try:
                font_manager.fontManager.addfont(path)
                font_name = font_manager.FontProperties(fname=path).get_name()
                plt.rcParams['font.sans-serif'] = [font_name]
                font_loaded = True
                break
            except:
                pass
    if not font_loaded:
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']


configure_styles_force()


# ==========================================

class DataClassifierApp:
    def __init__(self, root):
        self.root = root
        self.root.title("数据分类工具 - 下拉字号版")
        self.root.geometry("1400x900")

        # 🟢 这里可以设置默认字号
        self.current_font_size = 11

        self.df = pd.DataFrame(columns=['Label', 'Y', 'X'])
        self.thresholds = []
        self.category_list = []
        self.marked_indices = set()
        self.custom_cat_names = {}

        self.enable_lasso_mode = tk.BooleanVar(value=False)
        self.color_cycle = ['#FF0000', '#00AA00', '#FF8C00', '#9400D3', '#0000FF', '#00CED1']
        self.lasso = None

        # --- 布局 ---
        self.left_panel = tk.Frame(root, width=420, bg="#f0f0f0")
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        self.right_panel = tk.Frame(root, bg="white")
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.main_notebook = ttk.Notebook(self.right_panel)
        self.main_notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_res = tk.Frame(self.main_notebook)
        self.main_notebook.add(self.tab_res, text=" 📊 分类结果与报告 ")
        self.tab_plt = tk.Frame(self.main_notebook, bg="white")
        self.main_notebook.add(self.tab_plt, text=" 📈 交互绘图区 ")

        self.setup_left_panel()
        self.setup_results_tab()
        self.setup_plot_tab()
        self.apply_font_style()

    def setup_left_panel(self):
        # 🟢 0. 全局设置 (字号下拉框替代按钮)
        settings_frame = tk.LabelFrame(self.left_panel, text="0. 全局设置", padx=10, pady=8, font=("", 10, "bold"),
                                       fg="purple")
        settings_frame.pack(fill=tk.X, pady=5)

        tk.Label(settings_frame, text="界面字号:").pack(side=tk.LEFT, padx=(0, 5))

        # 定义字号范围
        font_sizes = [str(i) for i in range(8, 31)]
        self.combo_font = ttk.Combobox(settings_frame, values=font_sizes, width=5, state="readonly")
        self.combo_font.set(str(self.current_font_size))  # 设置默认值
        self.combo_font.pack(side=tk.LEFT)

        # 绑定选择事件
        self.combo_font.bind("<<ComboboxSelected>>", self.on_font_combo_change)

        # 1. 数据导入
        control_frame = tk.LabelFrame(self.left_panel, text="1. 数据导入", padx=10, pady=10)
        control_frame.pack(fill=tk.X, pady=5)
        self.text_input = tk.Text(control_frame, height=8, width=40, font=("Consolas", 10))
        self.text_input.pack(fill=tk.X, pady=5)
        tk.Button(control_frame, text="📋 粘贴并解析数据", command=self.load_from_text, bg="#e1f5fe",
                  font=("", 10, "bold")).pack(fill=tk.X)

        # 2. 交互模式
        mode_frame = tk.LabelFrame(self.left_panel, text="2. 交互模式切换", padx=10, pady=10, fg="blue")
        mode_frame.pack(fill=tk.X, pady=10)
        tk.Radiobutton(mode_frame, text="🖱️ 直线模式 (左键加线/右键删线)", variable=self.enable_lasso_mode, value=False,
                       command=self.update_plot_view).pack(anchor="w")
        tk.Radiobutton(mode_frame, text="🎯 圈选模式 (画圈提取数据)", variable=self.enable_lasso_mode, value=True,
                       command=self.update_plot_view).pack(anchor="w")

        # 3. 操作
        op_frame = tk.LabelFrame(self.left_panel, text="3. 状态重置", padx=10, pady=10)
        op_frame.pack(fill=tk.X, pady=10)
        tk.Button(op_frame, text="🗑️ 清空所有数据及分类", command=self.reset_all, bg="#ffdddd").pack(fill=tk.X)

    def setup_results_tab(self):
        self.inner_nb = ttk.Notebook(self.tab_res)
        self.inner_nb.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 表格树
        self.tab_tree = tk.Frame(self.inner_nb)
        self.inner_nb.add(self.tab_tree, text="分类目录树")
        self.tree = ttk.Treeview(self.tab_tree, columns=('Label', 'Status', 'Index'), show='tree headings',
                                 displaycolumns=('Label', 'Status'))
        self.tree.heading('#0', text='分类目录');
        self.tree.heading('Label', text='条目名称');
        self.tree.heading('Status', text='标记')
        self.tree.column('Index', width=0, stretch=False)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<Button-3>", self.on_right_click)

        # 文本报告
        self.tab_report = tk.Frame(self.inner_nb)
        self.inner_nb.add(self.tab_report, text="文本报告")
        tk.Button(self.tab_report, text="💾 导出 TXT", command=self.export_txt_file).pack(anchor="w", padx=5, pady=2)
        self.report_text = tk.Text(self.tab_report);
        self.report_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def setup_plot_tab(self):
        self.fig, self.ax = plt.subplots(figsize=(6, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab_plt)
        self.canvas.mpl_connect('button_press_event', self.on_plot_click)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    # ===============================================
    # 🎯 交互逻辑
    # ===============================================
    def on_font_combo_change(self, event):
        """字号下拉框切换事件"""
        self.current_font_size = int(self.combo_font.get())
        self.apply_font_style()
        self.classify_and_display()

    def on_plot_click(self, event):
        if event.inaxes != self.ax: return
        if not self.enable_lasso_mode.get():
            if event.button == 1:  # 左键加线
                val = round(event.ydata, 1)
                if val not in self.thresholds:
                    self.thresholds.append(val);
                    self.thresholds.sort();
                    self.refresh_all()
            elif event.button == 3:  # 右键删线
                if self.thresholds:
                    closest_val = min(self.thresholds, key=lambda x: abs(x - event.ydata))
                    y_lim = self.ax.get_ylim()
                    if abs(closest_val - event.ydata) < (y_lim[1] - y_lim[0]) * 0.05:
                        self.thresholds.remove(closest_val);
                        self.refresh_all()

    def on_lasso_select(self, verts):
        if self.df.empty: return
        path = Path(verts)
        inside = path.contains_points(self.df[['X', 'Y']].values)
        new_indices = set(self.df.index[inside].tolist())
        if new_indices:
            for cat in self.category_list: cat['indices'] = cat['indices'] - new_indices
            cat_id = len(self.category_list) + 1
            self.category_list.append({
                'name': f"圈选提取 {cat_id}",
                'indices': new_indices,
                'color': self.color_cycle[(cat_id - 1) % len(self.color_cycle)]
            })
            self.refresh_all()

    def update_plot_view(self):
        self.ax.clear()
        self.ax.set_title("数据交互绘图区")
        if not self.df.empty:
            colors = ['#1f77b4'] * len(self.df)
            sizes = [60] * len(self.df)
            for i in self.df.index:
                if i in self.marked_indices:
                    colors[i], sizes[i] = 'red', 120
                else:
                    for cat in self.category_list:
                        if i in cat['indices']: colors[i], sizes[i] = cat['color'], 100; break
            self.ax.scatter(self.df['X'], self.df['Y'], c=colors, s=sizes, zorder=5)
            for idx, row in self.df.iterrows():
                m = idx in self.marked_indices
                self.ax.annotate(row['Label'], (row['X'], row['Y']), xytext=(0, 5),
                                 textcoords="offset points", ha='center', fontsize=9,
                                 color='red' if m else 'black', weight='bold' if m else 'normal')
        for y in self.thresholds: self.ax.axhline(y=y, color='blue', linestyle='--', alpha=0.5)
        if self.enable_lasso_mode.get():
            self.lasso = LassoSelector(self.ax, onselect=self.on_lasso_select, props={'color': 'red', 'linewidth': 1.5})
        else:
            if self.lasso: self.lasso.set_active(False); self.lasso = None
        self.canvas.draw()

    def classify_and_display(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        if self.df.empty: return
        categorized_idx = set()
        for i, cat in enumerate(self.category_list):
            if not cat['indices']: continue
            tag = f"tag_{cat['color']}"
            self.tree.tag_configure(tag, foreground=cat['color'], font=("", self.current_font_size, "bold"))
            pid = self.tree.insert("", "end", text=f"📂 {cat['name']}", open=True, tags=(tag,))
            for idx in sorted(list(cat['indices'])):
                m = idx in self.marked_indices
                self.tree.insert(pid, "end", values=(self.df.loc[idx, 'Label'], "✅ 已标记" if m else "", idx),
                                 tags=('marked' if m else ''))
                categorized_idx.add(idx)
        rem_df = self.df.drop(list(categorized_idx))
        if not rem_df.empty:
            t_sorted = sorted(self.thresholds)
            line_cats = []
            if not t_sorted:
                line_cats.append(("未选中数据", rem_df))
            else:
                line_cats.append((f"低于 {t_sorted[0]}", rem_df[rem_df['Y'] < t_sorted[0]]))
                for i in range(len(t_sorted) - 1):
                    line_cats.append((f"{t_sorted[i]} ~ {t_sorted[i + 1]}",
                                      rem_df[(rem_df['Y'] >= t_sorted[i]) & (rem_df['Y'] < t_sorted[i + 1])]))
                line_cats.append((f"高于 {t_sorted[-1]}", rem_df[rem_df['Y'] >= t_sorted[-1]]))
            for name, sub in line_cats:
                if sub.empty: continue
                d_name = self.custom_cat_names.get(name, name)
                pid = self.tree.insert("", "end", text=f"📂 {d_name}", open=True)
                for r_idx, r in sub.iterrows():
                    m = r_idx in self.marked_indices
                    self.tree.insert(pid, "end", values=(r['Label'], "✅ 已标记" if m else "", r_idx),
                                     tags=('marked' if m else ''))
        self.generate_report_from_tree()

    # ===============================================
    # 📝 报告逻辑
    # ===============================================
    def generate_report_from_tree(self):
        self.report_text.delete("1.0", tk.END)
        content = ""
        for pid in self.tree.get_children(""):
            title = self.tree.item(pid, "text").replace("📂 ", "")
            children = self.tree.get_children(pid)
            if not children: continue
            content += f"【{title}】:\n"
            prev_m = None
            for i, cid in enumerate(children):
                vals = self.tree.item(cid, "values")
                name, idx = vals[0], int(vals[2])
                curr_m = idx in self.marked_indices
                if curr_m:
                    if prev_m is False or prev_m is None: content += "\n"
                    content += f"{name}\n"
                else:
                    content += f"\n{name}\n\n"
                if curr_m:
                    next_m = False
                    if i < len(children) - 1:
                        next_m = int(self.tree.item(children[i + 1], "values")[2]) in self.marked_indices
                    if not next_m: content += "\n"
                prev_m = curr_m
            content += "\n"
        self.report_text.insert(tk.END, re.sub(r'\n{3,}', '\n\n', content).strip() + "\n")

    # ===============================================
    # 📋 其他方法
    # ===============================================
    def apply_font_style(self):
        s = self.current_font_size
        ttk.Style().configure("Treeview", font=("Microsoft YaHei", s), rowheight=int(s * 2.5))
        self.tree.tag_configure('marked', foreground='red', font=("", s, "bold"))
        self.report_text.configure(font=("Microsoft YaHei", s))

    def on_right_click(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            if self.tree.parent(iid):
                idx = int(self.tree.item(iid, 'values')[2])
                if idx in self.marked_indices:
                    self.marked_indices.remove(idx)
                else:
                    self.marked_indices.add(idx)
                self.refresh_all()
            else:
                old = self.tree.item(iid, "text").replace("📂 ", "")
                new = simpledialog.askstring("重命名", "分类名称:", initialvalue=old)
                if new:
                    idx = self.tree.get_children("").index(iid);
                    if idx < len(self.category_list):
                        self.category_list[idx]['name'] = new
                    else:
                        self.custom_cat_names[old] = new
                    self.refresh_all()

    def refresh_all(self):
        self.update_plot_view();
        self.classify_and_display()

    def reset_all(self):
        if messagebox.askyesno("确认", "重置所有？"):
            self.thresholds = [];
            self.category_list = [];
            self.marked_indices = set();
            self.custom_cat_names = {};
            self.refresh_all()

    def load_from_text(self):
        raw = self.text_input.get("1.0", tk.END).strip()
        data = []
        for line in raw.split('\n'):
            parts = re.split(r'[|\t,，]+', line.strip())
            if len(parts) >= 3:
                try:
                    data.append([parts[0].strip(), float(parts[1]), float(parts[2])])
                except:
                    continue
        if data:
            self.df = pd.DataFrame(data, columns=['Label', 'Y', 'X'])
            self.reset_all();
            self.main_notebook.select(self.tab_plt)

    def export_txt_file(self):
        raw = self.report_text.get("1.0", tk.END)
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path:
            filtered = [l for l in raw.splitlines() if not (l.strip().startswith("【") and "】" in l)]
            with open(path, "w", encoding="utf-8") as f: f.write("\n".join(filtered).strip())


if __name__ == "__main__":
    root = tk.Tk();
    app = DataClassifierApp(root);
    root.mainloop()