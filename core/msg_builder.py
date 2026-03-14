import requests
from datetime import date
from utils.config import get_config
from utils.hitokoto import request_hitokoto

def get_env_info():
    """从 api.ipapi.is 获取 Country 和 Datacenter 信息"""
    try:
        # 请求接口，设置 8 秒超时防止阻塞
        response = requests.get("https://api.ipapi.is/", timeout=8)
        data = response.json()
        
        ip = data.get("ip", "未知IP")
        
        # 1. 提取国家 (对应 JSON 中的 location -> country)
        country = data.get("location", {}).get("country", "未知国家")
        
        # 2. 提取数据中心 (对应 JSON 中的 datacenter -> datacenter)
        # 逻辑：如果 datacenter 字段存在则取其值，否则回退到 ASN 组织名（如 China Mobile）
        dc_info = data.get("datacenter", {}).get("datacenter")
        if not dc_info:
            dc_info = data.get("asn", {}).get("org", "非机房网络")
            
        return ip, country, dc_info
    except Exception:
        return "查询失败", "未知国家", "获取失败"

def build_message() -> str:
    today = date.today()
    config = get_config()
    
    # --- 阶段 1: 确定基础模板 ---
    # 检查是否处于新年活动期间且功能已开启
    is_festival = (config.get("happyNewYear", {}).get("enabled", False) and 
                   date(2026, 2, 16) <= today <= date(2026, 3, 3))
    
    if is_festival:
        from utils.chinese_new_year_2026_mare import get_random_festival_quote, get_lunar_date
        message = config.get("happyNewYear", {}).get("messageTemplate", "[API]")
        
        # 替换节日特有标签
        if "[data]" in message:
            message = message.replace("[data]", today.strftime("%Y年%m月%d日"))
        if "[data_lunar]" in message:
            lunar_date = get_lunar_date(today)
            message = message.replace("[data_lunar]", lunar_date if lunar_date else "未知农历日期")
        if "[API]" in message:
            message = message.replace("[API]", get_random_festival_quote())
    else:
        # 普通模式模板
        message = config.get("messageTemplate", "续火花")
        if "[API]" in message:
            message = message.replace("[API]", request_hitokoto())
    
    # --- 阶段 2: 动态适配环境信息标签 ---
    # 只有当模板中包含对应标签时才发起网络请求，避免无谓消耗
    env_tags = ["[IP]", "[COUNTRY]", "[DC]"]
    if any(tag in message for tag in env_tags):
        ip_addr, country_name, dc_name = get_env_info()
        message = message.replace("[IP]", ip_addr)
        message = message.replace("[COUNTRY]", country_name)
        message = message.replace("[DC]", dc_name)

    return message.strip()
