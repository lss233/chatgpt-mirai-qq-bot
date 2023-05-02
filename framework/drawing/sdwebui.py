from typing import List
import base64
import httpx
from graia.ariadne.message.element import Image

from config import SDWebUIParams
from .base import DrawAI


def basic_auth_encode(authorization: str) -> str:
    authorization_bytes = authorization.encode('utf-8')
    encoded_authorization = base64.b64encode(authorization_bytes).decode('utf-8')
    return f"Basic {encoded_authorization}"

class SDWebUI(DrawAI):

    def __init__(self, params: SDWebUIParams):
        self.params = params
        self.client = httpx.AsyncClient(timeout=params.timeout)
        if params.authorization:
            self.client.headers["Authorization"] = basic_auth_encode(params.authorization)

    async def text_to_img(self, prompt):
        payload = {
            'enable_hr': 'false',
            'denoising_strength': 0.45,
            'prompt': f'{self.params.prompt_prefix}, {prompt}',
            'steps': 15,
            'seed': -1,
            'batch_size': 1,
            'n_iter': 1,
            'cfg_scale': 7.5,
            'restore_faces': 'false',
            'tiling': 'false',
            'negative_prompt': self.params.negative_prompt,
            'eta': 0,
            'sampler_index': self.params.sampler_index
        }

        for key, value in self.params.dict(exclude_none=True).items():
            if isinstance(value, bool):
                payload[key] = 'true' if value else 'false'
            else:
                payload[key] = value

        resp = await self.client.post(f"{self.params.api_url}sdapi/v1/txt2img", json=payload)
        resp.raise_for_status()
        r = resp.json()

        return [Image(base64=i) for i in r.get('images', [])]

    async def img_to_img(self, init_images: List[Image], prompt=''):
        payload = {
            'init_images': [x.base64 for x in init_images],
            'enable_hr': 'false',
            'denoising_strength': 0.45,
            'prompt': f'{self.params.prompt_prefix}, {prompt}',
            'steps': 15,
            'seed': -1,
            'batch_size': 1,
            'n_iter': 1,
            'cfg_scale': 7.5,
            'restore_faces': 'false',
            'tiling': 'false',
            'negative_prompt': self.params.negative_prompt,
            'eta': 0,
            'sampler_index': self.params.sampler_index,
            "filter_nsfw": 'true' if self.params.filter_nsfw else 'false',
        }

        for key, value in self.params.dict(exclude_none=True).items():
            if isinstance(value, bool):
                payload[key] = 'true' if value else 'false'
            else:
                payload[key] = value

        resp = await self.client.post(f"{self.params.api_url}sdapi/v1/img2img", json=payload)
        resp.raise_for_status()
        r = resp.json()
        return [Image(base64=i) for i in r.get('images', [])]
