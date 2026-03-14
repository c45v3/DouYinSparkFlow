import os, sys
from enum import Enum
import json
import logging
from utils.logger import setup_logger

logger = setup_logger(level=logging.DEBUG)

"""
是否启用调试模式
更详细的日志打印，浏览器操作可视化等
"""
DEBUG = False
CONFIGFILE = "config.json"
USERDATAFILE = "usersData.json"
config = None
userData = None


class Environment(Enum):
    GITHUBACTION = "GITHUB_ACTION"  # GitHub Action 运行
    LOCAL = "LOCAL"  # 本地代码运行
    PACKED = "PACKED"  # PyInstaller 打包运行

    def __str__(self):
        return self.value


def get_environment():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Environment.PACKED
    elif os.getenv("GITHUB_ACTIONS") == "true":
        return Environment.GITHUBACTION
    else:
        return Environment.LOCAL


def get_config():
    """
    获取配置信息
    :return: 配置字典
    """
    global config
    
    if config:
        return config
    
    env = get_environment()

    configFile = CONFIGFILE

    if env == Environment.PACKED:
        configFile = os.path.join(os.path.dirname(sys.executable), CONFIGFILE)

    with open(configFile, "r", encoding="utf-8") as f:
        config = json.loads(f.read())
    return config


import os
import json
import base64

def get_userData():
    # 1. 从环境变量获取数据
    user_data_raw = os.getenv("USER_DATA", "").strip()
    
    if not user_data_raw:
        return []

    try:
        # 2. 尝试 Base64 解码
        # 如果是 Base64 编码，这里会成功
        decoded_bytes = base64.b64decode(user_data_raw, validate=True)
        decoded_str = decoded_bytes.decode('utf-8')
        return json.loads(decoded_str)
    except Exception:
        # 3. 如果解码失败（例如之前手动填入的明文 JSON），则直接解析
        try:
            return json.loads(user_data_raw)
        except json.JSONDecodeError as e:
            # 记录错误方便排查，但不要崩溃
            print(f"解析 USER_DATA 失败: {e}")
            return []
