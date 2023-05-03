import itertools
from typing import Type, TypeVar, Dict, List, Any, Optional

import asyncio
from loguru import logger
from pydantic import BaseConfig
from pydantic.fields import ModelField

from config import AccountsModel
from framework.exceptions import NoAvailableBotException

from .models import AccountInfoBaseModel

CT = TypeVar('CT', bound=AccountInfoBaseModel)


class AccountManager:
    registered_models: Dict[str, Type[CT]] = {}
    """已向系统注册的账号列表"""

    loaded_accounts: Dict[str, List[CT]] = {}
    """已加载的账号列表"""

    _roundrobin: Dict[str, Any] = {}

    def register_type(self, name: str, model: Type[CT]):
        """注册账号类型"""
        self.registered_models[name] = model
        AccountsModel.__fields__[name] = ModelField(
            name=name,
            type_=Optional[List[model]],
            class_validators=None,
            default=[],
            model_config=BaseConfig
        )
        logger.debug(f"[AccountManager] 注册账号类型：{name}")

    def pick(self, type_: str) -> CT:
        """从可用的账号列表中按照轮盘法选择一个账号"""
        if (
            type_ not in self.loaded_accounts
            or len(self.loaded_accounts[type_]) < 1
        ):
            raise NoAvailableBotException(type_)

        if type_ not in self._roundrobin:
            self._roundrobin[type_] = itertools.cycle(self.loaded_accounts[type_])
        return next(self._roundrobin[type_])

    async def login_account(self, type_: str, account: CT):
        """登录单个账号"""
        try:
            if await account.check_alive():
                if type_ not in self.loaded_accounts:
                    self.loaded_accounts[type_] = []
                account.ok = True
                self.loaded_accounts[type_].append(account)
                logger.success(f"[AccountManager] 登录成功: {type_}")
            else:
                account.ok = False
                logger.error(f"[AccountManager] 登录失败: {type_}")
        except Exception as e:
            account.ok = False
            logger.error(f"[AccountManager] 登录失败: {type_} with exception: {e}")


    async def load_accounts(self, accounts_model: AccountsModel):
        """从配置文件中加载所有账号"""
        self.loaded_accounts = {}
        tasks = []
        for field in accounts_model.__fields__.keys():
            tasks.extend(
                asyncio.create_task(self.login_account(field, account))
                for account in accounts_model.__getattribute__(field)
            )
        before_logins = len(tasks)
        await asyncio.gather(*tasks, return_exceptions=True)
        after_logins = sum(len(models) for _, models in self.loaded_accounts.items())
        logger.debug(f"[AccountManager] 登录完毕，共有 {after_logins}/{before_logins} 个账号成功登录。")


account_manager = AccountManager()
