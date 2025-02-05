from typing import Dict, Type, Optional
from framework.workflow.core.workflow import Workflow
from framework.ioc.container import DependencyContainer
from framework.logger import get_logger
import os

from framework.workflow.core.workflow.builder import WorkflowBuilder

class WorkflowRegistry:
    """工作流注册表，管理工作流的注册和获取"""
    
    WORKFLOWS_DIR = "data/workflows"
    
    def __init__(self, container: DependencyContainer):
        self._workflows: Dict[str, Type[WorkflowBuilder]] = {}
        self.logger = get_logger("WorkflowRegistry")
        self.container = container
        
    @classmethod
    def get_workflow_path(cls, group_id: str, workflow_id: str) -> str:
        """获取工作流文件路径"""
        group_dir = os.path.join(cls.WORKFLOWS_DIR, group_id)
        if not os.path.exists(group_dir):
            os.makedirs(group_dir)
        return os.path.join(group_dir, f"{workflow_id}.yaml")

    def register(self, group_id: str, workflow_id: str, workflow_builder: Type[WorkflowBuilder]):
        """注册一个工作流"""
        full_name = f"{group_id}:{workflow_id}"
        if full_name in self._workflows:
            self.logger.warning(f"Workflow {full_name} already registered, overwriting")
        self._workflows[full_name] = workflow_builder
        self.logger.info(f"Registered workflow: {full_name}")
        
    def get(self, name: str) -> Optional[Type[WorkflowBuilder]]:
        """获取工作流构建器"""
        return self._workflows.get(name)
        
    def load_workflows(self, workflows_dir: str = None):
        """从指定目录加载所有工作流定义"""
        workflows_dir = workflows_dir or self.WORKFLOWS_DIR
        if not os.path.exists(workflows_dir):
            os.makedirs(workflows_dir)
                    
        # 遍历所有组目录
        for group_id in os.listdir(workflows_dir):
            group_dir = os.path.join(workflows_dir, group_id)
            if not os.path.isdir(group_dir):
                continue
                
            # 遍历组内的工作流文件
            for file_name in os.listdir(group_dir):
                if not file_name.endswith('.yaml'):
                    continue
                    
                workflow_id = os.path.splitext(file_name)[0]
                file_path = os.path.join(group_dir, file_name)
                
                try:
                    workflow = WorkflowBuilder.load_from_yaml(file_path, self.container)
                    self.register(group_id, workflow_id, workflow)
                except Exception as e:
                    self.logger.error(f"Failed to load workflow from {file_path}: {str(e)}")