# -*- coding: utf-8 -*-
"""
身份验证管理模块
处理用户登录、验证码发送和用户信息缓存
"""

import json
import logging
import os
import random
import sys
import time
from typing import Optional, Dict

from feishu_client import FeishuClient, FeishuConfig


class AuthManager:
    """身份验证管理器"""
    
    def __init__(self, config: Optional[Dict] = None, config_path: str = "config.json", profile_path: str = "user_profile.json"):
        # 确定基准路径
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
            
        self.profile_path = os.path.join(base_path, profile_path)
        self.config_path = os.path.join(base_path, config_path)
        
        # 加载公共配置
        if config:
            self.app_config = config
        else:
            self.app_config = self._load_json(self.config_path)
            # 如果找不到外部配置且是打包环境，尝试加载内部默认配置
            if not self.app_config and getattr(sys, 'frozen', False):
                 internal_config = os.path.join(sys._MEIPASS, "config.json")
                 self.app_config = self._load_json(internal_config)
                 
        self.feishu_cfg = self.app_config.get("feishu", {})
        
        # 初始化客户端
        self.client = FeishuClient(FeishuConfig(
            app_id=self.feishu_cfg.get("app_id"),
            app_secret=self.feishu_cfg.get("app_secret")
        ))
        
        # 验证码缓存 {mobile: (code, expire_time, user_id)}
        self._verify_codes = {}
        
    def _load_json(self, path: str) -> Dict:
        """加载 JSON 文件"""
        if not os.path.exists(path):
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"加载配置文件失败 {path}: {e}")
            return {}

    def _save_profile(self, profile: Dict):
        """保存用户配置"""
        with open(self.profile_path, 'w', encoding='utf-8') as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)

    def get_current_user(self) -> Optional[Dict]:
        """获取当前登录用户信息"""
        profile = self._load_json(self.profile_path)
        if profile.get("user_id"):
            return profile
        return None

    def logout(self):
        """退出登录"""
        if os.path.exists(self.profile_path):
            os.remove(self.profile_path)

    def send_verification_code(self, mobile: str) -> str:
        """
        发送验证码到飞书
        Returns:
            user_id: 找到的用户ID
        """
        # 1. 查找用户
        user_id = self.client.get_user_id_by_mobile(mobile)
        if not user_id:
            raise Exception("未找到该手机号对应的飞书账号")
            
        # 2. 生成验证码
        code = str(random.randint(100000, 999999))
        
        # 3. 发送消息
        msg = f"【飞书报销助手】您的登录验证码是：{code}\n有效期5分钟，请勿告诉他人。"
        try:
            self.client.send_message(user_id, msg)
        except Exception as e:
            raise Exception(f"发送验证码失败: {str(e)}\n请确认已在飞书后台开通消息权限。")
            
        # 4. 缓存 (5分钟有效)
        self._verify_codes[mobile] = (code, time.time() + 300, user_id)
        
        return user_id

    def verify_code(self, mobile: str, code: str) -> bool:
        """验证代码并登录"""
        record = self._verify_codes.get(mobile)
        if not record:
            raise Exception("请先获取验证码")
            
        stored_code, expire_time, user_id = record
        
        if time.time() > expire_time:
            raise Exception("验证码已过期，请重新获取")
            
        if stored_code != code:
            raise Exception("验证码错误")
            
        # 验证成功，保存用户信息
        try:
            user_info = self.client.get_user_info(user_id)
            name = user_info.get("name", "")
        except Exception as e:
            logging.warning(f"获取用户信息失败: {e}")
            name = ""
            
        profile = {
            "user_id": user_id,
            "mobile": mobile,
            "name": name,
            "login_time": time.time()
        }
        self._save_profile(profile)
        
        # 清除验证码
        del self._verify_codes[mobile]
        
        return True
