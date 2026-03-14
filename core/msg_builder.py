import requests
from datetime import date
from utils.config import get_config
from utils.hitokoto import request_hitokoto

def get_env_info():
    """从 api.ipapi.is 获取 Country 和 Datacenter 信息"""
    try:
        # 设置超时，防止接口响应慢导致 Action 整体超时
        response = requests.get("https://api.ipapi.is/", timeout=8)
        data = response.json()
        
        ip = data.get("ip", "未知IP")
        
        # 1. 提取国家信息
        country = data.get("location", {}).get("country", "未知国家")
        
        # 2. 提取数据中心/网络信息
        # 优先查找 datacenter 字段，如果不是机房 IP，则回退到 ASN 组织名称
        dc_info = data.get("datacenter", {}).get("datacenter")
        if not dc_info:
            dc_info = data.get("asn", {}).get("org", "家用/移动网络")
            
        return ip, country, dc_info
    except Exception:
        return "查询失败", "未知国家", "网络信息获取失败"

def build_message() -> str:
    today = date.today()
    
    # --- 保持你原有的节日与普通模板逻辑 ---
    if get_config().get("happyNewYear", {}).get("enabled", False) and date(2026, 2, 16) <= today <= date(2026, 3, 3):
        from utils.chinese_new_year_2026_mare import get_random_festival_quote, get_lunar_date
        message = get_config().get("happyNewYear", {}).get("messageTemplate", "[API]")
        if "[data]" in message:
            message = message.replace("[data]", today.strftime("%Y年%m月%d日"))
        if "[data_lunar]" in message:
            lunar_date = get_lunar_date(today)
            message = message.replace("[data_lunar]", lunar_date if lunar_date else "未知农历日期")
        if "[API]" in message:
            api_content = get_random_festival_quote()
            message = message.replace("[API]", api_content)
    else:
        message = get_config().get("messageTemplate", "续火花")
        if "[API]" in message:
            api_content = request_hitokoto()
            message = message.replace("[API]", api_content)
    
    # --- 新增：解析环境标签 ---
    # 只有模板中包含这些标签时才触发网络请求，节省资源
    if any(tag in message for tag in ["[IP]", "[COUNTRY]", "[DC]"]):
        ip_addr, country, dc = get_env_info()
        message = message.replace("[IP]", ip_addr)
        message = message.replace("[COUNTRY]", country)
        message = message.replace("[DC]", dc)

    return message.strip()
