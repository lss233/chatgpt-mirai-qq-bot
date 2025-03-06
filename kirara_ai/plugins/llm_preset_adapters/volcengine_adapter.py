import datetime
import hashlib
import hmac
from urllib.parse import quote

import aiohttp
from pydantic import Field

from .openai_adapter import OpenAIAdapter, OpenAIConfig


class VolcengineConfig(OpenAIConfig):
    api_base: str = "https://ark.cn-beijing.volces.com/api/v3"
    access_key_id: str = Field(default="", env="VOLCENGINE_ACCESS_KEY_ID", description="火山云引擎 API 密钥 ID，用于获取模型列表")
    access_key_secret: str = Field(default="", env="VOLCENGINE_ACCESS_KEY_SECRET", description="火山云引擎 API 密钥，用于获取模型列表")

def generate_volcengine_signature(access_key_id, access_key_secret, method, path, query, body=None):
    """生成火山引擎API所需的HMAC-SHA256签名"""
    # 初始化参数
    service = "ark"
    region = "cn-beijing"
    host = "open.volcengineapi.com"
    content_type = "application/json"
    
    # 获取UTC时间
    now = datetime.datetime.utcnow()
    x_date = now.strftime("%Y%m%dT%H%M%SZ")
    short_date = x_date[:8]
    
    # 计算请求体的SHA256哈希值
    body = body or ""
    x_content_sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest()
    
    # 规范化查询字符串
    canonical_query = normalize_query(query)
    
    # 签名所需的头部
    signed_headers = ["host", "x-content-sha256", "x-date"]
    signed_headers_str = ";".join(signed_headers)
    
    # 构建规范请求字符串
    canonical_headers = "\n".join([
        f"host:{host}",
        f"x-content-sha256:{x_content_sha256}",
        f"x-date:{x_date}",
    ])
    
    canonical_request = "\n".join([
        method.upper(),
        path,
        canonical_query,
        canonical_headers,
        "",
        signed_headers_str,
        x_content_sha256
    ])
    
    # 计算规范请求的哈希值
    hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    
    # 构建签名字符串
    credential_scope = f"{short_date}/{region}/{service}/request"
    string_to_sign = "\n".join(["HMAC-SHA256", x_date, credential_scope, hashed_canonical_request])
    
    # 计算签名
    k_date = hmac.new(access_key_secret.encode("utf-8"), short_date.encode("utf-8"), hashlib.sha256).digest()
    k_region = hmac.new(k_date, region.encode("utf-8"), hashlib.sha256).digest()
    k_service = hmac.new(k_region, service.encode("utf-8"), hashlib.sha256).digest()
    k_signing = hmac.new(k_service, b"request", hashlib.sha256).digest()
    signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    
    # 构建Authorization头
    authorization = f"HMAC-SHA256 Credential={access_key_id}/{credential_scope}, SignedHeaders={signed_headers_str}, Signature={signature}"
    
    # 返回所有需要的头部
    return {
        "Host": host,
        "X-Content-Sha256": x_content_sha256,
        "X-Date": x_date,
        "Authorization": authorization
    }

def normalize_query(params):
    """规范化查询参数"""
    if not params:
        return ""
        
    query = ""
    for key in sorted(params.keys()):
        if isinstance(params[key], list):
            for k in params[key]:
                query += quote(key, safe="-_.~") + "=" + quote(str(k), safe="-_.~") + "&"
        else:
            query += quote(key, safe="-_.~") + "=" + quote(str(params[key]), safe="-_.~") + "&"
    
    return query[:-1].replace("+", "%20") if query else ""

class VolcengineAdapter(OpenAIAdapter):
    def __init__(self, config: VolcengineConfig):
        super().__init__(config)

    async def auto_detect_models(self) -> list[str]:
        """获取火山引擎可用的模型列表，支持分页获取所有结果"""
        host = "open.volcengineapi.com"
        path = "/"
        
        all_models = []
        page_number = 1
        page_size = 100
        total_pages = 1  # 初始值，会在第一次请求后更新
        
        while page_number <= total_pages:
            query = {
                "Action": "ListFoundationModels",
                "Version": "2024-01-01",
                "PageNumber": page_number,
                "PageSize": page_size
            }
            
            # 生成签名和头部
            headers = generate_volcengine_signature(
                self.config.access_key_id,
                self.config.access_key_secret,
                "GET", 
                path, 
                query
            )
            
            # 构建完整URL
            url = f"https://{host}{path}"
            
            async with aiohttp.ClientSession(trust_env=True) as session:
                async with session.get(url, headers=headers, params=query) as response:
                    response.raise_for_status()
                    response_data = await response.json()
                    
                    if "Result" in response_data:
                        response_data = response_data["Result"]
                    else:
                        return []
                    # 更新总页数（如果API返回了这个信息）
                    if "TotalCount" in response_data and "PageSize" in response_data:
                        total_count = response_data["TotalCount"]
                        total_pages = (total_count + page_size - 1) // page_size
                    # 提取模型信息，使用更简洁的链式判断
                    print(response_data)
                    for model in response_data["Items"]:
                        foundation_model = model.get("FoundationModelTag", {})
                        if ("LLM" in foundation_model.get("Domains", []) and
                            model.get("Name")):
                            all_models.append(model["Name"])
            # 准备获取下一页
            page_number += 1
        
        return all_models