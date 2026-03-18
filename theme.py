# -*- coding: utf-8 -*-
"""
Theme Configuration - 仓库进仓单识别助手
"""

# 飞书原生风格
class LarkTheme:
    PRIMARY = "#3370FF"
    SECONDARY = "#D1DEFC"
    ACCENT = "#3370FF"

    BACKGROUND = "#F5F6F7"
    SURFACE = "#FFFFFF"

    TEXT_MAIN = "#1F2329"
    TEXT_MUTED = "#646A73"

    ERROR = "#F54A45"
    SUCCESS = "#00B600"
    WARNING = "#FF8800"

    BORDER = "#DEE0E3"

    FONT_FAMILY = ("Microsoft YaHei", "Segoe UI", "sans-serif")
    FONT_SIZE_SM = 12
    FONT_SIZE_MD = 14
    FONT_SIZE_LG = 16
    FONT_SIZE_XL = 20
    FONT_SIZE_2XL = 24

    CORNER_RADIUS = 6
    PADDING_SM = 10
    PADDING_MD = 16
    PADDING_LG = 24

    BTN_PRIMARY_COLOR = PRIMARY
    BTN_PRIMARY_HOVER = "#2864EE"

    BTN_SECONDARY_COLOR = "transparent"
    BTN_SECONDARY_HOVER = "#EBEDF0"
    BTN_SECONDARY_BORDER = "#1F2329"
    BTN_SECONDARY_TEXT = PRIMARY

    BTN_ACCENT_COLOR = PRIMARY
    BTN_ACCENT_HOVER = "#2864EE"

    FRAME_BG = SURFACE


# 当前选择
Theme = LarkTheme
