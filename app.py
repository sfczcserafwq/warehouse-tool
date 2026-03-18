# -*- coding: utf-8 -*-
"""
仓库进仓单识别助手 - GUI版本
简化版：扫描 → 核对 → 复制
"""

import os
import re
import sys
# 强制使用 UTF-8 输出
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

import json
import pyperclip
import threading
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional, List

import logging
import subprocess
import ctypes
import customtkinter as ctk

# 导入本地模块
from invoice_parser import WarehouseParser, WarehouseItem
from invoice_rules import CATEGORIES
from auth_manager import AuthManager
from theme import Theme


class GuiLogHandler(logging.Handler):
    """用于将日志输出到GUI的文本框"""
    def __init__(self, text_widget, master):
        super().__init__()
        self.text_widget = text_widget
        self.master = master
        self.formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S')

    def emit(self, record):
        msg = self.format(record)
        def append():
            try:
                self.text_widget.configure(state="normal")
                self.text_widget.insert("end", msg + "\n")
                self.text_widget.see("end")
                self.text_widget.configure(state="disabled")
            except:
                pass
        self.master.after(0, append)


class WarehouseApp(ctk.CTk):
    """仓库进仓单识别助手主窗口"""

    def __init__(self, config: dict, auth_manager: AuthManager):
        super().__init__()

        self.config = config
        self.auth_mgr = auth_manager

        # 设置任务栏图标ID
        try:
            myappid = 'warehouse.warehouse.assistant.v1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

        # 配置日志
        self.setup_gui_logging()

        # 窗口设置
        self.title("📦 仓库进仓单识别助手")

        # 设置图标
        icon_path = self.resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        self.geometry("700x600")
        self.minsize(600, 500)

        # 设置主题
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.configure(fg_color=Theme.BACKGROUND)

        # 数据
        self.scan_dir: Optional[str] = None
        self.warehouse_items: List[WarehouseItem] = []

        # 创建界面
        self.create_widgets()

        # 加载默认目录
        default_dir = self.config.get("invoice_dir", "./invoices")
        if os.path.isabs(default_dir):
            self.scan_dir = default_dir
        else:
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            self.scan_dir = os.path.normpath(os.path.join(base_path, default_dir))

        self.dir_entry.insert(0, self.scan_dir)

    def resource_path(self, relative_path):
        """获取资源绝对路径"""
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def setup_gui_logging(self):
        """配置GUI日志"""
        logging.info("仓库进仓单识别助手已启动")

    def create_widgets(self):
        """创建界面组件"""
        # 主容器
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=3)  # 结果区域
        self.grid_rowconfigure(4, weight=1)  # 日志区域

        # ===== 顶部：目录选择 =====
        dir_frame = ctk.CTkFrame(self, fg_color=Theme.SURFACE, corner_radius=Theme.CORNER_RADIUS)
        dir_frame.grid(row=0, column=0, padx=Theme.PADDING_MD, pady=(Theme.PADDING_MD, Theme.PADDING_SM), sticky="ew")
        dir_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(dir_frame, text="📂 进仓单目录:", font=(Theme.FONT_FAMILY[0], Theme.FONT_SIZE_MD), text_color=Theme.TEXT_MAIN).grid(
            row=0, column=0, padx=Theme.PADDING_SM, pady=Theme.PADDING_SM)

        self.dir_entry = ctk.CTkEntry(dir_frame, placeholder_text="选择进仓单所在目录...",
                                      font=(Theme.FONT_FAMILY[0], Theme.FONT_SIZE_MD),
                                      border_color=Theme.BORDER,
                                      fg_color=Theme.SURFACE, text_color=Theme.TEXT_MAIN)
        self.dir_entry.grid(row=0, column=1, padx=5, pady=Theme.PADDING_SM, sticky="ew")

        ctk.CTkButton(dir_frame, text="浏览...", width=80, command=self.browse_dir,
                      font=(Theme.FONT_FAMILY[0], Theme.FONT_SIZE_MD),
                      fg_color=Theme.SECONDARY, text_color=Theme.BTN_SECONDARY_TEXT, hover_color=Theme.BTN_PRIMARY_HOVER).grid(
            row=0, column=2, padx=Theme.PADDING_SM, pady=Theme.PADDING_SM)

        # ===== 中间：操作按钮 =====
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=1, column=0, padx=Theme.PADDING_MD, pady=Theme.PADDING_SM, sticky="ew")

        self.scan_btn = ctk.CTkButton(
            btn_frame, text="🔍 扫描识别", command=self.scan_warehouse,
            font=(Theme.FONT_FAMILY[0], Theme.FONT_SIZE_LG, "bold"), height=40,
            fg_color=Theme.PRIMARY, hover_color=Theme.BTN_PRIMARY_HOVER
        )
        self.scan_btn.pack(side="left", padx=Theme.PADDING_SM, pady=Theme.PADDING_SM, expand=True, fill="x")

        self.copy_btn = ctk.CTkButton(
            btn_frame, text="📋 复制结果", command=self.copy_results,
            font=(Theme.FONT_FAMILY[0], Theme.FONT_SIZE_LG), height=40, state="disabled",
            fg_color=Theme.ACCENT, hover_color=Theme.BTN_ACCENT_HOVER
        )
        self.copy_btn.pack(side="left", padx=Theme.PADDING_SM, pady=Theme.PADDING_SM, expand=True, fill="x")

        # ===== 主体：结果显示 =====
        result_frame = ctk.CTkFrame(self, fg_color=Theme.SURFACE, corner_radius=Theme.CORNER_RADIUS)
        result_frame.grid(row=2, column=0, padx=Theme.PADDING_MD, pady=Theme.PADDING_SM, sticky="nsew")
        result_frame.grid_columnconfigure(0, weight=1)
        result_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(result_frame, text="📋 识别结果:",
                     font=(Theme.FONT_FAMILY[0], Theme.FONT_SIZE_MD, "bold"),
                     text_color=Theme.TEXT_MAIN).grid(
            row=0, column=0, padx=Theme.PADDING_MD, pady=(Theme.PADDING_SM, 5), sticky="w")

        self.result_text = ctk.CTkTextbox(result_frame, font=("Consolas", Theme.FONT_SIZE_MD),
                                          fg_color=Theme.SURFACE, text_color=Theme.TEXT_MAIN)
        self.result_text.grid(row=1, column=0, padx=Theme.PADDING_MD, pady=(0, Theme.PADDING_MD), sticky="nsew")
        self.result_text.insert("1.0", "点击「扫描识别」开始...")

        # ===== 底部：状态栏 =====
        status_frame = ctk.CTkFrame(self, height=30)
        status_frame.grid(row=3, column=0, padx=20, pady=(0, 5), sticky="ew")

        self.status_label = ctk.CTkLabel(status_frame, text="就绪", font=("", 12))
        self.status_label.pack(side="left", padx=10, pady=5)

        self.total_label = ctk.CTkLabel(status_frame, text="", font=("", 12, "bold"))
        self.total_label.pack(side="right", padx=10, pady=5)

        # ===== 底部：实时日志 =====
        log_frame = ctk.CTkFrame(self, fg_color=Theme.SURFACE, corner_radius=Theme.CORNER_RADIUS)
        log_frame.grid(row=4, column=0, padx=Theme.PADDING_MD, pady=(0, Theme.PADDING_MD), sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(log_frame, text="📝 运行日志:",
                     font=(Theme.FONT_FAMILY[0], Theme.FONT_SIZE_SM, "bold"),
                     text_color=Theme.TEXT_MUTED).grid(
             row=0, column=0, padx=Theme.PADDING_SM, pady=2, sticky="w")

        self.log_textbox = ctk.CTkTextbox(log_frame, font=("Consolas", 10), height=80,
                                          fg_color=Theme.SURFACE, text_color=Theme.TEXT_MUTED)
        self.log_textbox.grid(row=1, column=0, padx=Theme.PADDING_SM, pady=5, sticky="nsew")
        self.log_textbox.insert("1.0", "等待操作...\n")
        self.log_textbox.configure(state="disabled")

        # 添加日志处理器
        gui_handler = GuiLogHandler(self.log_textbox, self)
        logging.getLogger().addHandler(gui_handler)

    def browse_dir(self):
        """浏览选择目录"""
        dir_path = filedialog.askdirectory(title="选择进仓单目录")
        if dir_path:
            self.scan_dir = dir_path
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, dir_path)

    def scan_warehouse(self):
        """扫描并识别进仓单"""
        dir_path = self.dir_entry.get().strip()
        if not dir_path or not os.path.isdir(dir_path):
            messagebox.showerror("错误", "请选择有效的进仓单目录")
            return

        self.scan_dir = dir_path
        self.status_label.configure(text="正在扫描识别...")
        self.scan_btn.configure(state="disabled")
        self.copy_btn.configure(state="disabled")
        self.result_text.delete("1.0", "end")
        self._append_log("🔍 开始扫描识别进仓单...\n")

        # 在后台线程执行
        thread = threading.Thread(target=self._scan_thread)
        thread.start()

    def _append_log(self, message: str):
        """线程安全地追加日志"""
        try:
            logging.info(message.strip())
        except Exception:
            pass

        def update():
            self.result_text.insert("end", message)
            self.result_text.see("end")
        self.after(0, update)

    def _scan_thread(self):
        """后台扫描线程"""
        try:
            self._append_log("📂 扫描目录中的文件...\n")
            parser = WarehouseParser(self.config)
            self.warehouse_items = parser.scan_directory(self.scan_dir)

            # 切换回主线程显示核对窗口
            self.after(0, lambda: self._show_verification_window())

        except Exception as e:
            self.after(0, lambda: self._show_error(str(e)))

    def _show_verification_window(self):
        """显示核对窗口"""
        self.scan_btn.configure(state="normal")

        if not self.warehouse_items:
            self._update_scan_result()
            return

        self._append_log("📝 正在打开核对窗口...\n")

        from verification_window import VerificationWindow

        def on_finish(edited_items):
            """核对完成回调"""
            if edited_items:
                # 更新数据
                self.warehouse_items = []
                for item_data in edited_items:
                    self.warehouse_items.append(WarehouseItem(
                        product_name=item_data.get('product_name', ''),
                        quantity=int(item_data.get('quantity', 1)),
                        category=item_data.get('category', '纸箱'),
                        file_path='',
                        file_name='',
                        raw_text=''
                    ))

            self._update_scan_result()

        VerificationWindow(self, self.warehouse_items, on_finish)

    def _update_scan_result(self):
        """更新扫描结果显示"""
        self.scan_btn.configure(state="normal")

        if not self.warehouse_items:
            self.result_text.delete("1.0", "end")
            self.result_text.insert("1.0", "未找到任何进仓单文件\n")
            self.status_label.configure(text="未找到文件")
            return

        # 显示结果
        lines = []
        lines.append(f"✅ 识别完成，共 {len(self.warehouse_items)} 项\n")
        lines.append("=" * 50 + "\n\n")

        # 按分类显示
        from collections import Counter
        category_count = Counter(item.category for item in self.warehouse_items)

        lines.append("📊 分类汇总:\n")
        for cat, count in category_count.items():
            lines.append(f"   {cat}: {count} 项\n")
        lines.append("\n")

        lines.append("📋 明细列表:\n")
        lines.append("-" * 50 + "\n")

        for i, item in enumerate(self.warehouse_items, 1):
            lines.append(f"{i}. {item.product_name}\n")
            lines.append(f"   数量: {item.quantity} | 分类: {item.category}\n\n")

        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", "".join(lines))

        self.status_label.configure(text=f"识别完成，共 {len(self.warehouse_items)} 项")
        self.copy_btn.configure(state="normal")

        self._append_log(f"✨ 识别完成，{len(self.warehouse_items)} 项\n")

    def copy_results(self):
        """复制结果到剪贴板"""
        if not self.warehouse_items:
            messagebox.showwarning("提示", "没有可复制的结果")
            return

        try:
            # 生成制表符分隔的文本
            lines = ["商品名称\t数量\t分类"]
            for item in self.warehouse_items:
                lines.append(f"{item.product_name}\t{item.quantity}\t{item.category}")

            text = "\n".join(lines)
            pyperclip.copy(text)

            self.status_label.configure(text="✅ 已复制到剪贴板")
            self._append_log("📋 结果已复制到剪贴板\n")

            messagebox.showinfo("复制成功", f"已复制 {len(self.warehouse_items)} 项到剪贴板\n可直接粘贴到 Excel 或表格中")

        except Exception as e:
            messagebox.showerror("复制失败", f"复制到剪贴板失败:\n{str(e)}")

    def _show_error(self, msg: str):
        """显示错误"""
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", f"❌ 错误: {msg}\n")
        self.status_label.configure(text="扫描失败")
        self.scan_btn.configure(state="normal")


# 保持兼容性别名
ReimbursementApp = WarehouseApp


if __name__ == "__main__":
    pass
