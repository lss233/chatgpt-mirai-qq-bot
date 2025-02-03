from typing import Dict, Type, Optional
from framework.workflow_executor.workflow import Workflow
from framework.workflow_executor.builder import WorkflowBuilder
from framework.ioc.container import DependencyContainer
from framework.logger import get_logger
import os

class WorkflowRegistry:
    """工作流注册表，管理工作流的注册和获取"""
    
    def __init__(self, container: DependencyContainer):
        self._workflows: Dict[str, Type[WorkflowBuilder]] = {}
        self.logger = get_logger("WorkflowRegistry")
        self.container = container
        

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
        
    def load_workflows(self, workflows_dir: str = "data/workflows"):
        """从指定目录加载所有工作流定义"""
        if not os.path.exists(workflows_dir):
            os.makedirs(workflows_dir)
                    
        for file_name in os.listdir(workflows_dir):
            if not file_name.endswith('.yaml'):
                continue
                
            file_path = os.path.join(workflows_dir, file_name)
            try:
                workflow = WorkflowBuilder.load_from_yaml(file_path, self.container)
                # 从文件名解析 group_id 和 workflow_id
                name_without_ext = os.path.splitext(file_name)[0]
                if ':' not in name_without_ext:
                    self.logger.warning(f"Invalid workflow file name {file_name}, skipping")
                    continue
                    
                group_id, workflow_id = name_without_ext.split(':', 1)
                self.register(group_id, workflow_id, workflow)
                
            except Exception as e:
                self.logger.error(f"Failed to load workflow from {file_path}: {str(e)}")
                
    def create_workflow(self, name: str) -> Optional[Workflow]:
        """创建工作流实例"""
        builder = self.get(name)
        if not builder:
            return None
            
        return builder.build() 