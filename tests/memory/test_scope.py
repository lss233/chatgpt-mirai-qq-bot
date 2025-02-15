import pytest
from framework.memory.scopes import MemberScope, GroupScope, GlobalScope
from framework.im.sender import ChatSender

# ==================== 常量区 ====================
TEST_USER_1 = "user1"
TEST_USER_2 = "user2"
TEST_GROUP_1 = "group1"
TEST_GROUP_2 = "group2"
TEST_DISPLAY_NAME = "john"

# ==================== Fixtures ====================
@pytest.fixture
def group_sender():
    return ChatSender.from_group_chat(
        user_id=TEST_USER_1,
        group_id=TEST_GROUP_1,
        display_name=TEST_DISPLAY_NAME
    )

@pytest.fixture
def c2c_sender():
    return ChatSender.from_c2c_chat(
        user_id=TEST_USER_1,
        display_name=TEST_DISPLAY_NAME
    )

@pytest.fixture
def different_group_sender():
    return ChatSender.from_group_chat(
        user_id=TEST_USER_1,
        group_id=TEST_GROUP_2,
        display_name=TEST_DISPLAY_NAME
    )

@pytest.fixture
def different_user_sender():
    return ChatSender.from_group_chat(
        user_id=TEST_USER_2,
        group_id=TEST_GROUP_1,
        display_name=TEST_DISPLAY_NAME
    )

# ==================== 测试逻辑 ====================
class TestMemberScope:
    @pytest.fixture
    def scope(self):
        return MemberScope()
        
    def test_get_scope_key_group(self, scope, group_sender):
        key = scope.get_scope_key(group_sender)
        assert key == f"member:{TEST_GROUP_1}:{TEST_USER_1}"
        
    def test_get_scope_key_c2c(self, scope, c2c_sender):
        key = scope.get_scope_key(c2c_sender)
        assert key == f"c2c:{TEST_USER_1}"
        
    def test_is_in_scope_group_same_user(self, scope, group_sender):
        same_sender = ChatSender.from_group_chat(TEST_USER_1, TEST_GROUP_1, TEST_DISPLAY_NAME)
        assert scope.is_in_scope(group_sender, same_sender)
        
    def test_is_in_scope_group_different_user(self, scope, group_sender, different_user_sender):
        assert not scope.is_in_scope(group_sender, different_user_sender)
        
    def test_is_in_scope_group_different_group(self, scope, group_sender, different_group_sender):
        assert not scope.is_in_scope(group_sender, different_group_sender)
        
    def test_is_in_scope_c2c_same_user(self, scope, c2c_sender):
        same_sender = ChatSender.from_c2c_chat(TEST_USER_1, TEST_DISPLAY_NAME)
        assert scope.is_in_scope(c2c_sender, same_sender)
        
    def test_is_in_scope_c2c_different_user(self, scope, c2c_sender):
        different_sender = ChatSender.from_c2c_chat(TEST_USER_2, TEST_DISPLAY_NAME)
        assert not scope.is_in_scope(c2c_sender, different_sender)
        
    def test_is_in_scope_different_chat_type(self, scope, group_sender, c2c_sender):
        assert not scope.is_in_scope(group_sender, c2c_sender)


class TestGroupScope:
    @pytest.fixture
    def scope(self):
        return GroupScope()
        
    def test_get_scope_key_group(self, scope, group_sender):
        key = scope.get_scope_key(group_sender)
        assert key == f"group:{TEST_GROUP_1}"
        
    def test_get_scope_key_c2c(self, scope, c2c_sender):
        key = scope.get_scope_key(c2c_sender)
        assert key == f"c2c:{TEST_USER_1}"
        
    def test_is_in_scope_group_same_group(self, scope, group_sender, different_user_sender):
        assert scope.is_in_scope(group_sender, different_user_sender)
        
    def test_is_in_scope_group_different_group(self, scope, group_sender, different_group_sender):
        assert not scope.is_in_scope(group_sender, different_group_sender)
        
    def test_is_in_scope_c2c_same_user(self, scope, c2c_sender):
        same_sender = ChatSender.from_c2c_chat(TEST_USER_1, TEST_DISPLAY_NAME)
        assert scope.is_in_scope(c2c_sender, same_sender)
        
    def test_is_in_scope_c2c_different_user(self, scope, c2c_sender):
        different_sender = ChatSender.from_c2c_chat(TEST_USER_2, TEST_DISPLAY_NAME)
        assert not scope.is_in_scope(c2c_sender, different_sender)
        
    def test_is_in_scope_different_chat_type(self, scope, group_sender, c2c_sender):
        assert not scope.is_in_scope(group_sender, c2c_sender)


class TestGlobalScope:
    @pytest.fixture
    def scope(self):
        return GlobalScope()
        
    def test_get_scope_key(self, scope, group_sender, c2c_sender):
        assert scope.get_scope_key(group_sender) == "global"
        assert scope.get_scope_key(c2c_sender) == "global"
        
    def test_is_in_scope_always_true(self, scope, group_sender, c2c_sender):
        assert scope.is_in_scope(group_sender, c2c_sender)
        assert scope.is_in_scope(c2c_sender, group_sender) 