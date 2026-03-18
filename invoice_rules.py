# -*- coding: utf-8 -*-
"""
进仓单识别规则配置
简化为：商品名称 + 数量，5大分类，3条规则
"""

from dataclasses import dataclass
from typing import List, Dict

@dataclass
class WarehouseRule:
    """进仓单识别规则"""
    keywords: List[str]
    category: str  # 分类：瓶子、商标、纸箱、盖子、彩盒

# 简化的进仓单识别规则 - 保留3条
WAREHOUSE_RULES: Dict[str, WarehouseRule] = {
    '纸箱': WarehouseRule(
        keywords=['纸箱', '箱子', '包装箱', '纸盒'],
        category='纸箱',
    ),
    '瓶子': WarehouseRule(
        keywords=['进货单', '瓶', '塑瓶', '胶瓶', '玻璃瓶'],
        category='瓶子',
    ),
    '商标': WarehouseRule(
        keywords=['商标', '标签', '贴纸', '不干胶'],
        category='商标',
    ),
    '盖子': WarehouseRule(
        keywords=['盖子', '瓶盖', '盖', '盖帽'],
        category='盖子',
    ),
    '彩盒': WarehouseRule(
        keywords=['彩盒', '彩印盒', '印刷盒', '展示盒'],
        category='彩盒',
    ),
}

# 5大分类
CATEGORIES = ['瓶子', '商标', '纸箱', '盖子', '彩盒']

# 分类描述
CATEGORY_DESCRIPTIONS = {
    '瓶子': '塑料瓶/玻璃瓶',
    '商标': '标签/贴纸',
    '纸箱': '纸箱/包装箱',
    '盖子': '瓶盖/盖子',
    '彩盒': '彩印包装盒',
}
