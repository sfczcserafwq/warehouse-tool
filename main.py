# -*- coding: utf-8 -*-
"""
仓库进仓单识别助手 - 主入口
简化版：扫描 → 识别 → 复制
"""

import json
import os
import sys
import logging
import logging.handlers


def load_config() -> dict:
    """加载配置文件"""
    try:
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        config_path = os.path.join(base_path, "config.json")

        if not os.path.exists(config_path) and getattr(sys, 'frozen', False):
            config_path = os.path.join(sys._MEIPASS, "config.json")

        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Config Load Error: {e}")
    return {}


def setup_global_logging():
    """配置全局日志"""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    log_file = os.path.join(base_path, 'warehouse.log')

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # File Handler
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=1*1024*1024, backupCount=3, encoding='utf-8', delay=True
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logging.info("=== 仓库进仓单识别助手启动 ===")


def main():
    """主启动入口"""
    # 1. Setup Logging
    setup_global_logging()

    # 2. Load Config
    config = load_config()
    if not config:
        logging.warning("Config not found, using defaults.")

    # 3. Init Auth Manager (兼容原有架构)
    from auth_manager import AuthManager
    auth_mgr = AuthManager(config=config)

    # 4. Init UI App
    from app import WarehouseApp
    app = WarehouseApp(config=config, auth_manager=auth_mgr)

    # 5. Run
    app.mainloop()


if __name__ == "__main__":
    main()
