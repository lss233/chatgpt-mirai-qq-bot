from typing import Any, List, Optional

from pydantic import BaseModel

from kirara_ai.llm.format.message import LLMChatMessage


class ResponseFormat(BaseModel):
    type: Optional[str] = None


class LLMChatRequest(BaseModel):
    messages: Optional[List[LLMChatMessage]] = None
    model: Optional[str] = None
    frequency_penalty: Optional[int] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[int] = None
    response_format: Optional[ResponseFormat] = None
    stop: Optional[Any] = None
    stream: Optional[bool] = None
    stream_options: Optional[Any] = None
    temperature: Optional[int] = None
    top_p: Optional[int] = None
    tools: Optional[Any] = None
    tool_choice: Optional[str] = None
    logprobs: Optional[bool] = None
    top_logprobs: Optional[Any] = None
