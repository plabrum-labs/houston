from typing import Any

from app.platform.comms.enums import MessageState
from app.platform.comms.models.messages import Message
from app.platform.state_machine.machine import State, StateMachine, Transition


class ReceivedState(State[MessageState, Message, Any]):
    value = MessageState.RECEIVED
    transitions = []


class QueuedState(State[MessageState, Message, Any]):
    value = MessageState.QUEUED
    transitions = [
        Transition(to=MessageState.SENT, system_only=True),
        Transition(to=MessageState.FAILED, system_only=True),
    ]


class SentState(State[MessageState, Message, Any]):
    value = MessageState.SENT
    transitions = []


class FailedState(State[MessageState, Message, Any]):
    value = MessageState.FAILED
    transitions = [
        Transition(to=MessageState.QUEUED, system_only=True),
    ]


message_state_machine = StateMachine(
    enum_type=MessageState,
    states={
        MessageState.RECEIVED: ReceivedState,
        MessageState.QUEUED: QueuedState,
        MessageState.SENT: SentState,
        MessageState.FAILED: FailedState,
    },
)
