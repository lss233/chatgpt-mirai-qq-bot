
import pytest

from kirara_ai.config.global_config import GlobalConfig, WebConfig
from kirara_ai.ioc.container import DependencyContainer
from kirara_ai.web.app import create_app
from kirara_ai.workflow.core.block import Block, BlockRegistry
from kirara_ai.workflow.core.block.input_output import Input, Output
from kirara_ai.workflow.core.workflow import WorkflowRegistry
from kirara_ai.workflow.core.workflow.builder import WorkflowBuilder
from tests.utils.auth_test_utils import auth_headers, setup_auth_service  # noqa

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
    name = "message_block"
    inputs = {}
    outputs = {"output": Output("output", "输出", str, "Output message")}
    container: DependencyContainer

    def __init__(self, text: str = ""):
        self.config = {"text": text}
        self.position = {"x": 0, "y": 0}

    def execute(self) -> dict:
        return {"output": self.config["text"]}


class LLMBlock(Block):
    name = "llm_block"
    inputs = {"input": Input("input", "输入", str, "Input message")}
    outputs = {"output": Output("output", "输出", str, "Output message")}
    container: DependencyContainer

    def __init__(self, prompt: str = ""):
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
        secret_key=TEST_SECRET_KEY, password_file="test_password.hash"
    )
    container.register(GlobalConfig, config)

    # 设置认证服务
    setup_auth_service(container)

    # 创建并注册 BlockRegistry
    block_registry = BlockRegistry()
    block_registry.register("message", "test", MessageBlock)
    block_registry.register("llm", "test", LLMBlock)
    container.register(BlockRegistry, block_registry)

    # 创建工作流
    builder = (
        WorkflowBuilder(TEST_WORKFLOW_NAME)
        .use(MessageBlock, text="Hello")
        .chain(LLMBlock, prompt="How are you?")
    )

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


# ==================== 测试用例 ====================
class TestWorkflow:
    @pytest.mark.asyncio
    async def test_list_workflows(self, test_client, auth_headers):
        """测试获取工作流列表"""
        response = await test_client.get(
            "/backend-api/api/workflow", headers=auth_headers
        )
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
            f"/backend-api/api/workflow/{TEST_GROUP_ID}/{TEST_WORKFLOW_ID}",
            headers=auth_headers,
        )
        data = await response.get_json()
        assert "error" not in data
        assert "workflow" in data
        workflow = data["workflow"]
        assert workflow["workflow_id"] == TEST_WORKFLOW_ID
        assert workflow["group_id"] == TEST_GROUP_ID
        assert workflow["name"] == TEST_WORKFLOW_NAME
        assert len(workflow["wires"]) == 1

    @pytest.mark.asyncio
    async def test_create_workflow(self, test_client, auth_headers):
        """测试创建工作流"""
        workflow_data = {
            "workflow_id": TEST_WORKFLOW_ID_NEW,
            "group_id": TEST_GROUP_ID,
            "name": TEST_WORKFLOW_NAME,
            "description": TEST_WORKFLOW_DESC,
            "blocks": [
                {
                    "block_id": "node1",
                    "type_name": "test:message",
                    "name": "Message Node",
                    "config": {"text": "Hello"},
                    "position": {"x": 0, "y": 0},
                }
            ],
            "wires": [],
        }

        response = await test_client.post(
            f"/backend-api/api/workflow/{TEST_GROUP_ID}/{TEST_WORKFLOW_ID_NEW}",
            headers=auth_headers,
            json=workflow_data,
        )

        data = await response.get_json()
        assert "error" not in data
        assert data["workflow_id"] == TEST_WORKFLOW_ID_NEW
        assert data["group_id"] == TEST_GROUP_ID
        assert data["name"] == TEST_WORKFLOW_NAME
        assert len(data["blocks"]) == 1

    @pytest.mark.asyncio
    async def test_update_workflow(self, test_client, auth_headers):
        """测试更新工作流"""
        workflow_data = {
            "workflow_id": TEST_WORKFLOW_ID,
            "group_id": TEST_GROUP_ID,
            "name": "Updated Workflow",
            "description": "Updated workflow description",
            "blocks": [
                {
                    "block_id": "node1",
                    "type_name": "test:message",
                    "name": "Message Node",
                    "config": {"text": "Updated text"},
                    "position": {"x": 0, "y": 0},
                }
            ],
            "wires": [],
        }

        response = await test_client.put(
            f"/backend-api/api/workflow/{TEST_GROUP_ID}/{TEST_WORKFLOW_ID}",
            headers=auth_headers,
            json=workflow_data,
        )

        data = await response.get_json()
        assert "error" not in data
        assert data["workflow_id"] == TEST_WORKFLOW_ID
        assert data["group_id"] == TEST_GROUP_ID
        assert data["name"] == "Updated Workflow"
        assert data["description"] == "Updated workflow description"
        assert len(data["blocks"]) == 1
        assert data["blocks"][0]["config"]["text"] == "Updated text"

    @pytest.mark.asyncio
    async def test_delete_workflow(self, test_client, auth_headers):
        """测试删除工作流"""
        response = await test_client.delete(
            f"/backend-api/api/workflow/{TEST_GROUP_ID}/{TEST_WORKFLOW_ID}",
            headers=auth_headers,
        )

        data = await response.get_json()
        assert "error" not in data
        assert "message" in data
        assert data["message"] == "Workflow deleted successfully"
