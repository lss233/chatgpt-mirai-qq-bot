from typing import List
from framework.im.adapter import IMAdapter
from framework.im.message import IMMessage
from framework.ioc.container import DependencyContainer
from framework.logger import get_logger
from framework.workflow_dispatcher.dispatch_rule import DispatchRule, FallbackMatchRule
from framework.workflow_executor.executor import WorkflowExecutor


class WorkflowDispatcher:
    def __init__(self, container: DependencyContainer):
        self.container = container
        self.logger = get_logger("WorkflowDispatcher")
        self.dispatch_rules: List[DispatchRule] = []
        self.__init_fallback()

    def __init_fallback(self):
        """初始化默认的兜底规则"""
        from framework.workflows.default.factory import DefaultWorkflowFactory
        fallback_factory = DefaultWorkflowFactory()
        self.dispatch_rules.append(FallbackMatchRule(fallback_factory))
        self.logger.info("Registered fallback dispatch rule")

    def register_rule(self, rule: DispatchRule):
        """注册一个调度规则"""
        self.dispatch_rules.append(rule)
        self.logger.info(f"Registered dispatch rule: {rule}")

    async def dispatch(self, source: IMAdapter, message: IMMessage):
        """
        根据消息内容选择第一个匹配的规则进行处理
        """
        for rule in self.dispatch_rules:
            if rule.match(message):
                self.logger.debug(f"Matched rule {rule}, executing workflow")
                with self.container.scoped() as scoped_container:
                    scoped_container.register(IMAdapter, source)
                    scoped_container.register(IMMessage, message)
                    # 此处构造出实际的 workflow 对象，使用的容器是注入了当前上下文的 container
                    workflow = rule.get_workflow(scoped_container)
                    executor = WorkflowExecutor(workflow)
                    return await executor.run()
                
        self.logger.debug("No matching rule found for message")
        return None