import pytest
from datetime import datetime, timedelta

import pytest_asyncio
from framework.web.app import create_app
from framework.ioc.container import DependencyContainer
from framework.config.global_config import GlobalConfig, WebConfig
from framework.workflow.core.workflow import WorkflowRegistry, Workflow, Wire
from framework.workflow.core.workflow.builder import WorkflowBuilder
from framework.workflow.core.block import Block, BlockRegistry
from framework.workflow.core.workflow.input_output import Input, Output
from framework.web.auth.routes import create_access_token
from unittest.mock import patch

# ==================== 常量区 ====================
TEST_PASSWORD = "test-password"
TEST_SECRET_KEY = "test-secret-key"
TEST_GROUP_ID = "test-group"
TEST_WORKFLOW_ID = "test-workflow"
TEST_WORKFLOW_ID_NEW = "test-workflow-new"
TEST_WORKFLOW_NAME = "Test Workflow"
TEST_WORKFLOW_NAME_NEW = "Test Workflow New"
TEST_WORKFLOW_DESC = "A test workflow"


# ==================== 测试用Block ====================
class MessageBlock(Block):
    def __init__(self, container: DependencyContainer, text: str = ""):
        inputs = {}
        outputs = {"output": Output("output", str, "Output message")}
        super().__init__("message_block", inputs, outputs)
        self.config = {"text": text}
        self.position = {"x": 0, "y": 0}

    def execute(self) -> dict:
        return {"output": self.config["text"]}

class LLMBlock(Block):
    def __init__(self, container: DependencyContainer, prompt: str = ""):
        inputs = {"input": Input("input", str, "Input message")}
        outputs = {"output": Output("output", str, "Output message")}
        super().__init__("llm_block", inputs, outputs)
        self.config = {"prompt": prompt}
        self.position = {"x": 200, "y": 0}

    def execute(self, input: str) -> dict:
        return {"output": f"Response to: {input}"}

# ==================== Fixtures ====================
@pytest.fixture
def app():
    """创建测试应用实例"""
    container = DependencyContainer()
    
    # 配置
    config = GlobalConfig()
    config.web = WebConfig(
        secret_key=TEST_SECRET_KEY,
        password_file="test_password.hash"
    )
    container.register(GlobalConfig, config)
    
    # 创建并注册 BlockRegistry
    block_registry = BlockRegistry()
    block_registry.register("message", "test", MessageBlock)
    block_registry.register("llm", "test", LLMBlock)
    container.register(BlockRegistry, block_registry)
    
    # 创建工作流
    builder = (WorkflowBuilder(TEST_WORKFLOW_NAME, container)
        .use(MessageBlock, text="Hello")
        .chain(LLMBlock, prompt="How are you?")
        .build())
    
    # 创建并注册 WorkflowRegistry
    registry = WorkflowRegistry(container)
    registry.register(TEST_GROUP_ID, TEST_WORKFLOW_ID, builder)
    container.register(WorkflowRegistry, registry)
    

    app = create_app(container)
    app.container = container
    return app

@pytest.fixture
def test_client(app):
    """创建测试客户端"""
    return app.test_client()

@pytest_asyncio.fixture
async def auth_headers(test_client):
    """获取认证头"""
    with patch('framework.web.auth.routes.verify_saved_password', return_value=True):
        response = await test_client.post('/api/auth/login', json={
            'password': TEST_PASSWORD
        })
        data = await response.get_json()
        assert response.status_code == 200
        token = data['access_token']
        return {'Authorization': f'Bearer {token}'}

# ==================== 测试用例 ====================
class TestWorkflow:
    @pytest.mark.asyncio
    async def test_list_workflows(self, test_client, auth_headers):
        """测试获取工作流列表"""
        response = await test_client.get('/api/workflow', headers=auth_headers)
        data = await response.get_json()
        assert "error" not in data
        assert "workflows" in data
        workflows = data["workflows"]
        assert len(workflows) == 1
        workflow = workflows[0]
        assert workflow["workflow_id"] == TEST_WORKFLOW_ID
        assert workflow["group_id"] == TEST_GROUP_ID
        assert workflow["name"] == TEST_WORKFLOW_NAME

    @pytest.mark.asyncio
    async def test_get_workflow(self, test_client, auth_headers):
        """测试获取单个工作流"""
        response = await test_client.get(
            f'/api/workflow/{TEST_GROUP_ID}/{TEST_WORKFLOW_ID}',
            headers=auth_headers
        )
        data = await response.get_json()
        assert "error" not in data
        assert "workflow" in data
        workflow = data["workflow"]
        assert workflow["workflow_id"] == TEST_WORKFLOW_ID
        assert workflow["group_id"] == TEST_GROUP_ID
        assert workflow["name"] == TEST_WORKFLOW_NAME
        assert len(workflow["blocks"]) == 2
        assert len(workflow["wires"]) == 1

    @pytest.mark.asyncio
    async def test_create_workflow(self, test_client, auth_headers):
        """测试创建工作流"""
        workflow_data = {
            'workflow_id': TEST_WORKFLOW_ID_NEW,
            'group_id': TEST_GROUP_ID,
            'name': TEST_WORKFLOW_NAME,
            'description': TEST_WORKFLOW_DESC,
            'blocks': [
                {
                    'block_id': 'node1',
                    'type_name': 'test:message',
                    'name': 'Message Node',
                    'config': {'text': 'Hello'},
                    'position': {'x': 0, 'y': 0}

                }
            ],
            'wires': []
        }
        
        response = await test_client.post(
            f'/api/workflow/{TEST_GROUP_ID}/{TEST_WORKFLOW_ID_NEW}',
            headers=auth_headers,
            json=workflow_data
        )
        
        data = await response.get_json()
        assert "error" not in data
        assert data['workflow_id'] == TEST_WORKFLOW_ID_NEW
        assert data['group_id'] == TEST_GROUP_ID
        assert data['name'] == TEST_WORKFLOW_NAME
        assert len(data['blocks']) == 1

    @pytest.mark.asyncio
    async def test_update_workflow(self, test_client, auth_headers):
        """测试更新工作流"""
        workflow_data = {
            'workflow_id': TEST_WORKFLOW_ID,
            'group_id': TEST_GROUP_ID,
            'name': 'Updated Workflow',
            'description': 'Updated workflow description',
            'blocks': [
                {
                    'block_id': 'node1',
                    'type_name': 'test:message',
                    'name': 'Message Node',
                    'config': {'text': 'Updated text'},
                    'position': {'x': 0, 'y': 0}

                }
            ],
            'wires': []
        }
        
        response = await test_client.put(
            f'/api/workflow/{TEST_GROUP_ID}/{TEST_WORKFLOW_ID}',
            headers=auth_headers,
            json=workflow_data
        )
        
        data = await response.get_json()
        assert "error" not in data
        assert data['workflow_id'] == TEST_WORKFLOW_ID
        assert data['group_id'] == TEST_GROUP_ID
        assert data['name'] == 'Updated Workflow'
        assert data['description'] == 'Updated workflow description'
        assert len(data['blocks']) == 1
        assert data['blocks'][0]['config']['text'] == 'Updated text'

    @pytest.mark.asyncio
    async def test_delete_workflow(self, test_client, auth_headers):
        """测试删除工作流"""
        response = await test_client.delete(
            f'/api/workflow/{TEST_GROUP_ID}/{TEST_WORKFLOW_ID}',
            headers=auth_headers
        )
        
        data = await response.get_json()
        assert "error" not in data
        assert "message" in data
        assert data["message"] == "Workflow deleted successfully" 