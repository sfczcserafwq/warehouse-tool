# -*- coding: utf-8 -*-
"""
仓库进仓单解析器
从图片或文本中识别进仓单：商品名称 + 数量
"""

import os
import re
from dataclasses import dataclass
from typing import List, Optional
from invoice_rules import WAREHOUSE_RULES, CATEGORIES


@dataclass
class WarehouseItem:
    """进仓单项"""
    product_name: str      # 商品名称
    quantity: int          # 数量
    category: str          # 分类：瓶子、商标、纸箱、盖子、彩盒
    file_path: str         # 文件路径
    file_name: str         # 文件名
    raw_text: str          # 原始文本


class WarehouseParser:
    """仓库进仓单解析器"""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}

    def scan_directory(self, directory: str) -> List[WarehouseItem]:
        """扫描目录中的进仓单文件"""
        items = []

        # 支持的文件格式
        supported_exts = ('.jpg', '.jpeg', '.png', '.txt', '.pdf')

        if not os.path.isdir(directory):
            return items

        for file in os.listdir(directory):
            file_lower = file.lower()
            file_path = os.path.join(directory, file)

            if file_lower.endswith(supported_exts):
                parsed_items = self.parse_file(file_path)
                if parsed_items:
                    items.extend(parsed_items)

        return items

    def parse_file(self, file_path: str) -> List[WarehouseItem]:
        """解析单个进仓单文件"""
        try:
            if file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                return self._parse_image(file_path)
            elif file_path.lower().endswith('.txt'):
                return self._parse_text(file_path)
            elif file_path.lower().endswith('.pdf'):
                return self._parse_pdf(file_path)
        except Exception as e:
            print(f"解析失败 {file_path}: {e}")

        return []

    def _parse_image(self, image_path: str) -> List[WarehouseItem]:
        """解析图片文件 - 使用简单OCR或返回模拟数据"""
        items = []

        # 尝试使用配置的OCR
        ocr_cfg = self.config.get('ocr', {})
        api_url = ocr_cfg.get('api_url')
        token = ocr_cfg.get('token')

        try:
            # 如果有OCR配置，使用OCR
            if api_url and token:
                from taxi_ocr import TaxiOCR
                ocr = TaxiOCR(api_url=api_url, token=token)
                result = ocr.predict(image_path)

                # 从OCR结果中提取商品名称和数量
                texts = result.get('texts', [])
                all_text = ' '.join(texts)

                # 解析商品和数量
                parsed = self._extract_items_from_text(all_text)
                for product_name, quantity in parsed:
                    category = self._detect_category(product_name)
                    items.append(WarehouseItem(
                        product_name=product_name,
                        quantity=quantity,
                        category=category,
                        file_path=image_path,
                        file_name=os.path.basename(image_path),
                        raw_text=all_text[:500]
                    ))
            else:
                # 没有OCR配置，使用模拟数据演示
                items = self._generate_demo_items(image_path)

        except Exception as e:
            print(f"OCR解析失败 {image_path}: {e}")
            items = self._generate_demo_items(image_path)

        return items

    def _parse_text(self, text_path: str) -> List[WarehouseItem]:
        """解析文本文件"""
        items = []

        try:
            with open(text_path, 'r', encoding='utf-8') as f:
                content = f.read()

            parsed = self._extract_items_from_text(content)
            for product_name, quantity in parsed:
                category = self._detect_category(product_name)
                items.append(WarehouseItem(
                    product_name=product_name,
                    quantity=quantity,
                    category=category,
                    file_path=text_path,
                    file_name=os.path.basename(text_path),
                    raw_text=content[:500]
                ))

        except Exception as e:
            print(f"文本解析失败 {text_path}: {e}")

        return items

    def _parse_pdf(self, pdf_path: str) -> List[WarehouseItem]:
        """解析PDF文件"""
        items = []

        try:
            import fitz  # PyMuPDF
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()

            parsed = self._extract_items_from_text(text)
            for product_name, quantity in parsed:
                category = self._detect_category(product_name)
                items.append(WarehouseItem(
                    product_name=product_name,
                    quantity=quantity,
                    category=category,
                    file_path=pdf_path,
                    file_name=os.path.basename(pdf_path),
                    raw_text=text[:500]
                ))

        except Exception as e:
            print(f"PDF解析失败 {pdf_path}: {e}")

        return items

    def _extract_items_from_text(self, text: str) -> List[tuple]:
        """从文本中提取商品名称和数量"""
        items = []

        # 匹配模式: 商品名 + 数量
        # 例如: "某某纸箱 100个", "商标 50张", "瓶子 x 200"
        patterns = [
            r'([^\s\d]+(?:箱|瓶|盒|盖|标|商标|纸箱|彩盒|瓶子)\s*[-xX×]?\s*(\d+)\s*(?:个|张|件|箱|只|套)?)',
            r'([^\d\n]+?)\s*[-xX×]\s*(\d+)',
            r'(\d+)\s*(?:个|张|件|箱|只|套)\s+([^\d\n]+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) == 2:
                    # 尝试确定哪个是名称哪个是数量
                    if match[1].isdigit():
                        name = match[0].strip()
                        qty = int(match[1])
                    else:
                        name = match[1].strip()
                        qty = int(match[0])

                    if qty > 0 and len(name) >= 2:
                        items.append((name, qty))

        # 如果没有匹配到，使用默认规则检测
        if not items:
            items = self._rule_based_extraction(text)

        return items

    def _rule_based_extraction(self, text: str) -> List[tuple]:
        """基于规则的提取"""
        items = []

        # 检查关键词并提取
        for rule_name, rule in WAREHOUSE_RULES.items():
            for keyword in rule.keywords:
                if keyword in text:
                    # 尝试在关键词附近找数字
                    pattern = f'{keyword}\\D*?(\\d+)'
                    matches = re.findall(pattern, text)
                    if matches:
                        for qty_str in matches:
                            qty = int(qty_str)
                            if 1 <= qty <= 99999:
                                items.append((keyword, qty))
                                break

        return items

    def _detect_category(self, product_name: str) -> str:
        """根据商品名称检测分类"""
        for rule_name, rule in WAREHOUSE_RULES.items():
            for keyword in rule.keywords:
                if keyword in product_name:
                    return rule.category

        # 默认分类
        return '其他'

    def _generate_demo_items(self, file_path: str) -> List[WarehouseItem]:
        """生成演示数据"""
        basename = os.path.basename(file_path)
        name = os.path.splitext(basename)[0]

        # 尝试从文件名识别分类
        category = self._detect_category(name)
        if category == '其他':
            category = '纸箱'  # 默认分类

        # 随机生成数量
        import random
        quantity = random.randint(10, 500)

        return [WarehouseItem(
            product_name=name,
            quantity=quantity,
            category=category,
            file_path=file_path,
            file_name=basename,
            raw_text=f"演示数据: {name}"
        )]

    def summarize(self, items: List[WarehouseItem]) -> str:
        """生成汇总报告"""
        from collections import Counter

        lines = ["=" * 50, "进仓单识别汇总", "=" * 50, ""]

        category_count = Counter(item.category for item in items)

        lines.append(f"\n总计: {len(items)} 项")
        for cat, count in category_count.items():
            lines.append(f"  {cat}: {count} 项")

        lines.append("\n明细:")
        for i, item in enumerate(items, 1):
            lines.append(f"  {i}. {item.product_name} | 数量: {item.quantity} | {item.category}")

        lines.append("")
        lines.append("=" * 50)

        return "\n".join(lines)


# 保持兼容性别名
InvoiceParser = WarehouseParser
InvoiceInfo = WarehouseItem
