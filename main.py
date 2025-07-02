#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenModelica MAT文件解析工具 - PyQt5 + pyqtgraph版本
使用pyqtgraph提供高性能交互式绘图
"""

import sys
import scipy.io as scio
import numpy as np
import pandas as pd
from pathlib import Path
import time

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGridLayout, QSplitter, QTabWidget,
                            QTreeWidget, QTreeWidgetItem, QListWidget, QTextEdit,
                            QPushButton, QLabel, QLineEdit, QFileDialog, 
                            QMessageBox, QProgressBar, QComboBox, QCheckBox,
                            QGroupBox, QListWidgetItem, QAbstractItemView,
                            QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor

import pyqtgraph as pg
from pyqtgraph import PlotWidget, mkPen, mkBrush

# 设置pyqtgraph参数
pg.setConfigOptions(antialias=True)  # 抗锯齿
pg.setConfigOption('background', 'w')  # 白色背景
pg.setConfigOption('foreground', 'k')  # 黑色前景

class ModelicaMatReader:
    """OpenModelica MAT文件读取器 - 基于原始函数"""
    
    def __init__(self):
        self.file_path = None
        self.data = None
        self.keys = []
        self.values = {}
        self.time_vector = []
        
    def load_data(self, file_path):
        """加载MAT文件数据"""
        self.file_path = file_path
        
        try:
            print(f"🔄 加载文件: {file_path}")
            start_time = time.time()
            
            # 使用原始逻辑加载数据
            self.data = scio.loadmat(file_path)
            
            # 解析变量名 - 完全基于原始代码
            self._parse_keys_original()
            
            # 解析变量值 - 完全基于原始代码  
            self._parse_values_original()
            
            # 提取时间向量
            self._extract_time_original()
            
            load_time = time.time() - start_time
            print(f"✅ 成功加载 {len(self.keys)} 个变量，耗时 {load_time:.2f}s")
            return True, f"成功加载 {len(self.keys)} 个变量"
            
        except Exception as e:
            error_msg = f"加载失败: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    def _parse_keys_original(self):
        """解析变量名 - 使用原始逻辑"""
        key = ''
        keys = []
        
        # 完全按照原始代码逻辑
        for xx in range(len(self.data["name"][0]) - 1):
            for i in range(len(self.data["name"]) - 1):
                if len(self.data["name"][i]) < xx:
                    break
                try:
                    _k = self.data["name"][i][xx]
                    if _k == '\x00':
                        break
                except Exception as e:
                    break
                key = key + _k
            keys.append(key)
            key = ''
        
        self.keys = keys
    
    def _parse_values_original(self):
        """解析变量值 - 使用原始逻辑"""
        values = {}
        
        # 完全按照原始代码逻辑
        for index, value in enumerate(self.keys):
            try:
                data_index = self.data["dataInfo"][0,][index]
                line_num = self.data["dataInfo"][1,][index] - 1
                if data_index in [1, 2]:
                    dataV = self.data["data_%s" % data_index][line_num,]
                    values[value] = dataV.tolist()
            except Exception as e:
                continue
        
        self.values = values
    
    def _extract_time_original(self):
        """提取时间向量 - 使用原始逻辑"""
        try:
            # 按照原始代码
            self.time_vector = self.data["data_2"][0,].tolist()
        except Exception as e:
            self.time_vector = []
    
    def read_variables(self, read_keys):
        """读取指定变量 - 兼容原始接口"""
        rv = []
        
        for _rk in read_keys:
            # 处理表达式
            if self._is_expression(_rk):
                _v = self._evaluate_expression(_rk)
            else:
                _v = self.values.get(_rk, [])
            
            rv.append(_v)
        
        return rv, self.time_vector
    
    def _is_expression(self, key):
        """检查是否为数学表达式"""
        operators = ['+', '-', '*', '/', '(', ')']
        return any(op in key for op in operators)
    
    def _evaluate_expression(self, expression):
        """计算变量表达式"""
        try:
            # 处理减法表达式 如 'rectifier.DC.v[1]-rectifier.DC.v[2]'
            if '-' in expression and '[' in expression:
                parts = expression.split('-')
                if len(parts) == 2:
                    var1 = parts[0].strip()
                    var2 = parts[1].strip()
                    
                    _v1 = self.values.get(var1, [])
                    _v2 = self.values.get(var2, [])
                    
                    if _v1 and _v2 and len(_v1) == len(_v2):
                        return [_v1[i] - _v2[i] for i in range(len(_v1))]
            
            return []
            
        except Exception as e:
            print(f"❌ 表达式计算失败 {expression}: {e}")
            return []
    
    def get_variable_categories(self):
        """获取变量分类"""
        categories = {
            'electrical': [],
            'thermal': [],
            'mechanical': [],
            'control': [],
            'fault': [],
            'time': [],
            'other': []
        }
        
        for key in self.keys:
            key_lower = key.lower()
            
            if 'time' in key_lower:
                categories['time'].append(key)
            elif any(kw in key_lower for kw in ['voltage', 'current', 'power', 'v[', 'i[', 'p[', 'volt', 'amp', 'dc', 'ac']):
                categories['electrical'].append(key)
            elif any(kw in key_lower for kw in ['temp', 'heat', 'cool', 'thermal']):
                categories['thermal'].append(key)
            elif any(kw in key_lower for kw in ['speed', 'torque', 'rpm', 'mechanical', 'omega']):
                categories['mechanical'].append(key)
            elif any(kw in key_lower for kw in ['control', 'ref', 'cmd', 'set', 'governor']):
                categories['control'].append(key)
            elif any(kw in key_lower for kw in ['fault', 'error', 'alarm', 'trip']):
                categories['fault'].append(key)
            else:
                categories['other'].append(key)
        
        return categories
    
    def search_variables(self, pattern):
        """搜索变量"""
        pattern = pattern.lower()
        return [key for key in self.keys if pattern in key.lower()]
    
    def get_variable_stats(self, var_name):
        """获取变量统计信息"""
        if var_name not in self.values:
            return None
        
        data = np.array(self.values[var_name])
        if data.size == 0:
            return None
        
        return {
            'min': float(np.min(data)),
            'max': float(np.max(data)),
            'mean': float(np.mean(data)),
            'std': float(np.std(data)),
            'size': data.size
        }


class LoadingThread(QThread):
    """文件加载线程"""
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str)
    
    def __init__(self, reader, file_path):
        super().__init__()
        self.reader = reader
        self.file_path = file_path
    
    def run(self):
        self.progress.emit("正在加载文件...")
        success, message = self.reader.load_data(self.file_path)
        self.finished.emit(success, message)


class PyQtGraphWidget(QWidget):
    """PyQtGraph 绘图组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 创建布局
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 创建工具栏
        toolbar = self.create_toolbar()
        layout.addWidget(toolbar)
        
        # 创建绘图区域
        self.plot_widget = PlotWidget()
        self.plot_widget.setLabel('left', '数值')
        self.plot_widget.setLabel('bottom', '时间 (s)')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.addLegend()
        
        # 设置交互功能
        self.plot_widget.setMouseEnabled(x=True, y=True)  # 启用鼠标交互
        self.plot_widget.enableAutoRange()  # 自动范围
        
        layout.addWidget(self.plot_widget)
        
        # 颜色列表
        self.colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
        ]
        
        self.current_plots = []  # 存储当前绘制的曲线
        
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QFrame()
        toolbar.setFrameStyle(QFrame.StyledPanel)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(5, 5, 5, 5)
        
        # 清除按钮
        clear_btn = QPushButton("清除图表")
        clear_btn.clicked.connect(self.clear_plot)
        toolbar_layout.addWidget(clear_btn)
        
        # 自适应按钮
        auto_range_btn = QPushButton("自适应范围")
        auto_range_btn.clicked.connect(self.auto_range)
        toolbar_layout.addWidget(auto_range_btn)
        
        # 网格切换
        self.grid_checkbox = QCheckBox("显示网格")
        self.grid_checkbox.setChecked(True)
        self.grid_checkbox.toggled.connect(self.toggle_grid)
        toolbar_layout.addWidget(self.grid_checkbox)
        
        # 抗锯齿切换
        self.antialias_checkbox = QCheckBox("抗锯齿")
        self.antialias_checkbox.setChecked(True)
        self.antialias_checkbox.toggled.connect(self.toggle_antialias)
        toolbar_layout.addWidget(self.antialias_checkbox)
        
        toolbar_layout.addStretch()
        
        # 状态标签
        self.status_label = QLabel("就绪")
        toolbar_layout.addWidget(self.status_label)
        
        return toolbar
    
    def clear_plot(self):
        """清除图表"""
        self.plot_widget.clear()
        self.current_plots.clear()
        self.status_label.setText("图表已清除")
    
    def auto_range(self):
        """自适应范围"""
        self.plot_widget.autoRange()
        self.status_label.setText("已自适应范围")
    
    def toggle_grid(self, checked):
        """切换网格显示"""
        self.plot_widget.showGrid(x=checked, y=checked, alpha=0.3)
    
    def toggle_antialias(self, checked):
        """切换抗锯齿"""
        pg.setConfigOptions(antialias=checked)
        # 重新绘制所有曲线
        if self.current_plots:
            self.replot_all()
    
    def replot_all(self):
        """重新绘制所有曲线"""
        plot_data = []
        for plot_item in self.current_plots:
            x_data, y_data = plot_item.getData()
            name = plot_item.opts.get('name', '')
            plot_data.append((x_data, y_data, name))
        
        self.plot_widget.clear()
        self.current_plots.clear()
        
        for i, (x_data, y_data, name) in enumerate(plot_data):
            color = self.colors[i % len(self.colors)]
            pen = mkPen(color=color, width=2)
            curve = self.plot_widget.plot(x_data, y_data, pen=pen, name=name)
            self.current_plots.append(curve)
    
    def plot_variables(self, reader, variable_names):
        """绘制变量"""
        if not variable_names:
            self.status_label.setText("没有选择变量")
            return
        
        try:
            # 清除之前的图表
            self.clear_plot()
            
            # 读取变量数据
            var_data, time_data = reader.read_variables(variable_names)
            
            # 检查时间数据
            if time_data:
                x_data = np.array(time_data)
                x_label = '时间 (s)'
            else:
                x_label = '数据点'
            
            self.plot_widget.setLabel('bottom', x_label)
            
            # 绘制每个变量
            valid_count = 0
            for i, (var_name, data) in enumerate(zip(variable_names, var_data)):
                if not data:
                    continue
                
                y_data = np.array(data)
                
                # 确定x轴数据
                if time_data and len(y_data) == len(x_data):
                    plot_x = x_data
                else:
                    plot_x = np.arange(len(y_data))
                
                # 选择颜色和样式
                color = self.colors[valid_count % len(self.colors)]
                pen = mkPen(color=color, width=2)
                
                # 绘制曲线
                curve = self.plot_widget.plot(
                    plot_x, y_data, 
                    pen=pen, 
                    name=var_name,
                    symbol=None  # 不显示数据点符号，提高性能
                )
                
                self.current_plots.append(curve)
                valid_count += 1
            
            # 自适应范围
            self.plot_widget.autoRange()
            
            # 更新状态
            self.status_label.setText(f"已绘制 {valid_count} 个变量")
            
        except Exception as e:
            self.status_label.setText(f"绘图错误: {str(e)}")
            print(f"绘图错误: {e}")
    
    def add_variable(self, reader, var_name):
        """添加单个变量到现有图表"""
        try:
            var_data, time_data = reader.read_variables([var_name])
            
            if not var_data[0]:
                return
            
            y_data = np.array(var_data[0])
            
            # 确定x轴数据
            if time_data and len(y_data) == len(time_data):
                x_data = np.array(time_data)
            else:
                x_data = np.arange(len(y_data))
            
            # 选择颜色
            color = self.colors[len(self.current_plots) % len(self.colors)]
            pen = mkPen(color=color, width=2)
            
            # 绘制曲线
            curve = self.plot_widget.plot(
                x_data, y_data,
                pen=pen,
                name=var_name
            )
            
            self.current_plots.append(curve)
            self.status_label.setText(f"已添加变量: {var_name}")
            
        except Exception as e:
            self.status_label.setText(f"添加变量失败: {str(e)}")


