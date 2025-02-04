import pytest
from framework.memory.scopes import MemberScope, GroupScope, GlobalScope
from framework.im.sender import ChatSender

@pytest.fixture
def group_sender():
    return ChatSender.from_group_chat(
        user_id="user1",
        group_id="group1"
    )

@pytest.fixture
def c2c_sender():
    return ChatSender.from_c2c_chat(
        user_id="user1"
    )

class TestMemberScope:
    @pytest.fixture
    def scope(self):
        return MemberScope()
        
    def test_get_scope_key_group(self, scope, group_sender):
        key = scope.get_scope_key(group_sender)
        assert key == "member:group1:user1"
        
    def test_get_scope_key_c2c(self, scope, c2c_sender):
        key = scope.get_scope_key(c2c_sender)
        assert key == "c2c:user1"
        
    def test_is_in_scope_group_same_user(self, scope):
        sender1 = ChatSender.from_group_chat("user1", "group1")
        sender2 = ChatSender.from_group_chat("user1", "group1")
        assert scope.is_in_scope(sender1, sender2)
        
    def test_is_in_scope_group_different_user(self, scope):
        sender1 = ChatSender.from_group_chat("user1", "group1")
        sender2 = ChatSender.from_group_chat("user2", "group1")
        assert not scope.is_in_scope(sender1, sender2)
        
    def test_is_in_scope_group_different_group(self, scope):
        sender1 = ChatSender.from_group_chat("user1", "group1")
        sender2 = ChatSender.from_group_chat("user1", "group2")
        assert not scope.is_in_scope(sender1, sender2)
        
    def test_is_in_scope_c2c_same_user(self, scope):
        sender1 = ChatSender.from_c2c_chat("user1")
        sender2 = ChatSender.from_c2c_chat("user1")
        assert scope.is_in_scope(sender1, sender2)
        
    def test_is_in_scope_c2c_different_user(self, scope):
        sender1 = ChatSender.from_c2c_chat("user1")
        sender2 = ChatSender.from_c2c_chat("user2")
        assert not scope.is_in_scope(sender1, sender2)
        
    def test_is_in_scope_different_chat_type(self, scope):
        sender1 = ChatSender.from_group_chat("user1", "group1")
        sender2 = ChatSender.from_c2c_chat("user1")
        assert not scope.is_in_scope(sender1, sender2)

class TestGroupScope:
    @pytest.fixture
    def scope(self):
        return GroupScope()
        
    def test_get_scope_key_group(self, scope, group_sender):
        key = scope.get_scope_key(group_sender)
        assert key == "group:group1"
        
    def test_get_scope_key_c2c(self, scope, c2c_sender):
        key = scope.get_scope_key(c2c_sender)
        assert key == "c2c:user1"
        
    def test_is_in_scope_group_same_group(self, scope):
        sender1 = ChatSender.from_group_chat("user1", "group1")
        sender2 = ChatSender.from_group_chat("user2", "group1")
        assert scope.is_in_scope(sender1, sender2)
        
    def test_is_in_scope_group_different_group(self, scope):
        sender1 = ChatSender.from_group_chat("user1", "group1")
        sender2 = ChatSender.from_group_chat("user1", "group2")
        assert not scope.is_in_scope(sender1, sender2)
        
    def test_is_in_scope_c2c_same_user(self, scope):
        sender1 = ChatSender.from_c2c_chat("user1")
        sender2 = ChatSender.from_c2c_chat("user1")
        assert scope.is_in_scope(sender1, sender2)
        
    def test_is_in_scope_c2c_different_user(self, scope):
        sender1 = ChatSender.from_c2c_chat("user1")
        sender2 = ChatSender.from_c2c_chat("user2")
        assert not scope.is_in_scope(sender1, sender2)
        
    def test_is_in_scope_different_chat_type(self, scope):
        sender1 = ChatSender.from_group_chat("user1", "group1")
        sender2 = ChatSender.from_c2c_chat("user1")
        assert not scope.is_in_scope(sender1, sender2)

class TestGlobalScope:
    @pytest.fixture
    def scope(self):
        return GlobalScope()
        
    def test_get_scope_key(self, scope, group_sender, c2c_sender):
        assert scope.get_scope_key(group_sender) == "global"
        assert scope.get_scope_key(c2c_sender) == "global"
        
    def test_is_in_scope_always_true(self, scope):
        sender1 = ChatSender.from_group_chat("user1", "group1")
        sender2 = ChatSender.from_c2c_chat("user2")
        assert scope.is_in_scope(sender1, sender2)
        assert scope.is_in_scope(sender2, sender1) 