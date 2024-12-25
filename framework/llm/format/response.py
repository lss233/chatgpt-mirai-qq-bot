from typing import Optional, List
from pydantic import BaseModel

class Function(BaseModel):
    name: Optional[str] = None
    arguments: Optional[str] = None

class ToolCall(BaseModel):
    id: Optional[str] = None
    type: Optional[str] = None
    function: Optional[Function] = None

class Message(BaseModel):
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    role: Optional[str] = None

class TopLogprob(BaseModel):
    token: Optional[str] = None
    logprob: Optional[int] = None
    bytes: Optional[List[int]] = None

class ContentItem(BaseModel):
    token: Optional[str] = None
    logprob: Optional[int] = None
    bytes: Optional[List[int]] = None
    top_logprobs: Optional[List[TopLogprob]] = None

class Logprobs(BaseModel):
    content: Optional[List[ContentItem]] = None

class Usage(BaseModel):
    completion_tokens: Optional[int] = None
    prompt_tokens: Optional[int] = None
    total_tokens: Optional[int] = None

class LLMChatResponseContent(BaseModel):
    finish_reason: Optional[str] = None
    index: Optional[int] = None
    message: Optional[Message] = None
    logprobs: Optional[Logprobs] = None

class LLMChatResponse(BaseModel):
    content: Optional[List[LLMChatResponseContent]] = None
    model: Optional[str] = None
    usage: Optional[Usage] = None