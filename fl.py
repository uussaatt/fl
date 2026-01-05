import tkinter as tk
from tkinter import filedialog, ttk, messagebox, simpledialog, Menu
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import re
import os
import random
from matplotlib import font_manager

# === 尝试导入简繁转换库 ===
try:
    import opencc

    HAS_OPENCC = True
except ImportError:
    HAS_OPENCC = False


# ==========================================
# 🛑 核心修复区：强制加载 Windows 中文字体
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
        self.root.title("数据分类工具 - 标签页整合版")
        self.root.geometry("1400x900")

        self.current_font_size = 11
        self.df = pd.DataFrame(columns=['Label', 'Y', 'X'])
        self.thresholds = []
        self.enable_click_mode = tk.BooleanVar(value=True)
        self.marked_labels = set()
        self.custom_category_names = {}
        self.drag_source_item = None

        # ===============================================
        # 🟢 布局结构：左侧控制 + 右侧主标签页
        # ===============================================

        # --- 1. 左侧面板 (固定不动) ---
        self.left_panel = tk.Frame(root, width=420, bg="#f0f0f0")
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        # --- 2. 右侧面板 (主标签页容器) ---
        self.right_panel = tk.Frame(root, bg="white")
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 创建主 Notebook (用于切换 结果/报告 和 图表)
        self.main_notebook = ttk.Notebook(self.right_panel)
        self.main_notebook.pack(fill=tk.BOTH, expand=True)

        # >>> 主标签页 1：分类结果与报告 <<<
        self.tab_results_container = tk.Frame(self.main_notebook)
        self.main_notebook.add(self.tab_results_container, text=" 📊 分类结果与报告 ")

        # >>> 主标签页 2：数据分布图 <<<
        self.tab_plot_container = tk.Frame(self.main_notebook, bg="white")
        self.main_notebook.add(self.tab_plot_container, text=" 📈 数据分布图 ")

        # ===============================================
        # 🔵 初始化各个模块
        # ===============================================
        self.setup_left_panel()  # 左侧控件
        self.setup_results_tab()  # 构建标签页 1 的内容
        self.setup_plot_tab()  # 构建标签页 2 的内容
        self.apply_font_style()  # 应用初始字体

    def setup_left_panel(self):
        # 1. 全局设置 (字号)
        settings_frame = tk.LabelFrame(self.left_panel, text="0. 全局设置", padx=10, pady=5,
                                       font=("Microsoft YaHei", 10, "bold"), fg="purple")
        settings_frame.pack(fill=tk.X, pady=5)

        tk.Label(settings_frame, text="界面字号:", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        tk.Button(settings_frame, text=" A+ ", command=lambda: self.adjust_font_size(1),
                  bg="#ddd", width=4).pack(side=tk.LEFT, padx=5)
        tk.Button(settings_frame, text=" A- ", command=lambda: self.adjust_font_size(-1),
                  bg="#ddd", width=4).pack(side=tk.LEFT, padx=5)
        self.lbl_size_display = tk.Label(settings_frame, text=f"当前: {self.current_font_size}", fg="gray")
        self.lbl_size_display.pack(side=tk.LEFT, padx=10)

        # 2. 数据导入
        control_frame = tk.LabelFrame(self.left_panel, text="1. 数据导入", padx=10, pady=10,
                                      font=("Microsoft YaHei", 10, "bold"))
        control_frame.pack(fill=tk.X, pady=5)
        tk.Label(control_frame, text="粘贴数据 (名称 | Y | X):", anchor="w", font=("Microsoft YaHei", 10)).pack(
            fill=tk.X)
        self.text_input = tk.Text(control_frame, height=8, width=40, font=("Consolas", 10))
        self.text_input.pack(fill=tk.X, pady=5)

        tk.Button(control_frame, text="▶ 解析并绘图", command=self.load_from_text, bg="#e1f5fe",
                  font=("Microsoft YaHei", 10)).pack(fill=tk.X, pady=2)
        tk.Button(control_frame, text="清空", command=lambda: self.text_input.delete("1.0", tk.END),
                  font=("Microsoft YaHei", 10)).pack(fill=tk.X, pady=2)

        # 3. 阈值控制
        line_frame = tk.LabelFrame(self.left_panel, text="2. 分类设置", padx=10, pady=10, fg="blue",
                                   font=("Microsoft YaHei", 10, "bold"))
        line_frame.pack(fill=tk.X, pady=10)
        tk.Checkbutton(line_frame, text="启用鼠标点击绘图", variable=self.enable_click_mode,
                       font=("Microsoft YaHei", 10)).pack(fill=tk.X)

        input_frame = tk.Frame(line_frame)
        input_frame.pack(fill=tk.X, pady=5)
        self.line_entry = tk.Entry(input_frame, width=8, font=("Microsoft YaHei", 10))
        self.line_entry.pack(side=tk.LEFT, padx=5)
        self.line_entry.bind('<Return>', lambda event: self.add_threshold_manual())

        tk.Button(input_frame, text="添加Y轴线", command=self.add_threshold_manual, font=("Microsoft YaHei", 10)).pack(
            side=tk.LEFT)
        tk.Button(input_frame, text="清除所有", command=self.clear_thresholds, bg="#ffdddd",
                  font=("Microsoft YaHei", 10)).pack(side=tk.RIGHT)

        self.threshold_list_label = tk.Label(line_frame, text="当前阈值: 无", fg="red", wraplength=350,
                                             font=("Microsoft YaHei", 10))
        self.threshold_list_label.pack(fill=tk.X)

    def setup_results_tab(self):
        # 在 "分类结果与报告" 主标签页中，再放一个内部 Notebook
        # 用来切换 "表格操作区" 和 "纯文本报告"
        self.inner_notebook = ttk.Notebook(self.tab_results_container)
        self.inner_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- 内部子标签 1: 表格 ---
        self.tab_table = tk.Frame(self.inner_notebook)
        self.inner_notebook.add(self.tab_table, text="表格操作区")

        # 表格工具条
        btn_bar = tk.Frame(self.tab_table, bg="#ddd")
        btn_bar.pack(fill=tk.X, side=tk.TOP)
        tk.Button(btn_bar, text="➕ 新增", command=self.open_add_data_dialog, bg="#ccffcc").pack(side=tk.LEFT, padx=2,
                                                                                                pady=2)
        tk.Button(btn_bar, text="❌ 删除", command=self.delete_selected_data, bg="#ffcccc", fg="red").pack(side=tk.LEFT,
                                                                                                          padx=2,
                                                                                                          pady=2)
        tk.Label(btn_bar, text=" | ✋拖拽排序 | ", bg="#ddd", fg="blue").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_bar, text="🚩 标记状态", command=self.toggle_mark, bg="pink").pack(side=tk.LEFT, padx=5)

        # Treeview 构建
        columns = ('Label', 'Status', 'Y', 'X')
        self.tree = ttk.Treeview(self.tab_table, columns=columns, show='tree headings',
                                 displaycolumns=('Label', 'Status'), selectmode='extended')
        self.tree.heading('#0', text='类别 (右键重命名)')
        self.tree.column('#0', width=180, anchor='w')
        self.tree.heading('Label', text='名称')
        self.tree.column('Label', width=220)
        self.tree.heading('Status', text='状态')
        self.tree.column('Status', width=80, anchor='center')

        scrollbar = ttk.Scrollbar(self.tab_table, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # 绑定事件
        self.tree.bind("<Button-3>", self.on_right_click)
        self.tree.bind("<ButtonPress-1>", self.on_drag_start)
        self.tree.bind("<B1-Motion>", self.on_drag_motion)
        self.tree.bind("<ButtonRelease-1>", self.on_drag_release)
        self.tree.bind("<Delete>", lambda event: self.delete_selected_data())

        # --- 内部子标签 2: 文本 ---
        self.tab_text = tk.Frame(self.inner_notebook)
        self.inner_notebook.add(self.tab_text, text="纯文本报告")

        report_bar = tk.Frame(self.tab_text, bg="#ddd")
        report_bar.pack(fill=tk.X, side=tk.TOP)
        tk.Button(report_bar, text="💾 导出 TXT", command=self.export_txt_file, bg="#e1f5fe").pack(side=tk.LEFT, padx=5,
                                                                                                  pady=2)
        tk.Button(report_bar, text="繁 -> 简", command=self.convert_to_simplified, bg="#fff0f5").pack(side=tk.LEFT,
                                                                                                      padx=2)
        tk.Button(report_bar, text="简 -> 繁", command=self.convert_to_traditional, bg="#fff0f5").pack(side=tk.LEFT,
                                                                                                       padx=2)

        text_container = tk.Frame(self.tab_text)
        text_container.pack(fill=tk.BOTH, expand=True)
        text_scrollbar = ttk.Scrollbar(text_container, orient=tk.VERTICAL)
        self.report_text = tk.Text(text_container, yscrollcommand=text_scrollbar.set)
        text_scrollbar.config(command=self.report_text.yview)
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.report_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def setup_plot_tab(self):
        # 标签页 2: 绘图
        # 直接把 Matplotlib Canvas 放入 self.tab_plot_container
        self.fig, self.ax = plt.subplots(figsize=(6, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab_plot_container)
        self.canvas.draw()
        self.canvas.mpl_connect('button_press_event', self.on_plot_click)

        toolbar = NavigationToolbar2Tk(self.canvas, self.tab_plot_container)
        toolbar.update()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    # ===============================================
    # 动态字号调整
    # ===============================================
    def adjust_font_size(self, delta):
        new_size = self.current_font_size + delta
        if new_size < 8: new_size = 8
        if new_size > 30: new_size = 30
        self.current_font_size = new_size
        self.lbl_size_display.config(text=f"当前: {new_size}")
        self.apply_font_style()

    def apply_font_style(self):
        size = self.current_font_size
        row_height = int(size * 2.5)

        style = ttk.Style()
        style.theme_use('clam')

        # 配置 Treeview
        style.configure("Treeview", font=("Microsoft YaHei", size), rowheight=row_height)
        style.configure("Treeview.Heading", font=("Microsoft YaHei", size, "bold"))

        self.tree.tag_configure('normal', font=('Microsoft YaHei', size))
        self.tree.tag_configure('marked', font=('Microsoft YaHei', size, 'bold'),
                                foreground='red', background='#FFFFE0')

        # 配置 Text
        self.report_text.configure(font=("Microsoft YaHei", size))

    # ===============================================
    # 业务逻辑 (保持原有逻辑)
    # ===============================================
    def open_add_data_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("新增数据")
        dialog.geometry("300x220")

        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 150
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 110
        dialog.geometry(f"+{x}+{y}")

        def_y_val = ""
        def_x_val = ""
        selected_item = self.tree.selection()
        if selected_item:
            item_id = selected_item[0]
            if self.tree.parent(item_id):
                vals = self.tree.item(item_id, 'values')
                try:
                    def_y_val = str(float(vals[2]) + 1)
                    def_x_val = str(float(vals[3]) + 1)
                except:
                    pass

        tk.Label(dialog, text="名称 (Label):", font=("Microsoft YaHei", 10)).pack(pady=(10, 2))
        entry_name = tk.Entry(dialog, font=("Microsoft YaHei", 10))
        entry_name.pack()

        tk.Label(dialog, text="Y 轴数值 (选填):", fg="gray", font=("Microsoft YaHei", 9)).pack(pady=2)
        entry_y = tk.Entry(dialog, font=("Microsoft YaHei", 10))
        entry_y.pack()
        if def_y_val: entry_y.insert(0, def_y_val)

        tk.Label(dialog, text="X 轴数值 (选填):", fg="gray", font=("Microsoft YaHei", 9)).pack(pady=2)
        entry_x = tk.Entry(dialog, font=("Microsoft YaHei", 10))
        entry_x.pack()
        if def_x_val: entry_x.insert(0, def_x_val)

        def confirm_add():
            name = entry_name.get().strip()
            y_str = entry_y.get().strip()
            x_str = entry_x.get().strip()
            if not name: name = f"新增数据_{random.randint(100, 999)}"
            try:
                y_val = float(y_str) if y_str else 0.0
                x_val = float(x_str) if x_str else 0.0
                new_row = pd.DataFrame([[name, y_val, x_val]], columns=['Label', 'Y', 'X'])

                insert_index = -1
                current_selection = self.tree.selection()
                if current_selection:
                    try:
                        c_item_id = current_selection[0]
                        if self.tree.parent(c_item_id):
                            vals = self.tree.item(c_item_id, 'values')
                            sel_label = vals[0]
                            sel_y, sel_x = float(vals[2]), float(vals[3])
                            matches = self.df.index[
                                (self.df['Label'] == sel_label) & (abs(self.df['Y'] - sel_y) < 1e-9) & (
                                        abs(self.df['X'] - sel_x) < 1e-9)].tolist()
                            if matches: insert_index = matches[0] + 1
                    except Exception:
                        pass

                if self.df.empty:
                    self.df = new_row
                elif insert_index != -1 and insert_index <= len(self.df):
                    self.df = pd.concat([self.df.iloc[:insert_index], new_row, self.df.iloc[insert_index:]],
                                        ignore_index=True)
                else:
                    self.df = pd.concat([self.df, new_row], ignore_index=True)

                self.refresh_all()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("错误", "数值格式不正确", parent=dialog)

        tk.Button(dialog, text="✅ 确认添加", command=confirm_add, bg="#ccffcc", width=15,
                  font=("Microsoft YaHei", 10)).pack(pady=15)

    def export_txt_file(self):
        raw_content = self.report_text.get("1.0", tk.END).strip()
        if not raw_content:
            messagebox.showinfo("提示", "文本框是空的")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                                 filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if not file_path: return
        lines = raw_content.split('\n')
        filtered_lines = []
        for line in lines:
            line_str = line.strip()
            if line_str.startswith("【") and "】" in line_str: continue
            filtered_lines.append(line)
        final_content = "\n".join(filtered_lines)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(final_content)
            messagebox.showinfo("成功", "文件导出成功！")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {e}")

    def convert_text(self, mode):
        if not HAS_OPENCC:
            messagebox.showwarning("缺少库", "检测到未安装 opencc 库。\n请运行: pip install opencc-python-reimplemented")
            return
        current_content = self.report_text.get("1.0", tk.END).strip()
        if not current_content: return
        try:
            converter = opencc.OpenCC(mode)
            converted_content = converter.convert(current_content)
            self.report_text.delete("1.0", tk.END)
            self.report_text.insert(tk.END, converted_content)
        except Exception as e:
            messagebox.showerror("转换错误", str(e))

    def convert_to_traditional(self):
        self.convert_text('s2t')

    def convert_to_simplified(self):
        self.convert_text('t2s')

    def generate_report_from_tree(self):
        self.report_text.delete("1.0", tk.END)
        report_content = ""
        categories = self.tree.get_children("")

        for cat_id in categories:
            cat_text_raw = self.tree.item(cat_id, "text")
            if "(" in cat_text_raw:
                cat_name_clean = cat_text_raw.replace("📂 ", "").rsplit(" (", 1)[0]
            else:
                cat_name_clean = cat_text_raw.replace("📂 ", "")

            children = self.tree.get_children(cat_id)
            if not children: continue

            report_content += f"【{cat_name_clean}】:\n"

            prev_was_marked = False
            is_first_item = True

            for child_id in children:
                values = self.tree.item(child_id, "values")
                name = values[0]
                is_curr_marked = name in self.marked_labels

                prefix = ""
                if not is_first_item:
                    if prev_was_marked and is_curr_marked:
                        prefix = ""
                    else:
                        prefix = "\n"

                report_content += f"{prefix}{name}\n"
                prev_was_marked = is_curr_marked
                is_first_item = False

            report_content += "\n"

        self.report_text.insert(tk.END, report_content)

    def update_plot_view(self):
        self.ax.clear()
        self.ax.set_title("数据分布图")
        self.ax.set_xlabel("X 轴")
        self.ax.set_ylabel("Y 轴")
        self.ax.grid(True, linestyle='--', alpha=0.5)

        if not self.df.empty:
            mask_marked = self.df['Label'].isin(self.marked_labels)
            df_marked = self.df[mask_marked]
            df_normal = self.df[~mask_marked]

            if not df_normal.empty:
                self.ax.scatter(df_normal['X'], df_normal['Y'],
                                c='#1f77b4', s=80, edgecolors='white', zorder=5)

            if not df_marked.empty:
                self.ax.scatter(df_marked['X'], df_marked['Y'],
                                c='#ff0000', s=150, edgecolors='black', zorder=10)

            for _, row in self.df.iterrows():
                is_marked = row['Label'] in self.marked_labels
                # 图表字体固定，不随界面字号缩放
                font_props = {'color': 'red', 'weight': 'bold', 'fontsize': 10} if is_marked else {'color': 'black',
                                                                                                   'fontsize': 9}
                z_text = 10 if is_marked else 5

                self.ax.annotate(str(row['Label']), (row['X'], row['Y']),
                                 textcoords="offset points", xytext=(0, 8), ha='center',
                                 zorder=z_text, **font_props)

        colors_line = ['#d62728', '#ff7f0e', '#2ca02c', '#9467bd']
        for i, y in enumerate(self.thresholds):
            c = colors_line[i % len(colors_line)]
            self.ax.axhline(y=y, color=c, lw=2, zorder=1)
            self.ax.text(self.ax.get_xlim()[0], y, f' Y={y}', color="white", backgroundcolor=c, fontweight='bold')

        self.canvas.draw()

    def delete_selected_data(self):
        selected_items = self.tree.selection()
        if not selected_items: return
        target_items = [i for i in selected_items if self.tree.parent(i)]
        if not target_items: return
        if not messagebox.askyesno("确认删除", f"确定要删除选中的 {len(target_items)} 条数据吗？"): return
        to_delete_list = []
        for item_id in target_items:
            values = self.tree.item(item_id, 'values')
            try:
                to_delete_list.append((values[0], float(values[2]), float(values[3])))
            except ValueError:
                continue
        for label, y, x in to_delete_list:
            condition = (self.df['Label'] == label) & (abs(self.df['Y'] - y) < 1e-9) & (abs(self.df['X'] - x) < 1e-9)
            self.df = self.df[~condition]
        self.refresh_all()

    def on_drag_start(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id: return
        if not self.tree.parent(item_id): return
        self.drag_source_item = item_id

    def on_drag_motion(self, event):
        target_id = self.tree.identify_row(event.y)
        if target_id: self.tree.selection_set(target_id)

    def on_drag_release(self, event):
        if not self.drag_source_item: return
        target_id = self.tree.identify_row(event.y)
        if not target_id:
            self.drag_source_item = None
            return
        source = self.drag_source_item
        target = target_id
        if source == target:
            self.drag_source_item = None
            return
        source_parent = self.tree.parent(source)
        target_parent = self.tree.parent(target)
        if target_parent == source_parent:
            target_index = self.tree.index(target)
            self.tree.move(source, source_parent, target_index)
            self.generate_report_from_tree()
        elif target == source_parent:
            self.tree.move(source, source_parent, 0)
            self.generate_report_from_tree()
        self.drag_source_item = None

    def on_right_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id: return
        parent_id = self.tree.parent(item_id)
        if not parent_id:
            self.tree.selection_set(item_id)
            menu = Menu(self.root, tearoff=0)
            menu.add_command(label="✏️ 重命名此分类...", command=lambda: self.rename_category(item_id))
            menu.post(event.x_root, event.y_root)
        else:
            if item_id not in self.tree.selection():
                self.tree.selection_set(item_id)
            self.toggle_mark()

    def rename_category(self, item_id):
        current_text = self.tree.item(item_id, "text")
        if "(" in current_text:
            default_val = current_text.replace("📂 ", "").rsplit(" (", 1)[0]
        else:
            default_val = current_text.replace("📂 ", "")
        all_roots = self.tree.get_children("")
        try:
            cat_index = all_roots.index(item_id)
        except ValueError:
            return
        new_name = simpledialog.askstring("重命名分类", f"请输入新的分类名称:", parent=self.root,
                                          initialvalue=default_val)
        if new_name:
            self.custom_category_names[cat_index] = new_name
            self.classify_and_display()

    def toggle_mark(self):
        selected_items = self.tree.selection()
        if not selected_items: return
        target_items = [i for i in selected_items if self.tree.parent(i)]
        if not target_items: return
        any_unmarked = False
        for item_id in target_items:
            label_name = self.tree.item(item_id, 'values')[0]
            if label_name not in self.marked_labels:
                any_unmarked = True;
                break
        for item_id in target_items:
            values = self.tree.item(item_id, 'values')
            label_name = values[0]
            if any_unmarked:
                self.marked_labels.add(label_name)
                self.tree.item(item_id, tags=('marked',))
                self.tree.set(item_id, "Status", "✅ 已标记")
            else:
                if label_name in self.marked_labels: self.marked_labels.remove(label_name)
                self.tree.item(item_id, tags=('normal',))
                self.tree.set(item_id, "Status", "")
        self.generate_report_from_tree()
        self.update_plot_view()

    def on_plot_click(self, event):
        if not self.enable_click_mode.get(): return
        if event.inaxes != self.ax: return
        click_y = event.ydata
        if event.button == 1:
            self.add_threshold_value(round(click_y, 1))
        elif event.button == 3 and self.thresholds:
            closest = min(self.thresholds, key=lambda x: abs(x - click_y))
            if abs(closest - click_y) < ((self.ax.get_ylim()[1] - self.ax.get_ylim()[0]) * 0.05):
                self.thresholds.remove(closest)
                self.refresh_all()

    def add_threshold_manual(self):
        try:
            val = float(self.line_entry.get())
            self.add_threshold_value(val)
            self.line_entry.delete(0, tk.END)
        except:
            messagebox.showwarning("错误", "请输入数字")

    def add_threshold_value(self, val):
        if val not in self.thresholds:
            self.thresholds.append(val)
            self.thresholds.sort()
            self.refresh_all()

    def clear_thresholds(self):
        self.thresholds = []
        self.marked_labels.clear()
        self.custom_category_names.clear()
        self.refresh_all()

    def refresh_all(self):
        self.update_threshold_label()
        self.update_plot_view()
        self.classify_and_display()

    def update_threshold_label(self):
        text = " | ".join([str(t) for t in self.thresholds])
        self.threshold_list_label.config(text=f"当前阈值: {text if text else '无'}")

    def load_from_text(self):
        content = self.text_input.get("1.0", tk.END).strip()
        if not content: return
        data = []
        for line in content.split('\n'):
            parts = re.split(r'[|\t,，]+', line.strip())
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) >= 3:
                try:
                    data.append([parts[0], float(parts[1]), float(parts[2])])
                except:
                    continue
        if data:
            self.df = pd.DataFrame(data, columns=['Label', 'Y', 'X'])
            self.refresh_all()
            # 自动切换到绘图标签页查看结果
            self.main_notebook.select(self.tab_plot_container)
        else:
            messagebox.showerror("错误", "无法解析数据")

    def classify_and_display(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        if self.df.empty: return
        raw_categories = []
        if not self.thresholds:
            raw_categories.append(("全部数据", self.df))
        else:
            sorted_t = sorted(self.thresholds)
            raw_categories.append((f"低于 {sorted_t[0]}", self.df[self.df['Y'] < sorted_t[0]]))
            for i in range(len(sorted_t) - 1):
                raw_categories.append((f"{sorted_t[i]} ~ {sorted_t[i + 1]}",
                                       self.df[(self.df['Y'] >= sorted_t[i]) & (self.df['Y'] < sorted_t[i + 1])]))
            raw_categories.append((f"高于 {sorted_t[-1]}", self.df[self.df['Y'] >= sorted_t[-1]]))
        for index, (default_name, sub_df) in enumerate(raw_categories):
            if sub_df.empty: continue
            default_seq_name = f"第 {index + 1} 行"
            display_name = self.custom_category_names.get(index, default_seq_name)
            parent_id = self.tree.insert("", "end", text=f"📂 {display_name} ({len(sub_df)}个)", open=True)
            for _, row in sub_df.iterrows():
                is_marked = row['Label'] in self.marked_labels
                tag = 'marked' if is_marked else 'normal'
                status_text = "✅ 已标记" if is_marked else ""
                self.tree.insert(parent_id, "end", values=(row['Label'], status_text, row['Y'], row['X']), tags=(tag,))
        self.generate_report_from_tree()


if __name__ == "__main__":
    root = tk.Tk()
    app = DataClassifierApp(root)
    root.mainloop()