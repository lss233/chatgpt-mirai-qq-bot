from framework.im.adapter import IMAdapter
from framework.im.message import IMMessage
from framework.ioc.container import DependencyContainer
from framework.logger import get_logger
from framework.workflow.core.workflow.registry import WorkflowRegistry
from framework.workflow.core.dispatch.registry import DispatchRuleRegistry
from framework.workflow.core.dispatch.rule import DispatchRule, FallbackMatchRule
from framework.workflow.core.execution.executor import WorkflowExecutor
from framework.workflow.implementations.factories.default_factory import DefaultWorkflowFactory


class WorkflowDispatcher:
    """工作流调度器"""
    def __init__(self, container: DependencyContainer):
        self.container = container
        self.logger = get_logger("WorkflowDispatcher")
        
        # 从容器获取注册表
        self.workflow_registry = container.resolve(WorkflowRegistry)
        self.dispatch_registry = container.resolve(DispatchRuleRegistry)
        
        # 初始化默认的兜底规则
        self.__init_fallback()

    def __init_fallback(self):
        """初始化默认的兜底规则"""
        fallback_factory = DefaultWorkflowFactory()
        self.dispatch_registry.register(FallbackMatchRule(fallback_factory.create_default_workflow))
        self.logger.info("Registered fallback dispatch rule")

    def register_rule(self, rule: DispatchRule):
        """注册一个调度规则"""
        self.dispatch_registry.register(rule)
        self.logger.info(f"Registered dispatch rule: {rule}")

    async def dispatch(self, source: IMAdapter, message: IMMessage):
        """
        根据消息内容选择第一个匹配的规则进行处理
        """
        for rule in self.dispatch_registry.get_rules():
            if rule.match(message):
                self.logger.debug(f"Matched rule {rule}, executing workflow")
                with self.container.scoped() as scoped_container:
                    scoped_container.register(IMAdapter, source)
                    scoped_container.register(IMMessage, message)
                    workflow = rule.get_workflow(scoped_container)
                    executor = WorkflowExecutor(workflow)
                    return await executor.run()
                
        self.logger.debug("No matching rule found for message")
        return None