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

# === 尝试导入简繁转换库 ===
try:
    import opencc
    HAS_OPENCC = True
except ImportError:
    HAS_OPENCC = False

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
            except: pass
    if not font_loaded:
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']

configure_styles_force()

# ==========================================

class DataClassifierApp:
    def __init__(self, root):
        self.root = root
        self.root.title("数据分类工具 - 全功能终极版")
        self.root.geometry("1400x900")

        # 默认字号
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
        # 0. 全局字号下拉框
        settings_frame = tk.LabelFrame(self.left_panel, text="0. 全局设置", padx=10, pady=8, font=("", 10, "bold"), fg="purple")
        settings_frame.pack(fill=tk.X, pady=5)
        tk.Label(settings_frame, text="界面字号:").pack(side=tk.LEFT, padx=(0, 5))
        font_sizes = [str(i) for i in range(8, 31)]
        self.combo_font = ttk.Combobox(settings_frame, values=font_sizes, width=5, state="readonly")
        self.combo_font.set(str(self.current_font_size))
        self.combo_font.pack(side=tk.LEFT)
        self.combo_font.bind("<<ComboboxSelected>>", self.on_font_combo_change)

        # 1. 数据导入
        control_frame = tk.LabelFrame(self.left_panel, text="1. 数据导入", padx=10, pady=10)
        control_frame.pack(fill=tk.X, pady=5)
        self.text_input = tk.Text(control_frame, height=8, width=40, font=("Consolas", 10))
        self.text_input.pack(fill=tk.X, pady=5)
        tk.Button(control_frame, text="📋 粘贴并解析数据", command=self.load_from_text, bg="#e1f5fe", font=("", 10, "bold")).pack(fill=tk.X)

        # 2. 交互模式
        mode_frame = tk.LabelFrame(self.left_panel, text="2. 绘图模式切换", padx=10, pady=10, fg="blue")
        mode_frame.pack(fill=tk.X, pady=10)
        tk.Radiobutton(mode_frame, text="🖱️ 直线模式 (左键加线/右键删线)", variable=self.enable_lasso_mode, value=False, command=self.update_plot_view).pack(anchor="w")
        tk.Radiobutton(mode_frame, text="🎯 圈选模式 (画圈提取数据)", variable=self.enable_lasso_mode, value=True, command=self.update_plot_view).pack(anchor="w")
        
        # 3. 重置
        op_frame = tk.LabelFrame(self.left_panel, text="3. 状态重置", padx=10, pady=10)
        op_frame.pack(fill=tk.X, pady=10)
        tk.Button(op_frame, text="🗑️ 清空所有数据及分类", command=self.reset_all, bg="#ffdddd").pack(fill=tk.X)

    def setup_results_tab(self):
        self.inner_nb = ttk.Notebook(self.tab_res)
        self.inner_nb.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # --- 子页1：分类目录树 ---
        self.tab_tree = tk.Frame(self.inner_nb)
        self.inner_nb.add(self.tab_tree, text="分类目录树")
        
        # 🟢 增加/删除工具栏
        tree_btn_bar = tk.Frame(self.tab_tree, bg="#ddd")
        tree_btn_bar.pack(fill=tk.X, side=tk.TOP)
        tk.Button(tree_btn_bar, text="➕ 新增数据", command=self.open_add_data_dialog, bg="#ccffcc").pack(side=tk.LEFT, padx=5, pady=2)
        tk.Button(tree_btn_bar, text="❌ 删除选中", command=self.delete_selected_data, bg="#ffcccc").pack(side=tk.LEFT, padx=5, pady=2)
        tk.Label(tree_btn_bar, text="| 右键条目标记, 右键文件夹重命名 |", bg="#ddd", fg="#666", font=("", 9)).pack(side=tk.LEFT, padx=10)

        self.tree = ttk.Treeview(self.tab_tree, columns=('Label', 'Status', 'Index'), show='tree headings', displaycolumns=('Label', 'Status'))
        self.tree.heading('#0', text='分类目录'); self.tree.heading('Label', text='条目名称'); self.tree.heading('Status', text='标记')
        self.tree.column('Index', width=0, stretch=False)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<Button-3>", self.on_right_click)

        # --- 子页2：文本报告 ---
        self.tab_report = tk.Frame(self.inner_nb)
        self.inner_nb.add(self.tab_report, text="文本报告")
        
        btn_bar = tk.Frame(self.tab_report, bg="#ddd")
        btn_bar.pack(fill=tk.X, side=tk.TOP)
        tk.Button(btn_bar, text="💾 导出 TXT", command=self.export_txt_file, bg="#e1f5fe").pack(side=tk.LEFT, padx=5, pady=2)
        tk.Button(btn_bar, text="繁 -> 简", command=self.convert_to_simplified, bg="#fff0f5").pack(side=tk.LEFT, padx=2)
        tk.Button(btn_bar, text="简 -> 繁", command=self.convert_to_traditional, bg="#fff0f5").pack(side=tk.LEFT, padx=2)

        self.report_text = tk.Text(self.tab_report)
        self.report_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def setup_plot_tab(self):
        self.fig, self.ax = plt.subplots(figsize=(6, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab_plt)
        self.canvas.mpl_connect('button_press_event', self.on_plot_click)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    # ===============================================
    # ➕ 新增 & ❌ 删除 逻辑
    # ===============================================
    def open_add_data_dialog(self):
        """弹出对话框手动添加一条数据"""
        dialog = tk.Toplevel(self.root)
        dialog.title("手动新增数据")
        dialog.geometry("300x250")
        
        # 获取选中的数据作为默认值
        selected_items = self.tree.selection()
        default_y = ""
        default_x = ""
        
        if selected_items:
            # 找到第一个数据条目（不是文件夹）
            for item in selected_items:
                if self.tree.parent(item):  # 是数据条目，不是根节点
                    idx = int(self.tree.item(item, 'values')[2])
                    if idx < len(self.df):
                        selected_y = self.df.loc[idx, 'Y']
                        selected_x = self.df.loc[idx, 'X']
                        default_y = str(selected_y + 1)  # Y值加1
                        default_x = str(selected_x)      # X值保持不变
                        break
        
        tk.Label(dialog, text="数据名称:").pack(pady=(10,0))
        name_entry = tk.Entry(dialog)
        name_entry.pack(pady=5)
        
        tk.Label(dialog, text="Y 轴数值:").pack()
        y_entry = tk.Entry(dialog)
        y_entry.insert(0, default_y)  # 设置默认值
        y_entry.pack(pady=5)
        
        tk.Label(dialog, text="X 轴数值:").pack()
        x_entry = tk.Entry(dialog)
        x_entry.insert(0, default_x)  # 设置默认值
        x_entry.pack(pady=5)

        def save_new():
            name = name_entry.get().strip()
            try:
                y_val = float(y_entry.get())
                x_val = float(x_entry.get())
                if not name: name = "未命名"
                
                # 找到选中数据的位置，在其后插入新数据
                insert_position = len(self.df)  # 默认插入到末尾
                if selected_items:
                    for item in selected_items:
                        if self.tree.parent(item):  # 是数据条目
                            selected_idx = int(self.tree.item(item, 'values')[2])
                            insert_position = selected_idx + 1
                            break
                
                # 创建新行并插入到指定位置
                new_row = pd.DataFrame([[name, y_val, x_val]], columns=['Label', 'Y', 'X'])
                
                if insert_position >= len(self.df):
                    # 插入到末尾
                    self.df = pd.concat([self.df, new_row], ignore_index=True)
                else:
                    # 插入到指定位置
                    df_before = self.df.iloc[:insert_position]
                    df_after = self.df.iloc[insert_position:]
                    self.df = pd.concat([df_before, new_row, df_after], ignore_index=True)
                    
                    # 更新所有受影响的索引
                    # 标记索引需要更新
                    new_marked = set()
                    for idx in self.marked_indices:
                        if idx >= insert_position:
                            new_marked.add(idx + 1)
                        else:
                            new_marked.add(idx)
                    self.marked_indices = new_marked
                    
                    # 圈选分类索引需要更新
                    for cat in self.category_list:
                        new_indices = set()
                        for idx in cat['indices']:
                            if idx >= insert_position:
                                new_indices.add(idx + 1)
                            else:
                                new_indices.add(idx)
                        cat['indices'] = new_indices
                
                self.refresh_all()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("错误", "Y和X必须是数字")

        tk.Button(dialog, text="确认保存", command=save_new, bg="#ccffcc").pack(pady=10)

    def delete_selected_data(self):
        """删除选中的数据条目"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("提示", "请先在下方列表中选择要删除的条目")
            return
        
        # 过滤出条目（parent不为空的才是数据行，根节点是文件夹）
        indices_to_del = []
        for item in selected_items:
            if self.tree.parent(item):
                idx = int(self.tree.item(item, 'values')[2])
                indices_to_del.append(idx)
        
        if not indices_to_del:
            return

        if messagebox.askyesno("确认", f"确定要删除选中的 {len(indices_to_del)} 条数据吗？"):
            # 从 DataFrame 中移除
            self.df = self.df.drop(indices_to_del).reset_index(drop=True)
            # 清除标记
            self.marked_indices.clear()
            # 重新分配圈选索引（因为索引变了，简单起见清空圈选）
            self.category_list = []
            self.refresh_all()

    # ===============================================
    # 🎯 数据解析 & 转换
    # ===============================================
    def load_from_text(self):
        try:
            clipboard_content = self.root.clipboard_get()
            if clipboard_content and clipboard_content.strip():
                self.text_input.delete("1.0", tk.END)
                self.text_input.insert(tk.END, clipboard_content)
        except: pass
        raw = self.text_input.get("1.0", tk.END).strip()
        data = []
        for line in raw.split('\n'):
            parts = re.split(r'[|\t,，]+', line.strip())
            if len(parts) >= 3:
                try: data.append([parts[0].strip(), float(parts[1]), float(parts[2])])
                except: continue
        if data:
            self.df = pd.DataFrame(data, columns=['Label', 'Y', 'X'])
            self.reset_all(); self.refresh_all(); self.main_notebook.select(self.tab_plt)

    def convert_text(self, mode):
        if not HAS_OPENCC:
            messagebox.showwarning("提示", "请安装 opencc-python-reimplemented")
            return
        txt = self.report_text.get("1.0", tk.END).strip()
        if not txt: return
        try:
            converter = opencc.OpenCC(mode)
            self.report_text.delete("1.0", tk.END); self.report_text.insert(tk.END, converter.convert(txt))
        except: pass

    def convert_to_simplified(self): self.convert_text('t2s')
    def convert_to_traditional(self): self.convert_text('s2t')

    # ===============================================
    # 交互绘图逻辑
    # ===============================================
    def on_font_combo_change(self, event):
        self.current_font_size = int(self.combo_font.get())
        self.apply_font_style(); self.refresh_all()

    def on_plot_click(self, event):
        if event.inaxes != self.ax: return
        if not self.enable_lasso_mode.get():
            if event.button == 1:
                val = round(event.ydata, 1)
                if val not in self.thresholds:
                    self.thresholds.append(val); self.thresholds.sort(); self.refresh_all()
            elif event.button == 3 and self.thresholds:
                closest = min(self.thresholds, key=lambda x: abs(x - event.ydata))
                if abs(closest - event.ydata) < (self.ax.get_ylim()[1] - self.ax.get_ylim()[0]) * 0.05:
                    self.thresholds.remove(closest); self.refresh_all()

    def on_lasso_select(self, verts):
        if self.df.empty: return
        path = Path(verts)
        inside = path.contains_points(self.df[['X', 'Y']].values)
        new_indices = set(self.df.index[inside].tolist())
        if new_indices:
            for cat in self.category_list: cat['indices'] = cat['indices'] - new_indices
            cat_id = len(self.category_list) + 1
            self.category_list.append({'name': f"圈选提取 {cat_id}", 'indices': new_indices, 'color': self.color_cycle[(cat_id-1)%len(self.color_cycle)]})
            self.refresh_all()

    def update_plot_view(self):
        self.ax.clear(); self.ax.set_title("数据交互绘图区")
        if not self.df.empty:
            colors = ['#1f77b4'] * len(self.df); sizes = [60] * len(self.df)
            for i in self.df.index:
                if i in self.marked_indices: colors[i], sizes[i] = 'red', 120
                else:
                    for cat in self.category_list:
                        if i in cat['indices']: colors[i], sizes[i] = cat['color'], 100; break
            self.ax.scatter(self.df['X'], self.df['Y'], c=colors, s=sizes, zorder=5)
            for idx, row in self.df.iterrows():
                m = idx in self.marked_indices
                self.ax.annotate(row['Label'], (row['X'], row['Y']), xytext=(0,5), textcoords="offset points", ha='center', fontsize=9, color='red' if m else 'black', weight='bold' if m else 'normal')
        for y in self.thresholds: self.ax.axhline(y=y, color='blue', linestyle='--', alpha=0.5)
        if self.enable_lasso_mode.get(): self.lasso = LassoSelector(self.ax, onselect=self.on_lasso_select, props={'color': 'red', 'linewidth': 1.5})
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
                self.tree.insert(pid, "end", values=(self.df.loc[idx, 'Label'], "✅ 已标记" if m else "", idx), tags=('marked' if m else ''))
                categorized_idx.add(idx)
        rem_df = self.df.drop(list(categorized_idx))
        if not rem_df.empty:
            t_sorted = sorted(self.thresholds)
            line_cats = []
            if not t_sorted: line_cats.append(("未分类数据区", rem_df))
            else:
                line_cats.append((f"低于 {t_sorted[0]}", rem_df[rem_df['Y'] < t_sorted[0]]))
                for i in range(len(t_sorted)-1):
                    line_cats.append((f"{t_sorted[i]} ~ {t_sorted[i+1]}", rem_df[(rem_df['Y'] >= t_sorted[i]) & (rem_df['Y'] < t_sorted[i+1])]))
                line_cats.append((f"高于 {t_sorted[-1]}", rem_df[rem_df['Y'] >= t_sorted[-1]]))
            for name, sub in line_cats:
                if sub.empty: continue
                d_name = self.custom_cat_names.get(name, name)
                pid = self.tree.insert("", "end", text=f"📂 {d_name}", open=True)
                for r_idx, r in sub.iterrows():
                    m = r_idx in self.marked_indices
                    self.tree.insert(pid, "end", values=(r['Label'], "✅ 已标记" if m else "", r_idx), tags=('marked' if m else ''))
        self.generate_report_from_tree()

    def generate_report_from_tree(self):
        self.report_text.delete("1.0", tk.END); content = ""
        for pid in self.tree.get_children(""):
            title = self.tree.item(pid, "text").replace("📂 ", ""); children = self.tree.get_children(pid)
            if not children: continue
            content += f"【{title}】:\n"
            prev_m = None
            for i, cid in enumerate(children):
                vals = self.tree.item(cid, "values"); name, idx = vals[0], int(vals[2]); curr_m = idx in self.marked_indices
                if curr_m:
                    if prev_m is False or prev_m is None: content += "\n"
                    content += f"{name}\n"
                else: content += f"\n{name}\n\n"
                if curr_m:
                    next_m = False
                    if i < len(children) - 1: next_m = int(self.tree.item(children[i+1], "values")[2]) in self.marked_indices
                    if not next_m: content += "\n"
                prev_m = curr_m
            content += "\n"
        self.report_text.insert(tk.END, re.sub(r'\n{3,}', '\n\n', content).strip() + "\n")

    def apply_font_style(self):
        s = self.current_font_size
        ttk.Style().configure("Treeview", font=("Microsoft YaHei", s), rowheight=int(s*2.5))
        self.tree.tag_configure('marked', foreground='red', font=("", s, "bold"))
        self.report_text.configure(font=("Microsoft YaHei", s))

    def on_right_click(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            if self.tree.parent(iid): 
                idx = int(self.tree.item(iid, 'values')[2])
                if idx in self.marked_indices: self.marked_indices.remove(idx)
                else: self.marked_indices.add(idx)
                self.refresh_all()
            else: 
                old = self.tree.item(iid, "text").replace("📂 ", "")
                new = simpledialog.askstring("重命名", "重命名分类:", initialvalue=old)
                if new:
                    idx = self.tree.get_children("").index(iid)
                    if idx < len(self.category_list): self.category_list[idx]['name'] = new
                    else: self.custom_cat_names[old] = new
                    self.refresh_all()

    def refresh_all(self): self.update_plot_view(); self.classify_and_display()

    def reset_all(self):
        self.thresholds = []; self.category_list = []; self.marked_indices = set(); self.custom_cat_names = {}; self.refresh_all()

    def export_txt_file(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path:
            # 导出文本报告区域中的内容，但过滤掉分类标题
            raw = self.report_text.get("1.0", tk.END)
            filtered = [l for l in raw.splitlines() if not (l.strip().startswith("【") and "】" in l)]
            with open(path, "w", encoding="utf-8") as f: 
                f.write("\n".join(filtered).strip())

if __name__ == "__main__":
    root = tk.Tk(); app = DataClassifierApp(root); root.mainloop()