# -*- coding: utf-8 -*-
"""User state management for conversation flow"""

from enum import Enum, auto
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

class State(Enum):
    """User states"""
    IDLE = auto()
    WAITING_PHONE = auto()
    WAITING_CODE = auto()
    WAITING_2FA_PASSWORD = auto()
    WAITING_GROUP_LINK = auto()
    WAITING_GROUP_DELETE = auto()
    WAITING_KEYWORD = auto()
    WAITING_KEYWORD_DELETE = auto()
    WAITING_BLACKLIST = auto()
    WAITING_BLACKLIST_DELETE = auto()
    WAITING_DESTINATION_GROUP = auto()
    WAITING_ADMIN_ADD = auto()
    WAITING_ADMIN_DELETE = auto()
    WAITING_PAUSE_DURATION = auto()
    WAITING_MESSAGE_FORMAT = auto()

@dataclass
class UserState:
    """User state data"""
    state: State = State.IDLE
    data: Dict[str, Any] = field(default_factory=dict)
    last_message_id: Optional[int] = None

class StateManager:
    """Manage user states"""

    def __init__(self):
        self._states: Dict[int, UserState] = {}

    def get_state(self, user_id: int) -> UserState:
        if user_id not in self._states:
            self._states[user_id] = UserState()
        return self._states[user_id]

    def set_state(self, user_id: int, state: State, data: Dict[str, Any] = None):
        if data is None:
            existing = self.get_state(user_id)
            self._states[user_id] = UserState(state=state, data=existing.data)
        else:
            self._states[user_id] = UserState(state=state, data=data)

    def clear_state(self, user_id: int):
        if user_id in self._states:
            self._states[user_id] = UserState()

    def set_data(self, user_id: int, key: str, value: Any):
        state = self.get_state(user_id)
        state.data[key] = value

    def get_data(self, user_id: int, key: str, default: Any = None) -> Any:
        state = self.get_state(user_id)
        return state.data.get(key, default)
