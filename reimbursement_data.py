# -*- coding: utf-8 -*-
"""
进仓单数据模型
简化为：商品名称 + 数量
"""

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class WarehouseItem:
    """进仓单项"""
    product_name: str      # 商品名称
    quantity: int          # 数量
    category: str          # 分类：瓶子、商标、纸箱、盖子、彩盒
    file_path: str         # 文件路径
    file_name: str         # 文件名
    raw_text: str          # 原始文本（用于调试）

class WarehouseDataBuilder:
    """进仓单数据构建"""

    def __init__(self, items: List[WarehouseItem]):
        self.items = items

    def to_clipboard_text(self) -> str:
        """生成可粘贴到表格的文本"""
        lines = []
        for item in self.items:
            lines.append(f"{item.product_name}\t{item.quantity}\t{item.category}")
        return "\n".join(lines)

    def to_json(self) -> str:
        """导出为JSON格式"""
        import json
        data = [
            {
                'product_name': item.product_name,
                'quantity': item.quantity,
                'category': item.category,
                'file_name': item.file_name
            }
            for item in self.items
        ]
        return json.dumps(data, ensure_ascii=False, indent=2)

    def print_summary(self):
        """打印汇总"""
        print("=" * 50)
        print("进仓单汇总")
        print("=" * 50)

        # 按分类汇总
        from collections import Counter
        category_count = Counter(item.category for item in self.items)

        print(f"\n总计: {len(self.items)} 项")
        for cat, count in category_count.items():
            print(f"  {cat}: {count} 项")

        print("\n明细:")
        for i, item in enumerate(self.items, 1):
            print(f"  {i}. {item.product_name} | 数量: {item.quantity} | {item.category}")

        print("=" * 50)
