from typing import List

import httpx
from graia.ariadne.message.element import Image

from constants import config
from .base import DrawingAPI


class SDWebUI(DrawingAPI):

    async def text_to_img(self, prompt):
        payload = {
            'enable_hr': 'false',
            'denoising_strength': 0.45,
            'prompt': f'{config.sdwebui.prompt_prefix}, {prompt}',
            'steps': 15,
            'seed': -1,
            'batch_size': 1,
            'n_iter': 1,
            'cfg_scale': 7.5,
            'restore_faces': 'false',
            'tiling': 'false',
            'negative_prompt': config.sdwebui.negative_prompt,
            'eta': 0,
            'sampler_index': config.sdwebui.sampler_index,
            "filter_nsfw": 'true' if config.sdwebui.filter_nsfw else 'false',
        }
        resp = await httpx.AsyncClient(timeout=config.sdwebui.timeout).post(f"{config.sdwebui.api_url}sdapi/v1/txt2img", json=payload)
        resp.raise_for_status()
        r = resp.json()

        return [Image(base64=i) for i in r.get('images', [])]


    async def img_to_img(self, init_images: List[Image], prompt=''):
        payload = {
            'init_images': [x.base64 for x in init_images],
            'enable_hr': 'false',
            'denoising_strength': 0.45,
            'prompt': f'{config.sdwebui.prompt_prefix}, {prompt}',
            'steps': 15,
            'seed': -1,
            'batch_size': 1,
            'n_iter': 1,
            'cfg_scale': 7.5,
            'restore_faces': 'false',
            'tiling': 'false',
            'negative_prompt': config.sdwebui.negative_prompt,
            'eta': 0,
            'sampler_index': config.sdwebui.sampler_index,
            "filter_nsfw": 'true' if config.sdwebui.filter_nsfw else 'false',
        }
        resp = await httpx.AsyncClient(timeout=config.sdwebui.timeout).post(f"{config.sdwebui.api_url}sdapi/v1/img2img", json=payload)
        resp.raise_for_status()
        r = resp.json()
        return [Image(base64=i) for i in r.get('images', [])]
