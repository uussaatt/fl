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
# 🎨 现代化主题配色
# ==========================================
THEME_COLORS = {
    'primary': '#2E86AB',      # 主色调 - 蓝色
    'secondary': '#A23B72',    # 次要色 - 紫红色
    'accent': '#F18F01',       # 强调色 - 橙色
    'success': '#C73E1D',      # 成功色 - 红色
    'bg_light': '#F8F9FA',     # 浅背景
    'bg_dark': '#343A40',      # 深背景
    'text_primary': '#212529', # 主文字
    'text_secondary': '#6C757D', # 次要文字
    'border': '#DEE2E6',       # 边框色
    'hover': '#E9ECEF'         # 悬停色
}

# ==========================================
# 🛑 字体配置 (Windows 环境)
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
        self.root.title("🎯 智能数据分类工具 v2.0")
        self.root.geometry("1500x950")
        self.root.configure(bg=THEME_COLORS['bg_light'])
        
        # 设置窗口图标和样式
        self.setup_window_style()
        
        # 应用现代化主题
        self.setup_modern_theme()

        self.current_font_size = 11
        self.df = pd.DataFrame(columns=['Label', 'Y', 'X'])
        self.thresholds = []
        self.category_list = []
        self.marked_indices = set()
        self.custom_cat_names = {}
        self.drag_source_item = None

        self.enable_lasso_mode = tk.BooleanVar(value=False)
        self.color_cycle = ['#E74C3C', '#2ECC71', '#F39C12', '#9B59B6', '#3498DB', '#1ABC9C']
        self.lasso = None

        # --- 现代化界面布局 ---
        self.create_main_layout()
        
        # 初始化各个模块
        self.setup_left_panel()
        self.setup_results_tab()
        self.setup_plot_tab()
        self.apply_font_style()

    def setup_window_style(self):
        """设置窗口样式"""
        try:
            # 尝试设置窗口透明度和现代化外观
            self.root.attributes('-alpha', 0.98)
        except:
            pass
    
    def setup_modern_theme(self):
        """设置现代化主题"""
        style = ttk.Style()
        
        # 配置现代化的ttk样式
        style.theme_use('clam')
        
        # 自定义Notebook样式
        style.configure('Modern.TNotebook', 
                       background=THEME_COLORS['bg_light'],
                       borderwidth=0)
        style.configure('Modern.TNotebook.Tab',
                       background=THEME_COLORS['bg_light'],
                       foreground=THEME_COLORS['text_primary'],
                       padding=[20, 10],
                       font=('Microsoft YaHei', 10, 'bold'))
        style.map('Modern.TNotebook.Tab',
                 background=[('selected', THEME_COLORS['primary']),
                           ('active', THEME_COLORS['hover'])],
                 foreground=[('selected', 'white')])
        
        # 自定义Treeview样式
        style.configure('Modern.Treeview',
                       background='white',
                       foreground=THEME_COLORS['text_primary'],
                       fieldbackground='white',
                       borderwidth=1,
                       relief='solid')
        style.configure('Modern.Treeview.Heading',
                       background=THEME_COLORS['primary'],
                       foreground='white',
                       font=('Microsoft YaHei', 10, 'bold'))
        
        # 自定义Combobox样式
        style.configure('Modern.TCombobox',
                       fieldbackground='white',
                       background=THEME_COLORS['primary'],
                       foreground=THEME_COLORS['text_primary'])

    def create_main_layout(self):
        """创建主要布局"""
        # 创建主容器
        main_container = tk.Frame(self.root, bg=THEME_COLORS['bg_light'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # 左侧控制面板 - 现代化设计
        self.left_panel = tk.Frame(main_container, 
                                  width=450, 
                                  bg='white',
                                  relief='flat',
                                  bd=1)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
        self.left_panel.pack_propagate(False)
        
        # 添加左侧面板阴影效果
        shadow_frame = tk.Frame(main_container, bg='#E0E0E0', width=2)
        shadow_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        # 右侧主工作区
        self.right_panel = tk.Frame(main_container, bg='white', relief='flat', bd=1)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 现代化的Notebook
        self.main_notebook = ttk.Notebook(self.right_panel, style='Modern.TNotebook')
        self.main_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab_res = tk.Frame(self.main_notebook, bg='white')
        self.main_notebook.add(self.tab_res, text="📊 分类结果与报告")
        self.tab_plt = tk.Frame(self.main_notebook, bg='white')
        self.main_notebook.add(self.tab_plt, text="📈 交互绘图区")

    def setup_left_panel(self):
        # 添加标题栏
        title_frame = tk.Frame(self.left_panel, bg=THEME_COLORS['primary'], height=60)
        title_frame.pack(fill=tk.X, padx=0, pady=0)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame, 
                              text="🎯 控制面板", 
                              bg=THEME_COLORS['primary'], 
                              fg='white',
                              font=('Microsoft YaHei', 14, 'bold'))
        title_label.pack(expand=True)
        
        # 创建滚动容器
        canvas = tk.Canvas(self.left_panel, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.left_panel, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='white')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 0. 全局设置 - 现代化卡片设计
        settings_card = self.create_card(scrollable_frame, "⚙️ 全局设置", THEME_COLORS['secondary'])
        
        font_frame = tk.Frame(settings_card, bg='white')
        font_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(font_frame, text="界面字号:", bg='white', 
                font=('Microsoft YaHei', 10)).pack(side=tk.LEFT, padx=(0, 10))
        
        self.combo_font = ttk.Combobox(font_frame, 
                                      values=[str(i) for i in range(8, 31)], 
                                      width=8, 
                                      state="readonly",
                                      style='Modern.TCombobox')
        self.combo_font.set(str(self.current_font_size))
        self.combo_font.pack(side=tk.LEFT)
        self.combo_font.bind("<<ComboboxSelected>>", self.on_font_combo_change)

        # 1. 数据导入 - 现代化卡片
        import_card = self.create_card(scrollable_frame, "📥 数据导入", THEME_COLORS['primary'])
        
        self.text_input = tk.Text(import_card, 
                                 height=8, 
                                 font=("Consolas", 10),
                                 bg='#F8F9FA',
                                 relief='flat',
                                 bd=1,
                                 highlightthickness=1,
                                 highlightcolor=THEME_COLORS['primary'])
        self.text_input.pack(fill=tk.X, pady=(0, 10))
        
        import_btn = self.create_modern_button(import_card, 
                                              "📋 粘贴并解析数据", 
                                              self.load_from_text,
                                              THEME_COLORS['primary'])

        # 2. 交互模式 - 现代化卡片
        mode_card = self.create_card(scrollable_frame, "🎮 绘图模式", THEME_COLORS['accent'])
        
        mode_frame = tk.Frame(mode_card, bg='white')
        mode_frame.pack(fill=tk.X, pady=5)
        
        tk.Radiobutton(mode_frame, 
                      text="🖱️ 直线模式 (左键加线/右键删线)", 
                      variable=self.enable_lasso_mode, 
                      value=False,
                      command=self.update_plot_view,
                      bg='white',
                      font=('Microsoft YaHei', 9),
                      activebackground=THEME_COLORS['hover']).pack(anchor="w", pady=2)
        
        tk.Radiobutton(mode_frame, 
                      text="🎯 圈选模式 (画圈提取数据)", 
                      variable=self.enable_lasso_mode, 
                      value=True,
                      command=self.update_plot_view,
                      bg='white',
                      font=('Microsoft YaHei', 9),
                      activebackground=THEME_COLORS['hover']).pack(anchor="w", pady=2)

        # 3. 操作区 - 现代化卡片
        action_card = self.create_card(scrollable_frame, "🔧 操作区", THEME_COLORS['success'])
        
        reset_btn = self.create_modern_button(action_card, 
                                             "🗑️ 清空所有数据", 
                                             self.reset_all,
                                             '#DC3545')

    def create_card(self, parent, title, color):
        """创建现代化卡片"""
        card_frame = tk.Frame(parent, bg='white', relief='flat', bd=1)
        card_frame.pack(fill=tk.X, padx=15, pady=10)
        
        # 卡片标题
        title_frame = tk.Frame(card_frame, bg=color, height=40)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame, 
                              text=title, 
                              bg=color, 
                              fg='white',
                              font=('Microsoft YaHei', 11, 'bold'))
        title_label.pack(expand=True)
        
        # 卡片内容区
        content_frame = tk.Frame(card_frame, bg='white')
        content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        return content_frame

    def create_modern_button(self, parent, text, command, color):
        """创建现代化按钮"""
        btn = tk.Button(parent, 
                       text=text,
                       command=command,
                       bg=color,
                       fg='white',
                       font=('Microsoft YaHei', 10, 'bold'),
                       relief='flat',
                       bd=0,
                       padx=20,
                       pady=10,
                       cursor='hand2',
                       activebackground=self.darken_color(color),
                       activeforeground='white')
        btn.pack(fill=tk.X, pady=2)
        
        # 添加悬停效果
        def on_enter(e):
            btn.configure(bg=self.darken_color(color))
        def on_leave(e):
            btn.configure(bg=color)
            
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn

    def darken_color(self, color):
        """使颜色变暗"""
        color_map = {
            THEME_COLORS['primary']: '#1E5F7A',
            THEME_COLORS['secondary']: '#7A2B5A',
            THEME_COLORS['accent']: '#C17301',
            THEME_COLORS['success']: '#A02E17',
            '#DC3545': '#B02A37'
        }
        return color_map.get(color, color)

    def setup_results_tab(self):
        self.inner_nb = ttk.Notebook(self.tab_res, style='Modern.TNotebook')
        self.inner_nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- 分类树页面 ---
        self.tab_tree = tk.Frame(self.inner_nb, bg='white')
        self.inner_nb.add(self.tab_tree, text="🌳 分类目录树")
        
        # 现代化工具栏
        toolbar = tk.Frame(self.tab_tree, bg=THEME_COLORS['bg_light'], height=50)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        toolbar.pack_propagate(False)
        
        # 工具栏按钮
        btn_frame = tk.Frame(toolbar, bg=THEME_COLORS['bg_light'])
        btn_frame.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.create_toolbar_button(btn_frame, "➕ 新增", self.open_add_data_dialog, THEME_COLORS['primary'])
        self.create_toolbar_button(btn_frame, "❌ 删除", self.delete_selected_data, '#DC3545')
        
        # 分隔线
        separator = tk.Frame(btn_frame, bg=THEME_COLORS['border'], width=2, height=30)
        separator.pack(side=tk.LEFT, padx=10)
        
        self.create_toolbar_button(btn_frame, "↑ 上移", self.move_item_up, THEME_COLORS['accent'])
        self.create_toolbar_button(btn_frame, "↓ 下移", self.move_item_down, THEME_COLORS['accent'])
        
        # 提示文字
        tip_label = tk.Label(toolbar, 
                           text="💡 右键条目标记 | 右键文件夹重命名 | 拖拽排序", 
                           bg=THEME_COLORS['bg_light'], 
                           fg=THEME_COLORS['text_secondary'],
                           font=('Microsoft YaHei', 9))
        tip_label.pack(side=tk.RIGHT, padx=20, pady=15)

        # 现代化树形视图
        tree_frame = tk.Frame(self.tab_tree, bg='white')
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.tree = ttk.Treeview(tree_frame, 
                                columns=('Label', 'Status', 'Index'), 
                                show='tree headings',
                                displaycolumns=('Label', 'Status'),
                                style='Modern.Treeview')
        
        self.tree.heading('#0', text='📁 分类目录')
        self.tree.heading('Label', text='📝 条目名称')
        self.tree.heading('Status', text='🏷️ 状态标记')
        self.tree.column('Index', width=0, stretch=False)
        self.tree.column('#0', width=200)
        self.tree.column('Label', width=250)
        self.tree.column('Status', width=100)
        
        # 添加滚动条
        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")

        # 绑定事件
        self.tree.bind("<ButtonPress-1>", self.on_drag_start)
        self.tree.bind("<B1-Motion>", self.on_drag_motion)
        self.tree.bind("<ButtonRelease-1>", self.on_drag_release)
        self.tree.bind("<Button-3>", self.on_right_click)

        # --- 报告页面 ---
        self.tab_report = tk.Frame(self.inner_nb, bg='white')
        self.inner_nb.add(self.tab_report, text="📄 文本报告")
        
        # 报告工具栏
        report_toolbar = tk.Frame(self.tab_report, bg=THEME_COLORS['bg_light'], height=50)
        report_toolbar.pack(fill=tk.X, padx=5, pady=5)
        report_toolbar.pack_propagate(False)
        
        report_btn_frame = tk.Frame(report_toolbar, bg=THEME_COLORS['bg_light'])
        report_btn_frame.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.create_toolbar_button(report_btn_frame, "💾 导出 TXT", self.export_txt_file, THEME_COLORS['primary'])
        
        if HAS_OPENCC:
            self.create_toolbar_button(report_btn_frame, "繁→简", self.convert_to_simplified, THEME_COLORS['secondary'])
            self.create_toolbar_button(report_btn_frame, "简→繁", self.convert_to_traditional, THEME_COLORS['secondary'])
        
        # 文本编辑区
        text_frame = tk.Frame(self.tab_report, bg='white')
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.report_text = tk.Text(text_frame,
                                  bg='#F8F9FA',
                                  relief='flat',
                                  bd=1,
                                  highlightthickness=1,
                                  highlightcolor=THEME_COLORS['primary'],
                                  font=('Microsoft YaHei', 11),
                                  wrap=tk.WORD)
        
        # 文本区滚动条
        text_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.report_text.yview)
        self.report_text.configure(yscrollcommand=text_scroll.set)
        
        self.report_text.pack(side="left", fill="both", expand=True)
        text_scroll.pack(side="right", fill="y")

    def create_toolbar_button(self, parent, text, command, color):
        """创建工具栏按钮"""
        btn = tk.Button(parent, 
                       text=text,
                       command=command,
                       bg=color,
                       fg='white',
                       font=('Microsoft YaHei', 9, 'bold'),
                       relief='flat',
                       bd=0,
                       padx=15,
                       pady=5,
                       cursor='hand2')
        btn.pack(side=tk.LEFT, padx=3)
        
        # 悬停效果
        def on_enter(e):
            btn.configure(bg=self.darken_color(color))
        def on_leave(e):
            btn.configure(bg=color)
            
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn

    def setup_plot_tab(self):
        """设置现代化绘图标签页"""
        # 创建绘图容器
        plot_container = tk.Frame(self.tab_plt, bg='white')
        plot_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 绘图工具栏
        plot_toolbar_frame = tk.Frame(plot_container, bg=THEME_COLORS['bg_light'], height=45)
        plot_toolbar_frame.pack(fill=tk.X, pady=(0, 10))
        plot_toolbar_frame.pack_propagate(False)
        
        # 状态指示器
        status_frame = tk.Frame(plot_toolbar_frame, bg=THEME_COLORS['bg_light'])
        status_frame.pack(side=tk.LEFT, padx=15, pady=10)
        
        self.mode_indicator = tk.Label(status_frame,
                                      text="🖱️ 直线模式",
                                      bg=THEME_COLORS['primary'],
                                      fg='white',
                                      font=('Microsoft YaHei', 10, 'bold'),
                                      padx=15,
                                      pady=5)
        self.mode_indicator.pack(side=tk.LEFT)
        
        # 绘图统计信息
        stats_frame = tk.Frame(plot_toolbar_frame, bg=THEME_COLORS['bg_light'])
        stats_frame.pack(side=tk.RIGHT, padx=15, pady=10)
        
        self.stats_label = tk.Label(stats_frame,
                                   text="数据点: 0 | 分类线: 0",
                                   bg=THEME_COLORS['bg_light'],
                                   fg=THEME_COLORS['text_secondary'],
                                   font=('Microsoft YaHei', 9))
        self.stats_label.pack()
        
        # 创建matplotlib图形
        self.fig, self.ax = plt.subplots(figsize=(8, 6), dpi=100)
        self.fig.patch.set_facecolor('white')
        
        # 设置现代化的图表样式
        self.ax.set_facecolor('#FAFAFA')
        self.ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_color('#CCCCCC')
        self.ax.spines['bottom'].set_color('#CCCCCC')
        
        # 创建画布
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_container)
        self.canvas.mpl_connect('button_press_event', self.on_plot_click)
        
        # 添加matplotlib工具栏
        toolbar = NavigationToolbar2Tk(self.canvas, plot_container)
        toolbar.update()
        
        # 自定义工具栏样式
        for child in toolbar.winfo_children():
            if isinstance(child, tk.Button):
                child.configure(bg=THEME_COLORS['bg_light'], 
                               relief='flat',
                               bd=1)
        
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def update_mode_indicator(self):
        """更新模式指示器"""
        if self.enable_lasso_mode.get():
            self.mode_indicator.configure(text="🎯 圈选模式", bg=THEME_COLORS['accent'])
        else:
            self.mode_indicator.configure(text="🖱️ 直线模式", bg=THEME_COLORS['primary'])
    
    def update_stats_display(self):
        """更新统计信息显示"""
        data_count = len(self.df)
        threshold_count = len(self.thresholds)
        category_count = len(self.category_list)
        marked_count = len(self.marked_indices)
        
        stats_text = f"数据点: {data_count} | 分类线: {threshold_count} | 圈选组: {category_count} | 标记: {marked_count}"
        self.stats_label.configure(text=stats_text)

    # ===============================================
    # 🔼 🔽 上移/下移
    # ===============================================
    def move_item_up(self):
        selected = self.tree.selection()
        for item in selected:
            parent = self.tree.parent(item)
            if parent:
                idx = self.tree.index(item)
                if idx > 0: self.tree.move(item, parent, idx - 1)
        self.generate_report_from_tree()

    def move_item_down(self):
        selected = reversed(self.tree.selection())
        for item in selected:
            parent = self.tree.parent(item)
            if parent:
                idx = self.tree.index(item)
                siblings = self.tree.get_children(parent)
                if idx < len(siblings) - 1: self.tree.move(item, parent, idx + 1)
        self.generate_report_from_tree()

    # ===============================================
    # ➕ 插入新增逻辑
    # ===============================================
    def open_add_data_dialog(self):
        """现代化的新增数据对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("➕ 新增数据")
        dialog.geometry("400x350")
        dialog.configure(bg='white')
        dialog.resizable(False, False)
        
        # 居中显示
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 标题栏
        title_frame = tk.Frame(dialog, bg=THEME_COLORS['primary'], height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame, 
                              text="➕ 添加新数据点", 
                              bg=THEME_COLORS['primary'], 
                              fg='white',
                              font=('Microsoft YaHei', 14, 'bold'))
        title_label.pack(expand=True)
        
        # 内容区域
        content_frame = tk.Frame(dialog, bg='white')
        content_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # 获取默认值
        default_y, default_x, insert_pos = "", "", len(self.df)
        selected = self.tree.selection()
        if selected and self.tree.parent(selected[0]):
            vals = self.tree.item(selected[0], 'values')
            row_idx = int(vals[2])
            if row_idx in self.df.index:
                default_y = str(self.df.loc[row_idx, 'Y'] + 1)
                default_x = str(self.df.loc[row_idx, 'X'])
                insert_pos = self.df.index.get_loc(row_idx) + 1
        
        # 输入字段
        fields = [
            ("📝 数据名称:", ""),
            ("📊 Y 轴数值:", default_y),
            ("📈 X 轴数值:", default_x)
        ]
        
        entries = []
        for i, (label_text, default_val) in enumerate(fields):
            # 标签
            label = tk.Label(content_frame, 
                           text=label_text, 
                           bg='white',
                           fg=THEME_COLORS['text_primary'],
                           font=('Microsoft YaHei', 11, 'bold'))
            label.pack(anchor='w', pady=(10 if i > 0 else 0, 5))
            
            # 输入框
            entry = tk.Entry(content_frame,
                           font=('Microsoft YaHei', 11),
                           bg='#F8F9FA',
                           relief='flat',
                           bd=1,
                           highlightthickness=2,
                           highlightcolor=THEME_COLORS['primary'])
            entry.pack(fill=tk.X, pady=(0, 10), ipady=8)
            entry.insert(0, default_val)
            entries.append(entry)
        
        # 按钮区域
        button_frame = tk.Frame(content_frame, bg='white')
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        def save_data():
            try:
                name = entries[0].get().strip() or "未命名"
                y_val = float(entries[1].get())
                x_val = float(entries[2].get())
                
                row = pd.DataFrame([[name, y_val, x_val]], columns=['Label', 'Y', 'X'])
                self.df = pd.concat([self.df.iloc[:insert_pos], row, self.df.iloc[insert_pos:]]).reset_index(drop=True)
                self.category_list, self.marked_indices = [], set()
                self.refresh_all()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("输入错误", "Y和X必须是有效的数字！")
        
        def cancel():
            dialog.destroy()
        
        # 保存按钮
        save_btn = tk.Button(button_frame,
                           text="✅ 保存数据",
                           command=save_data,
                           bg=THEME_COLORS['primary'],
                           fg='white',
                           font=('Microsoft YaHei', 11, 'bold'),
                           relief='flat',
                           bd=0,
                           padx=20,
                           pady=10,
                           cursor='hand2')
        save_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # 取消按钮
        cancel_btn = tk.Button(button_frame,
                             text="❌ 取消",
                             command=cancel,
                             bg='#6C757D',
                             fg='white',
                             font=('Microsoft YaHei', 11, 'bold'),
                             relief='flat',
                             bd=0,
                             padx=20,
                             pady=10,
                             cursor='hand2')
        cancel_btn.pack(side=tk.RIGHT)
        
        # 设置焦点
        entries[0].focus_set()
        
        # 回车保存
        dialog.bind('<Return>', lambda e: save_data())

    # ===============================================
    # ✋ 拖拽逻辑
    # ===============================================
    def on_drag_start(self, event):
        item = self.tree.identify_row(event.y)
        if item and self.tree.parent(item): self.drag_source_item = item

    def on_drag_motion(self, event):
        target = self.tree.identify_row(event.y)
        if target: self.tree.selection_set(target)

    def on_drag_release(self, event):
        if not self.drag_source_item: return
        target = self.tree.identify_row(event.y)
        if target and target != self.drag_source_item:
            dest_p = self.tree.parent(target) or target
            try:
                self.tree.move(self.drag_source_item, dest_p, self.tree.index(target))
                self.generate_report_from_tree()
            except:
                pass
        self.drag_source_item = None

    # ===============================================
    # 🎯 绘图与交互
    # ===============================================
    def on_plot_click(self, event):
        if event.inaxes != self.ax: return
        if not self.enable_lasso_mode.get():
            if event.button == 1:
                val = round(event.ydata, 1)
                if val not in self.thresholds: self.thresholds.append(val); self.thresholds.sort(); self.refresh_all()
            elif event.button == 3 and self.thresholds:
                closest = min(self.thresholds, key=lambda x: abs(x - event.ydata))
                if abs(closest - event.ydata) < (self.ax.get_ylim()[1] - self.ax.get_ylim()[0]) * 0.05:
                    self.thresholds.remove(closest);
                    self.refresh_all()

    def on_lasso_select(self, verts):
        if self.df.empty: return
        path = Path(verts)
        inside = path.contains_points(self.df[['X', 'Y']].values)
        new_idx = set(self.df.index[inside].tolist())
        if new_idx:
            for cat in self.category_list: cat['indices'] -= new_idx
            cat_id = len(self.category_list) + 1
            self.category_list.append({'name': f"圈选提取 {cat_id}", 'indices': new_idx,
                                       'color': self.color_cycle[(cat_id - 1) % len(self.color_cycle)]})
            self.refresh_all()

    def update_plot_view(self):
        self.ax.clear()
        self.ax.set_title("📈 数据可视化交互区", fontsize=14, fontweight='bold', pad=20)
        self.ax.set_facecolor('#FAFAFA')
        self.ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        
        if not self.df.empty:
            colors = ['#3498DB'] * len(self.df)
            sizes = [80] * len(self.df)
            alphas = [0.7] * len(self.df)
            
            # 设置点的颜色和大小
            for i in self.df.index:
                if i in self.marked_indices:
                    colors[i], sizes[i], alphas[i] = '#E74C3C', 150, 1.0
                else:
                    for cat in self.category_list:
                        if i in cat['indices']:
                            colors[i], sizes[i], alphas[i] = cat['color'], 120, 0.8
                            break
            
            # 绘制散点图
            scatter = self.ax.scatter(self.df['X'], self.df['Y'], 
                                    c=colors, s=sizes, alpha=alphas, 
                                    zorder=5, edgecolors='white', linewidth=1.5)
            
            # 添加数据标签
            for idx, row in self.df.iterrows():
                is_marked = idx in self.marked_indices
                self.ax.annotate(row['Label'], 
                               (row['X'], row['Y']), 
                               xytext=(0, 8), 
                               textcoords="offset points",
                               ha='center', 
                               fontsize=9, 
                               color='#E74C3C' if is_marked else '#2C3E50',
                               weight='bold' if is_marked else 'normal',
                               bbox=dict(boxstyle="round,pad=0.3", 
                                       facecolor='white' if not is_marked else '#E74C3C',
                                       edgecolor='none',
                                       alpha=0.8))
        
        # 绘制分类线
        for y in self.thresholds:
            self.ax.axhline(y=y, color=THEME_COLORS['primary'], 
                          linestyle='--', alpha=0.8, linewidth=2)
            self.ax.text(self.ax.get_xlim()[1], y, f' {y}', 
                        verticalalignment='center',
                        bbox=dict(boxstyle="round,pad=0.2", 
                                facecolor=THEME_COLORS['primary'], 
                                alpha=0.8),
                        color='white', fontweight='bold')
        
        # 设置坐标轴样式
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_color('#CCCCCC')
        self.ax.spines['bottom'].set_color('#CCCCCC')
        self.ax.tick_params(colors='#666666')
        
        # 设置标签
        self.ax.set_xlabel('X 轴数值', fontsize=12, color='#2C3E50')
        self.ax.set_ylabel('Y 轴数值', fontsize=12, color='#2C3E50')
        
        # 圈选模式
        if self.enable_lasso_mode.get():
            self.lasso = LassoSelector(self.ax, onselect=self.on_lasso_select, 
                                     props={'color': THEME_COLORS['accent'], 'linewidth': 2})
        else:
            if self.lasso:
                self.lasso.set_active(False)
                self.lasso = None
        
        # 更新界面指示器
        self.update_mode_indicator()
        self.update_stats_display()
        
        self.canvas.draw()

    def classify_and_display(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        if self.df.empty: return
        cat_idx = set()
        for i, cat in enumerate(self.category_list):
            if not cat['indices']: continue
            tag = f"tag_{cat['color']}"
            self.tree.tag_configure(tag, foreground=cat['color'], font=("", self.current_font_size, "bold"))
            pid = self.tree.insert("", "end", text=f"📂 {cat['name']}", open=True, tags=(tag,))
            for idx in sorted(list(cat['indices'])):
                m = idx in self.marked_indices
                self.tree.insert(pid, "end", values=(self.df.loc[idx, 'Label'], "✅ 标记" if m else "", idx),
                                 tags=('marked' if m else ''))
                cat_idx.add(idx)
        rem_df = self.df.drop(list(cat_idx))
        if not rem_df.empty:
            t_sorted = sorted(self.thresholds)
            line_cats = []
            if not t_sorted:
                line_cats.append(("数据区", rem_df))
            else:
                line_cats.append((f"低于 {t_sorted[0]}", rem_df[rem_df['Y'] < t_sorted[0]]))
                for i in range(len(t_sorted) - 1):
                    line_cats.append((f"{t_sorted[i]} ~ {t_sorted[i + 1]}",
                                      rem_df[(rem_df['Y'] >= t_sorted[i]) & (rem_df['Y'] < t_sorted[i + 1])]))
                line_cats.append((f"高于 {t_sorted[-1]}", rem_df[rem_df['Y'] >= t_sorted[-1]]))
            for name, sub in line_cats:
                if sub.empty: continue
                pid = self.tree.insert("", "end", text=f"📂 {self.custom_cat_names.get(name, name)}", open=True)
                for r_idx, r in sub.iterrows():
                    m = r_idx in self.marked_indices
                    self.tree.insert(pid, "end", values=(r['Label'], "✅ 标记" if m else "", r_idx),
                                     tags=('marked' if m else ''))
        self.generate_report_from_tree()

    def generate_report_from_tree(self):
        self.report_text.delete("1.0", tk.END);
        content = ""
        for pid in self.tree.get_children(""):
            title = self.tree.item(pid, "text").replace("📂 ", "");
            children = self.tree.get_children(pid)
            if not children: continue
            content += f"【{title}】:\n"
            prev_m = None
            for i, cid in enumerate(children):
                vals = self.tree.item(cid, "values");
                name, idx = vals[0], int(vals[2]);
                curr_m = idx in self.marked_indices
                if curr_m:
                    if prev_m is False or prev_m is None: content += "\n"
                    content += f"{name}\n"
                else:
                    content += f"\n{name}\n\n"
                if curr_m:
                    next_m = False
                    if i < len(children) - 1: next_m = int(
                        self.tree.item(children[i + 1], "values")[2]) in self.marked_indices
                    if not next_m: content += "\n"
                prev_m = curr_m
            content += "\n"
        self.report_text.insert(tk.END, re.sub(r'\n{3,}', '\n\n', content).strip() + "\n")

    def on_font_combo_change(self, event):
        self.current_font_size = int(self.combo_font.get());
        self.apply_font_style();
        self.refresh_all()

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
        self.update_plot_view(); self.classify_and_display()

    def delete_selected_data(self):
        items = self.tree.selection()
        indices = [int(self.tree.item(i, 'values')[2]) for i in items if self.tree.parent(i)]
        if indices and messagebox.askyesno("确认", "删除数据？"):
            self.df = self.df.drop(indices).reset_index(drop=True)
            self.category_list, self.marked_indices = [], set();
            self.refresh_all()

    def reset_all(self):
        self.thresholds, self.category_list, self.marked_indices, self.custom_cat_names = [], [], set(), {};
        self.refresh_all()

    def load_from_text(self):
        try:
            txt = self.root.clipboard_get()
            if txt: self.text_input.delete("1.0", tk.END); self.text_input.insert(tk.END, txt)
        except:
            pass
        raw = self.text_input.get("1.0", tk.END).strip();
        data = []
        for line in raw.split('\n'):
            parts = re.split(r'[|\t,，]+', line.strip())
            if len(parts) >= 3:
                try:
                    data.append([parts[0].strip(), float(parts[1]), float(parts[2])])
                except:
                    continue
        if data:
            self.df = pd.DataFrame(data, columns=['Label', 'Y', 'X']);
            self.reset_all();
            self.main_notebook.select(self.tab_plt)

    def convert_text(self, mode):
        if not HAS_OPENCC: return
        txt = self.report_text.get("1.0", tk.END).strip()
        if txt:
            converter = opencc.OpenCC(mode);
            self.report_text.delete("1.0", tk.END);
            self.report_text.insert(tk.END, converter.convert(txt))

    def convert_to_simplified(self):
        self.convert_text('t2s')

    def convert_to_traditional(self):
        self.convert_text('s2t')

    def export_txt_file(self):
        raw = self.report_text.get("1.0", tk.END);
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path:
            filtered = [l for l in raw.splitlines() if not (l.strip().startswith("【") and "】" in l)]
            with open(path, "w", encoding="utf-8") as f: f.write("\n".join(filtered).strip())


if __name__ == "__main__":
    root = tk.Tk();
    app = DataClassifierApp(root);
    root.mainloop()