class ModelicaMatAnalyzer(QMainWindow):
    """主应用程序窗口"""
    
    def __init__(self):
        super().__init__()
        self.reader = ModelicaMatReader()
        self.selected_variables = []
        
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("OpenModelica MAT文件分析器 - PyQtGraph版")
        self.setGeometry(100, 100, 1600, 1000)
        
        # 设置窗口图标和样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 文件操作区域
        self.create_file_operations(main_layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧面板
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # 右侧面板
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # 设置分割器比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        # 状态栏
        self.statusBar().showMessage("就绪 - 请选择MAT文件开始分析")
        
    def create_file_operations(self, parent_layout):
        """创建文件操作区域"""
        file_group = QGroupBox("📁 文件操作")
        file_layout = QHBoxLayout(file_group)
        
        # 选择文件按钮
        self.select_file_btn = QPushButton("选择MAT文件")
        self.select_file_btn.clicked.connect(self.select_file)
        self.select_file_btn.setStyleSheet("QPushButton { background-color: #2196F3; }")
        file_layout.addWidget(self.select_file_btn)
        
        # 文件路径标签
        self.file_label = QLabel("未选择文件")
        self.file_label.setStyleSheet("color: gray; font-style: italic;")
        file_layout.addWidget(self.file_label)
        
        file_layout.addStretch()
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        file_layout.addWidget(self.progress_bar)
        
        parent_layout.addWidget(file_group)
    
    def create_left_panel(self):
        """创建左侧面板"""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 搜索区域
        search_group = QGroupBox("🔍 搜索变量")
        search_layout = QHBoxLayout(search_group)
        
        self.search_line = QLineEdit()
        self.search_line.setPlaceholderText("输入搜索关键词...")
        self.search_line.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_line)
        
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self.search_variables)
        search_btn.setStyleSheet("QPushButton { background-color: #FF9800; }")
        search_layout.addWidget(search_btn)
        
        left_layout.addWidget(search_group)
        
        # 变量分类标签页
        self.category_tabs = QTabWidget()
        left_layout.addWidget(self.category_tabs)
        
        # 创建各分类标签页
        self.category_lists = {}
        categories = {
            'time': '🕒 时间',
            'electrical': '🔌 电气量',
            'thermal': '🌡️ 热量',
            'mechanical': '⚙️ 机械量',
            'control': '🎛️ 控制',
            'fault': '⚠️ 故障',
            'other': '📋 其他'
        }
        
        for cat_key, cat_name in categories.items():
            list_widget = QListWidget()
            list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
            list_widget.itemDoubleClicked.connect(
                lambda item, cat=cat_key: self.add_variable_to_selection(item))
            
            # 添加右键菜单
            list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
            list_widget.customContextMenuRequested.connect(
                lambda pos, cat=cat_key: self.show_context_menu(pos, cat))
            
            self.category_lists[cat_key] = list_widget
            self.category_tabs.addTab(list_widget, cat_name)
        
        # 已选择变量
        selected_group = QGroupBox("✅ 已选择变量")
        selected_layout = QVBoxLayout(selected_group)
        
        self.selected_list = QListWidget()
        self.selected_list.itemDoubleClicked.connect(self.remove_variable_from_selection)
        selected_layout.addWidget(self.selected_list)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        plot_btn = QPushButton("📈 绘制选中变量")
        plot_btn.clicked.connect(self.plot_selected_variables)
        plot_btn.setStyleSheet("QPushButton { background-color: #4CAF50; }")
        button_layout.addWidget(plot_btn)
        
        clear_btn = QPushButton("🗑️ 清空选择")
        clear_btn.clicked.connect(self.clear_selection)
        clear_btn.setStyleSheet("QPushButton { background-color: #f44336; }")
        button_layout.addWidget(clear_btn)
        
        export_btn = QPushButton("💾 导出CSV")
        export_btn.clicked.connect(self.export_csv)
        export_btn.setStyleSheet("QPushButton { background-color: #9C27B0; }")
        button_layout.addWidget(export_btn)
        
        selected_layout.addLayout(button_layout)
        left_layout.addWidget(selected_group)
        
        return left_widget
    
    def create_right_panel(self):
        """创建右侧面板"""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 文件信息
        info_group = QGroupBox("📊 文件信息")
        info_layout = QVBoxLayout(info_group)
        
        self.info_text = QTextEdit()
        self.info_text.setMaximumHeight(150)
        self.info_text.setReadOnly(True)
        self.info_text.setStyleSheet("background-color: white; border: 1px solid #ccc;")
        info_layout.addWidget(self.info_text)
        
        right_layout.addWidget(info_group)
        
        # 图表显示
        plot_group = QGroupBox("📈 交互式图表 (PyQtGraph)")
        plot_layout = QVBoxLayout(plot_group)
        
        self.plot_widget = PyQtGraphWidget()
        plot_layout.addWidget(self.plot_widget)
        
        right_layout.addWidget(plot_group)
        
        return right_widget
    
    def show_context_menu(self, position, category):
        """显示右键菜单"""
        list_widget = self.category_lists[category]
        item = list_widget.itemAt(position)
        
        if item:
            from PyQt5.QtWidgets import QMenu
            menu = QMenu()
            
            add_action = menu.addAction("➕ 添加到选择")
            plot_action = menu.addAction("📊 单独绘制")
            info_action = menu.addAction("ℹ️ 查看统计信息")
            
            action = menu.exec_(list_widget.mapToGlobal(position))
            
            if action == add_action:
                self.add_variable_to_selection(item)
            elif action == plot_action:
                self.plot_single_variable(item.text())
            elif action == info_action:
                self.show_variable_info(item.text())
    
    def plot_single_variable(self, var_name):
        """单独绘制一个变量"""
        if not self.reader.keys:
            QMessageBox.warning(self, "警告", "请先加载MAT文件")
            return
        
        self.plot_widget.plot_variables(self.reader, [var_name])
    
    def show_variable_info(self, var_name):
        """显示变量统计信息"""
        stats = self.reader.get_variable_stats(var_name)
        if stats:
            info_text = f"变量: {var_name}\n"
            info_text += f"数据点数: {stats['size']}\n"
            info_text += f"最小值: {stats['min']:.6f}\n"
            info_text += f"最大值: {stats['max']:.6f}\n"
            info_text += f"平均值: {stats['mean']:.6f}\n"
            info_text += f"标准差: {stats['std']:.6f}"
            
            QMessageBox.information(self, f"变量信息 - {var_name}", info_text)
        else:
            QMessageBox.warning(self, "警告", f"无法获取变量 {var_name} 的统计信息")
    
    def select_file(self):
        """选择文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择OpenModelica MAT文件", "", "MAT files (*.mat);;All files (*)")
        
        if file_path:
            self.file_label.setText(f"正在加载: {Path(file_path).name}")
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # 不确定进度
            
            # 在后台线程中加载文件
            self.loading_thread = LoadingThread(self.reader, file_path)
            self.loading_thread.finished.connect(self.on_file_loaded)
            self.loading_thread.progress.connect(self.statusBar().showMessage)
            self.loading_thread.start()
    
    def on_file_loaded(self, success, message):
        """文件加载完成"""
        self.progress_bar.setVisible(False)
        
        if success:
            self.file_label.setText(f"✅ 文件: {Path(self.reader.file_path).name}")
            self.file_label.setStyleSheet("color: green; font-weight: bold;")
            self.populate_variable_lists()
            self.update_file_info()
            self.statusBar().showMessage("文件加载完成 - 可以开始分析")
            QMessageBox.information(self, "成功", message)
        else:
            self.file_label.setText("❌ 加载失败")
            self.file_label.setStyleSheet("color: red; font-weight: bold;")
            self.statusBar().showMessage("加载失败")
            QMessageBox.critical(self, "错误", message)
    
    def populate_variable_lists(self):
        """填充变量列表"""
        if not self.reader.keys:
            return
        
        categories = self.reader.get_variable_categories()
        
        for cat_key, variables in categories.items():
            list_widget = self.category_lists[cat_key]
            list_widget.clear()
            
            for var in sorted(variables):
                item = QListWidgetItem(var)
                # 为不同类型的变量设置不同的图标
                if cat_key == 'electrical':
                    item.setToolTip(f"电气变量: {var}")
                elif cat_key == 'thermal':
                    item.setToolTip(f"热力变量: {var}")
                elif cat_key == 'fault':
                    item.setToolTip(f"故障变量: {var}")
                    
                list_widget.addItem(item)
    
    def update_file_info(self):
        """更新文件信息"""
        if not self.reader.keys:
            return
        
        categories = self.reader.get_variable_categories()
        
        info_text = f"📁 文件信息:\n"
        info_text += f"  📊 变量总数: {len(self.reader.keys)}\n"
        info_text += f"  🕒 时间点数: {len(self.reader.time_vector)}\n"
        
        if self.reader.time_vector:
            info_text += f"  ⏱️ 时间范围: {self.reader.time_vector[0]:.3f} - {self.reader.time_vector[-1]:.3f} 秒\n"
        
        info_text += f"\n🏷️ 变量分类:\n"
        category_names = {
            'time': '🕒 时间',
            'electrical': '🔌 电气量',
            'thermal': '🌡️ 热量',
            'mechanical': '⚙️ 机械量',
            'control': '🎛️ 控制',
            'fault': '⚠️ 故障',
            'other': '📋 其他'
        }
        
        for cat, vars in categories.items():
            if vars:
                cat_name = category_names.get(cat, cat)
                info_text += f"  {cat_name}: {len(vars)} 个\n"
        
        self.info_text.setText(info_text)
    
    def on_search_changed(self):
        """搜索内容变化"""
        pattern = self.search_line.text().strip()
        if not pattern:
            self.populate_variable_lists()
            return
        
        self.search_variables()
    
    def search_variables(self):
        """搜索变量"""
        pattern = self.search_line.text().strip()
        if not pattern or not self.reader.keys:
            return
        
        matched_vars = self.reader.search_variables(pattern)
        categories = self.reader.get_variable_categories()
        
        # 清空所有列表
        for list_widget in self.category_lists.values():
            list_widget.clear()
        
        # 填充匹配的变量
        for cat_key, cat_vars in categories.items():
            list_widget = self.category_lists[cat_key]
            for var in matched_vars:
                if var in cat_vars:
                    item = QListWidgetItem(var)
                    item.setToolTip(f"搜索结果: {var}")
                    list_widget.addItem(item)
        
        self.statusBar().showMessage(f"搜索到 {len(matched_vars)} 个匹配变量")
    
    def add_variable_to_selection(self, item):
        """添加变量到选择列表"""
        var_name = item.text()
        if var_name not in self.selected_variables:
            self.selected_variables.append(var_name)
            self.update_selected_list()
            self.statusBar().showMessage(f"已添加变量: {var_name}")
    
    def remove_variable_from_selection(self, item):
        """从选择列表移除变量"""
        var_name = item.text()
        if var_name in self.selected_variables:
            self.selected_variables.remove(var_name)
            self.update_selected_list()
            self.statusBar().showMessage(f"已移除变量: {var_name}")
    
    def update_selected_list(self):
        """更新已选择变量列表"""
        self.selected_list.clear()
        for var in self.selected_variables:
            item = QListWidgetItem(f"📊 {var}")
            item.setToolTip(f"双击移除: {var}")
            self.selected_list.addItem(item)
    
    def clear_selection(self):
        """清空选择"""
        self.selected_variables.clear()
        self.update_selected_list()
        self.statusBar().showMessage("已清空选择")
    
    def plot_selected_variables(self):
        """绘制选中变量"""
        if not self.selected_variables:
            QMessageBox.warning(self, "警告", "请先选择要绘制的变量")
            return
        
        if not self.reader.keys:
            QMessageBox.warning(self, "警告", "请先加载MAT文件")
            return
        
        self.plot_widget.plot_variables(self.reader, self.selected_variables)
        self.statusBar().showMessage(f"已绘制 {len(self.selected_variables)} 个变量")
    
    def export_csv(self):
        """导出CSV"""
        if not self.selected_variables:
            QMessageBox.warning(self, "警告", "请先选择要导出的变量")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存CSV文件", "", "CSV files (*.csv);;All files (*)")
        
        if not file_path:
            return
        
        try:
            # 读取数据
            var_data, time_data = self.reader.read_variables(self.selected_variables)
            
            # 创建DataFrame
            export_data = {'time': time_data}
            for var_name, data in zip(self.selected_variables, var_data):
                if data and len(data) == len(time_data):
                    export_data[var_name] = data
            
            df = pd.DataFrame(export_data)
            df.to_csv(file_path, index=False)
            
            QMessageBox.information(self, "成功", f"数据已导出到: {Path(file_path).name}")
            self.statusBar().showMessage(f"数据已导出: {len(df.columns)} 个变量, {len(df)} 行数据")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setApplicationName("OpenModelica MAT分析器")
    app.setApplicationVersion("2.0 - PyQtGraph版")
    app.setOrganizationName("MAT分析工具")
    
    # 创建主窗口
    window = ModelicaMatAnalyzer()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()