import g4f
from loguru import logger

from adapter.common.chat_helper import ChatMessage, ROLE_USER
from config import G4fModels


def g4f_check_account(account: G4fModels):

    try:
        response = g4f.ChatCompletion.create(
            model=eval(account.model) if account.model.startswith("g4f.models.") else account.model,
            provider=eval(account.provider),
            messages=[vars(ChatMessage(ROLE_USER, "hello"))],
        )
        logger.debug(f"g4f model ({vars(account)}) is active. hello -> {response}")
    except KeyError as e:
        logger.debug(f"g4f model ({vars(account)}) is inactive. hello -> {e}")
        return False
    return True


def parse(model_alias: str):
    from constants import botManager
    return next(
        (
            model
            for model in botManager.bots["gpt4free"]
            if model_alias == model.alias
        ),
        None
    )
