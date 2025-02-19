from framework.im.adapter import IMAdapter
from framework.im.message import IMMessage
from framework.ioc.container import DependencyContainer
from framework.logger import get_logger
from framework.workflow.core.block.registry import BlockRegistry
from framework.workflow.core.dispatch.registry import DispatchRuleRegistry
from framework.workflow.core.dispatch.rules.base import DispatchRule
from framework.workflow.core.execution.executor import WorkflowExecutor
from framework.workflow.core.workflow.base import Workflow
from framework.workflow.core.workflow.registry import WorkflowRegistry


class WorkflowDispatcher:
    """工作流调度器"""

    def __init__(self, container: DependencyContainer):
        self.container = container
        self.logger = get_logger("WorkflowDispatcher")

        # 从容器获取注册表
        self.workflow_registry = container.resolve(WorkflowRegistry)
        self.dispatch_registry = container.resolve(DispatchRuleRegistry)

    def register_rule(self, rule: DispatchRule):
        """注册一个调度规则"""
        self.dispatch_registry.register(rule)
        self.logger.info(f"Registered dispatch rule: {rule}")

    async def dispatch(self, source: IMAdapter, message: IMMessage):
        """
        根据消息内容选择第一个匹配的规则进行处理
        """
        # 获取所有已启用的规则，按优先级排序
        active_rules = self.dispatch_registry.get_active_rules()

        for rule in active_rules:
            if rule.match(message, self.workflow_registry):
                try:
                    self.logger.debug(f"Matched rule {rule}, executing workflow")
                    with self.container.scoped() as scoped_container:
                        block_registry = self.container.resolve(BlockRegistry)
                        scoped_container.register(IMAdapter, source)
                        scoped_container.register(IMMessage, message)
                        workflow = rule.get_workflow(scoped_container)
                        if workflow is None:
                            self.logger.error(f"Workflow {rule} not found")
                            continue
                        executor = WorkflowExecutor(workflow, block_registry)
                        scoped_container.register(Workflow, workflow)
                        scoped_container.register(WorkflowExecutor, executor)
                        return await executor.run()
                except Exception as e:
                    self.logger.exception(e)
                    self.logger.error(f"Workflow execution failed: {e}")
                    raise e
        self.logger.debug("No matching rule found for message")
        return None
