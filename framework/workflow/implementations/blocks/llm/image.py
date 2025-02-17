import base64
from typing import Any, Dict, Optional

import requests

from framework.im.message import ImageMessage
from framework.workflow.core.block import Block
from framework.workflow.core.block.input_output import Input, Output


class SimpleStableDiffusionWebUI(Block):
    name = "simple_stable_diffusion_webui"
    inputs = {
        "prompt": Input("prompt", "提示", str, "提示"),
        "negative_prompt": Input("negative_prompt", "负面提示", str, "负面提示"),
    }
    outputs = {"image": Output("image", "图片", ImageMessage, "生成的图片")}

    def __init__(
        self,
        api_url: str,
        *,
        steps: int = 20,
        sampler_index: str = "Euler a",
        cfg_scale: float = 7.0,
        width: int = 512,
        height: int = 512,
        ckpt_name: Optional[str] = None,
        clip_skip: int = 1,
    ):
        self.api_url = api_url
        self.steps = steps
        self.sampler_index = sampler_index
        self.cfg_scale = cfg_scale
        self.width = width
        self.height = height
        self.ckpt_name = ckpt_name
        self.clip_skip = clip_skip

    def execute(self, prompt: str, negative_prompt: str) -> Dict[str, Any]:
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "steps": self.steps,
            "sampler_index": self.sampler_index,
            "cfg_scale": self.cfg_scale,
            "width": self.width,
            "height": self.height,
        }
        if self.ckpt_name:
            payload["ckpt_name"] = self.ckpt_name
        payload["clip_skip"] = self.clip_skip
        response = requests.post(url=f"{self.api_url}/sdapi/v1/txt2img", json=payload)

        if response.status_code == 200:
            r = response.json()
            # Assuming the API returns the image in base64 format
            # and it's the first image in the list
            if "images" in r and r["images"]:
                image_base64 = r["images"][0]
                image_bytes = base64.b64decode(image_base64)
                image_message = ImageMessage(
                    data=image_bytes, format="png"
                )  # 假设是 PNG 格式
                return {"image": image_message}
            else:
                raise Exception("No image data found in the response")
        else:
            raise Exception(
                f"API request failed with status code: {response.status_code}, message: {response.text}"
            )
