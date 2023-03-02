# encoding:utf-8

from loguru import logger
from config import Config
import openai
import uuid

config = Config.load_config()


# OpenAI对话模型API (可用)
class OpenAIBot:
    def __init__(self):
        openai.api_key = config.openai.secret_key

    def ask(self, type, prompt, conversation_id=None, parent_id=None):
        resp = dict()
        if conversation_id is None:
            conversation_id = uuid.uuid1()
        if parent_id is None:
            parent_id = uuid.uuid1()
        resp['conversation_id'] = conversation_id
        resp['parent_id'] = parent_id
        if type == 'create_img':
            resp['message'] = "![img](" + self.create_img(prompt[1:] + ")")
        return resp

    def reply_text(self, query):
        try:
            response = openai.Completion.create(
                model="text-davinci-003",  # 对话模型的名称
                prompt=query,
                temperature=0.9,  # 值在[0,1]之间，越大表示回复越具有不确定性
                max_tokens=2000,  # 回复最大的字符数
                top_p=1,
                frequency_penalty=0.0,  # [-2,2]之间，该值越大则更倾向于产生不同的内容
                presence_penalty=0.0,  # [-2,2]之间，该值越大则更倾向于产生不同的内容
                stop=["#"]
            )
            res_content = response.choices[0]["text"].strip().rstrip("<|im_end|>")
        except Exception as e:
            logger.exception(e)
            return "~!@#$%^&*"
            # Session.clear_session(user_id)
            # return None
        logger.info(f"[OPEN_AI] reply={res_content}")
        return res_content

    def create_img(self, query):
        try:
            logger.info(f"[OPEN_AI] image_query={query}")
            response = openai.Image.create(
                prompt=query,  # 图片描述
                n=1,  # 每次生成图片的数量
                size="512x512"  # 图片大小,可选有 256x256, 512x512, 1024x1024
            )
            image_url = response['data'][0]['url']
            logger.info(f"[OPEN_AI] image_url={image_url}")
        except Exception as e:
            logger.exception(e)
            return None
        return image_url

    def edit_img(self, query, src_img):
        try:
            response = openai.Image.create_edit(
                image=open(src_img, 'rb'),
                mask=open('cat-mask.png', 'rb'),
                prompt=query,
                n=1,
                size='512x512'
            )
            image_url = response['data'][0]['url']
            logger.info(f"[OPEN_AI] image_url={image_url}")
        except Exception as e:
            logger.exception(e)
            return None
        return image_url

    def migration_img(self, query, src_img):

        try:
            response = openai.Image.create_variation(
                image=open(src_img, 'rb'),
                n=1,
                size="512x512"
            )
            image_url = response['data'][0]['url']
            logger.info(f"[OPEN_AI] image_url={image_url}")
        except Exception as e:
            logger.exception(e)
            return None
        return image_url

    def append_question_mark(self, query):
        end_symbols = [".", "。", "?", "？", "!", "！"]
        for symbol in end_symbols:
            if query.endswith(symbol):
                return query
        return query + "?"
