# -*- coding: utf-8 -*-
"""
进仓单核对窗口 - 修复版
支持：图片预览、多图片导航、逐项核对、跳过循环复制
"""

import os
import customtkinter as ctk
from typing import List, Callable, Dict
from PIL import Image, ImageOps
import fitz
from invoice_parser import WarehouseItem
from invoice_rules import CATEGORIES
from theme import Theme


class VerificationWindow(ctk.CTkToplevel):
    """进仓单核对窗口"""

    MAX_PREVIEW_W = 500
    MAX_PREVIEW_H = 600

    def __init__(self, master, items: List[WarehouseItem], on_finish: Callable):
        super().__init__()

        self.title("📦 进仓单核对")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        self.configure(fg_color=Theme.BACKGROUND)

        self.items = items
        self.on_finish = on_finish
        self.current_index = 0
        self.selected_index = 0  # 当前选中的行（用于复制）

        self.file_groups: Dict[str, List[Dict]] = {}
        self.file_list: List[str] = []
        self._group_by_file()

        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        self.create_image_panel()
        self.create_edit_panel()
        self.create_nav_panel()

        self.load_current_file()

        self.grab_set()
        self.focus_force()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _group_by_file(self):
        self.file_groups = {}
        for item in self.items:
            if item.file_path not in self.file_groups:
                self.file_groups[item.file_path] = []
            self.file_groups[item.file_path].append({
                'product_name': item.product_name,
                'quantity': str(item.quantity),
                'category': item.category
            })
        self.file_list = list(self.file_groups.keys())

    def create_image_panel(self):
        self.image_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.image_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.image_label = ctk.CTkLabel(self.image_frame, text="加载中...", font=("", 14))
        self.image_label.pack(fill="both", expand=True, padx=10, pady=10)

    def create_edit_panel(self):
        self.edit_frame = ctk.CTkFrame(self, fg_color=Theme.SURFACE)
        self.edit_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
        self.edit_frame.pack_propagate(False)

        header = ctk.CTkFrame(self.edit_frame, fg_color="transparent", height=60)
        header.pack(fill="x", pady=(10, 5), padx=10)
        header.pack_propagate(False)

        self.file_title = ctk.CTkLabel(header, text="文件名",
                                       font=(Theme.FONT_FAMILY[0], 16, "bold"), text_color=Theme.TEXT_MAIN)
        self.file_title.pack()

        self.item_count_label = ctk.CTkLabel(header, text="0 项",
                                             font=(Theme.FONT_FAMILY[0], 12), text_color=Theme.TEXT_MUTED)
        self.item_count_label.pack()

        self.list_frame = ctk.CTkScrollableFrame(self.edit_frame, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # 操作按钮
        action_frame = ctk.CTkFrame(self.edit_frame, fg_color="transparent")
        action_frame.pack(fill="x", padx=10, pady=10)

        self.copy_selected_btn = ctk.CTkButton(action_frame, text="📋 复制选中行",
                                                command=self.copy_selected,
                                                font=(Theme.FONT_FAMILY[0], 13, "bold"),
                                                fg_color=Theme.ACCENT, hover_color=Theme.BTN_ACCENT_HOVER, height=36)
        self.copy_selected_btn.pack(fill="x", pady=(0, 5))

        add_frame = ctk.CTkFrame(action_frame, fg_color="transparent")
        add_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(add_frame, text="添加:", font=(Theme.FONT_FAMILY[0], 12),
                     text_color=Theme.TEXT_MUTED).pack(side="left", padx=(0, 5))

        self.add_name_entry = ctk.CTkEntry(add_frame, placeholder_text="商品名称", width=120,
                                           font=(Theme.FONT_FAMILY[0], 12), border_color=Theme.BORDER, fg_color=Theme.SURFACE)
        self.add_name_entry.pack(side="left", padx=2)

        self.add_qty_entry = ctk.CTkEntry(add_frame, placeholder_text="数量", width=60,
                                          font=(Theme.FONT_FAMILY[0], 12), border_color=Theme.BORDER, fg_color=Theme.SURFACE)
        self.add_qty_entry.insert(0, "1")
        self.add_qty_entry.pack(side="left", padx=2)

        self.add_cat_var = ctk.StringVar(value="纸箱")
        self.add_cat_menu = ctk.CTkOptionMenu(add_frame, variable=self.add_cat_var, values=CATEGORIES, width=70,
                                               font=(Theme.FONT_FAMILY[0], 12), fg_color=Theme.SURFACE, text_color=Theme.TEXT_MAIN)
        self.add_cat_menu.pack(side="left", padx=2)

        ctk.CTkButton(add_frame, text="+", width=30, height=30, command=self.add_item_from_entry,
                      font=("", 14), fg_color=Theme.PRIMARY, hover_color=Theme.BTN_PRIMARY_HOVER).pack(side="left", padx=2)

        self.item_rows = []

    def create_nav_panel(self):
        self.nav_frame = ctk.CTkFrame(self, height=70, fg_color=Theme.SURFACE)
        self.nav_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        self.nav_frame.pack_propagate(False)

        left_frame = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
        left_frame.pack(side="left", padx=15, pady=10)

        self.prev_btn = ctk.CTkButton(left_frame, text="◀ 上一张", width=100, command=self.prev_file,
                                       font=(Theme.FONT_FAMILY[0], 13), fg_color=Theme.SECONDARY, text_color=Theme.PRIMARY,
                                       hover_color=Theme.BTN_SECONDARY_HOVER)
        self.prev_btn.pack(side="left", padx=5)

        self.next_btn = ctk.CTkButton(left_frame, text="下一张 ▶", width=100, command=self.next_file,
                                       font=(Theme.FONT_FAMILY[0], 13), fg_color=Theme.SECONDARY, text_color=Theme.PRIMARY,
                                       hover_color=Theme.BTN_SECONDARY_HOVER)
        self.next_btn.pack(side="left", padx=5)

        self.nav_label = ctk.CTkLabel(left_frame, text="1/1", font=(Theme.FONT_FAMILY[0], 12), text_color=Theme.TEXT_MUTED)
        self.nav_label.pack(side="left", padx=15)

        right_frame = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
        right_frame.pack(side="right", padx=15, pady=10)

        self.skip_btn = ctk.CTkButton(right_frame, text="⏭ 选中下一行", width=130, command=self.skip_next,
                                       font=(Theme.FONT_FAMILY[0], 13), fg_color="#FF9800", hover_color="#F57C00",
                                       text_color="white", height=36)
        self.skip_btn.pack(side="left", padx=5)

        self.confirm_btn = ctk.CTkButton(right_frame, text="✓ 确认", width=100, command=self.confirm,
                                         font=(Theme.FONT_FAMILY[0], 13, "bold"), fg_color=Theme.PRIMARY,
                                         hover_color=Theme.BTN_PRIMARY_HOVER, height=36)
        self.confirm_btn.pack(side="left", padx=5)

    def save_current_page(self):
        if not self.file_list:
            return
        filepath = self.file_list[self.current_index]
        items = []
        for row in self.item_rows:
            name = row['name'].get().strip()
            qty = row['qty'].get().strip() or "1"
            cat = row['cat'].get()
            if name:
                items.append({'product_name': name, 'quantity': qty, 'category': cat})
        self.file_groups[filepath] = items

    def load_current_file(self):
        if not self.file_list:
            return
        filepath = self.file_list[self.current_index]
        filename = os.path.basename(filepath)
        file_items = self.file_groups.get(filepath, [])

        self.file_title.configure(text=filename)
        self.item_count_label.configure(text=f"{len(file_items)} 项")

        self._show_image(filepath)

        self.nav_label.configure(text=f"{self.current_index + 1}/{len(self.file_list)}")
        self.prev_btn.configure(state="normal" if self.current_index > 0 else "disabled")
        self.next_btn.configure(state="normal" if self.current_index < len(self.file_list) - 1 else "disabled")

        self._load_items(file_items)

    def _show_image(self, filepath):
        try:
            if filepath.lower().endswith('.pdf'):
                doc = fitz.open(filepath)
                page = doc.load_page(0)
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                doc.close()
            else:
                img = Image.open(filepath)
                img = ImageOps.exif_transpose(img)
            img.thumbnail((self.MAX_PREVIEW_W, self.MAX_PREVIEW_H), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            self.image_label.configure(image=ctk_img, text="")
            self.image_label.image = ctk_img
        except Exception as e:
            self.image_label.configure(text=f"无法预览图片:\n{str(e)}", image=None)

    def _load_items(self, file_items: List[Dict]):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        self.item_rows = []

        if not file_items:
            self._add_item_row(0, {'product_name': '', 'quantity': '1', 'category': '纸箱'})
        else:
            for i, item in enumerate(file_items):
                self._add_item_row(i, item)

        # 默认选中第一行
        self.selected_index = 0
        self._update_selection()

    def _add_item_row(self, index, item_data):
        row = ctk.CTkFrame(self.list_frame, fg_color=Theme.BACKGROUND, corner_radius=6)
        row.pack(fill="x", pady=4, padx=5)

        seq = ctk.CTkLabel(row, text=f"#{index + 1}", font=(Theme.FONT_FAMILY[0], 11, "bold"),
                           text_color=Theme.TEXT_MUTED, width=30)
        seq.pack(side="left", padx=(8, 3), pady=8)

        inputs = ctk.CTkFrame(row, fg_color="transparent")
        inputs.pack(side="left", fill="x", expand=True, padx=3)

        name_entry = ctk.CTkEntry(inputs, placeholder_text="商品名称", font=(Theme.FONT_FAMILY[0], 12),
                                   border_color=Theme.BORDER, fg_color=Theme.SURFACE)
        name_entry.insert(0, item_data.get('product_name', ''))
        name_entry.pack(fill="x", pady=2)

        row2 = ctk.CTkFrame(inputs, fg_color="transparent")
        row2.pack(fill="x", pady=2)

        qty_entry = ctk.CTkEntry(row2, placeholder_text="数量", width=60, font=(Theme.FONT_FAMILY[0], 12),
                                  border_color=Theme.BORDER, fg_color=Theme.SURFACE)
        qty_entry.insert(0, item_data.get('quantity', '1'))
        qty_entry.pack(side="left", padx=(0, 5))

        cat_var = ctk.StringVar(value=item_data.get('category', '纸箱'))
        cat_menu = ctk.CTkOptionMenu(row2, variable=cat_var, values=CATEGORIES, font=(Theme.FONT_FAMILY[0], 11),
                                      fg_color=Theme.SURFACE, text_color=Theme.TEXT_MAIN,
                                      dropdown_font=(Theme.FONT_FAMILY[0], 11))
        cat_menu.pack(side="left")

        row_data = {'name': name_entry, 'qty': qty_entry, 'cat': cat_var, 'row': row}
        self.item_rows.append(row_data)

        del_btn = ctk.CTkButton(row, text="×", width=30, height=30, command=lambda i=index: self._delete_item(i),
                                 font=("", 14, "bold"), fg_color=Theme.ERROR, hover_color="#DC2626", text_color="white")
        del_btn.pack(side="right", padx=(0, 3), pady=5)

    def _update_selection(self):
        """更新选中高亮"""
        for i, row in enumerate(self.item_rows):
            if i == self.selected_index:
                row['row'].configure(fg_color=Theme.PRIMARY)
            else:
                row['row'].configure(fg_color=Theme.BACKGROUND)

    def skip_next(self):
        """选中下一行，循环"""
        if not self.item_rows:
            return
        self.selected_index = (self.selected_index + 1) % len(self.item_rows)
        self._update_selection()

    def copy_selected(self):
        """复制选中的行（只复制名称和数量）"""
        if not self.item_rows or self.selected_index >= len(self.item_rows):
            return

        row = self.item_rows[self.selected_index]
        name = row['name'].get().strip()
        qty = row['qty'].get().strip() or "1"

        if not name:
            return

        # 只复制名称和数量，用Tab分隔
        text = f"{name}\t{qty}"
        try:
            import pyperclip
            pyperclip.copy(text)
        except:
            pass

    def add_item_from_entry(self):
        name = self.add_name_entry.get().strip()
        qty = self.add_qty_entry.get().strip() or "1"
        cat = self.add_cat_var.get()

        if not name:
            return

        self._add_item_row(len(self.item_rows), {'product_name': name, 'quantity': qty, 'category': cat})

        self.add_name_entry.delete(0, "end")
        self.add_qty_entry.delete(0, "end")
        self.add_qty_entry.insert(0, "1")

        self.item_count_label.configure(text=f"{len(self.item_rows)} 项")

    def _delete_item(self, index):
        if len(self.item_rows) > 1:
            self.item_rows[index]['row'].destroy()
            del self.item_rows[index]
            for i, row in enumerate(self.item_rows):
                for child in row['row'].winfo_children():
                    if isinstance(child, ctk.CTkLabel) and child.cget("text").startswith("#"):
                        child.configure(text=f"#{i + 1}")
            self.item_count_label.configure(text=f"{len(self.item_rows)} 项")

            # 调整选中索引
            if self.selected_index >= len(self.item_rows):
                self.selected_index = len(self.item_rows) - 1
            self._update_selection()

    def prev_file(self):
        self.save_current_page()
        if self.current_index > 0:
            self.current_index -= 1
            self.selected_index = 0
            self.load_current_file()

    def next_file(self):
        self.save_current_page()
        if self.current_index < len(self.file_list) - 1:
            self.current_index += 1
            self.selected_index = 0
            self.load_current_file()

    def confirm(self):
        self.save_current_page()
        results = []
        for filepath in self.file_list:
            items = self.file_groups.get(filepath, [])
            for item in items:
                results.append({
                    'product_name': item.get('product_name', ''),
                    'quantity': item.get('quantity', '1'),
                    'category': item.get('category', '纸箱'),
                    'file_path': filepath,
                    'file_name': os.path.basename(filepath),
                    'raw_text': ''
                })
        self.destroy()
        self.on_finish(results)

    def on_close(self):
        self.confirm()
