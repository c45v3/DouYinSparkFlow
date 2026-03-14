import requests
from datetime import date
from utils.config import get_config
from utils.hitokoto import request_hitokoto

def get_env_info():
    """从 api.ipapi.is 获取信息并对 IP 进行脱敏处理"""
    try:
        response = requests.get("https://api.ipapi.is/", timeout=8)
        data = response.json()
        raw_ip = data.get("ip", "未知IP")
        
        # IP 脱敏
        if "." in raw_ip:
            ip_parts = raw_ip.split(".")
            mask_ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.*"
        elif ":" in raw_ip:
            ip_parts = raw_ip.split(":")
            mask_ip = f"{':'.join(ip_parts[:4])}:*:*:*:*"
        else:
            mask_ip = raw_ip

        country = data.get("location", {}).get("country", "未知国家")
        dc_info = data.get("datacenter", {}).get("datacenter")
        if not dc_info:
            dc_info = data.get("asn", {}).get("org", "家用/移动网络")
            
        return mask_ip, country, dc_info
    except Exception:
        return "查询失败", "未知国家", "网络获取失败"

def build_message() -> str:
    today = date.today()
    config = get_config()
    # 【修复点】初始化 message，防止生成器表达式作用域报错
    message = "" 
    
    # 1. 确定基础模板逻辑
    is_festival = (config.get("happyNewYear", {}).get("enabled", False) and 
                   date(2026, 2, 16) <= today <= date(2026, 3, 3))
    
    if is_festival:
        from utils.chinese_new_year_2026_mare import get_random_festival_quote, get_lunar_date
        message = config.get("happyNewYear", {}).get("messageTemplate", "[API]")
        if "[data]" in message:
            message = message.replace("[data]", today.strftime("%Y年%m月%d日"))
        if "[data_lunar]" in message:
            lunar_date = get_lunar_date(today)
            message = message.replace("[data_lunar]", lunar_date if lunar_date else "未知农历日期")
        if "[API]" in message:
            message = message.replace("[API]", get_random_festival_quote())
    else:
        # 获取普通模板，如果没有配置则使用默认值
        message = config.get("messageTemplate", "续火花")
        if "[API]" in message:
            message = message.replace("[API]", request_hitokoto())
    
    # 确保 message 此时是一个字符串
    message = str(message)

    # 2. 动态替换环境标签
    env_tags = ["[IP]", "[COUNTRY]", "[DC]"]
    # 【修复点】直接检查，避免在 any() 内部引用可能未绑定的 free variable
    need_env = False
    for tag in env_tags:
        if tag in message:
            need_env = True
            break

    if need_env:
        mask_ip, country_name, dc_name = get_env_info()
        message = message.replace("[IP]", mask_ip)
        message = message.replace("[COUNTRY]", country_name)
        message = message.replace("[DC]", dc_name)

    return message.strip()
