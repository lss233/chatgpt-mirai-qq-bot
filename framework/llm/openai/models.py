import httpx
import openai
from pydantic import Field

from framework.accounts import AccountInfoBaseModel
import revChatGPT.V1 as ChatGPTV1


class OpenAIWebAuthBaseModel(AccountInfoBaseModel):
    paid: bool = Field(
        default=False,
        description="使用 ChatGPT Plus",
    )
    model: str = Field(
        default='text-davinci-002-render-sha',
        description="使用的默认模型，此选项优先级最高",
    )
    verbose: bool = Field(
        default=False,
        description="启用详尽日志模式",
    )
    title_pattern: str = Field(
        default="",
        description="自动修改标题，为空则不修改",
    )
    auto_remove_old_conversations: bool = Field(
        default=False,
        description="自动删除旧的对话",
    )

    async def check_alive(self) -> bool:
        raise NotImplemented("check_alive() for this method is not implemented")


class OpenAIAccessTokenAuth(OpenAIWebAuthBaseModel):
    access_token: str = Field(
        description="OpenAI 的 access_token",
    )

    class Config:
        title = 'ChatGPT 网页版 账号设置'
        schema_extra = {
            "description": "配置教程：[Wiki](https://chatgpt-qq.lss233.com/pei-zhi-wen-jian-jiao-cheng/jie-ru-ai-ping-tai/jie-ru-openai-de-chatgpt#jie-ru-wang-ye-ban-openai-chatgpt)"
        }

    async def check_alive(self) -> bool:
        """
        Successful response:
        ```
        {
            "detail": [
                {
                    "loc": [
                        "body"
                    ],
                    "msg": "field required",
                    "type": "value_error.missing"
                }
            ]
        }
        ```
        Failed response: variety
        """
        async with httpx.AsyncClient(timeout=10, trust_env=True) as client:
            response = await client.post(url=f"{ChatGPTV1.BASE_URL}conversation",
                                         headers={'Authorization': f'Bearer {self.access_token}'})

            return 'value_error.missing' in response.text


class OpenAIAPIKeyAuth(AccountInfoBaseModel):
    api_key: str = Field(
        description="OpenAI 的 api_key",
    )

    class Config:
        title = 'OpenAI API 账号设置'
        schema_extra = {
            "description": "配置教程：[Wiki](https://chatgpt-qq.lss233.com/pei-zhi-wen-jian-jiao-cheng/jie-ru-ai-ping-tai/jie-ru-openai-de-chatgpt#jie-ru-api-ban-openai-chatgpt)"
        }

    async def check_alive(self) -> bool:
        async with httpx.AsyncClient() as client:
            response = await client.post(f'{openai.api_base}/chat/completions',
                                         headers={'Authorization': f'Bearer {self.api_key}'},
                                         json={"model": "gpt-3.5-turbo", "messages": []}
                                         )

            return 'invalid_request_error' in response.text
