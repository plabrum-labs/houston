from app.domain.apps.enums import AppState
from app.domain.apps.models import App
from app.domain.users.roles import Role
from app.platform.state_machine.machine import State, StateMachine, Transition


class Registered(State[AppState, App, Role]):
    value = AppState.registered
    transitions = [Transition(to=AppState.provisioning, roles={Role.STAFF})]


class Provisioning(State[AppState, App, Role]):
    value = AppState.provisioning
    transitions = [
        Transition(to=AppState.live, roles={Role.STAFF}),
        Transition(to=AppState.suspended, system_only=True),  # e.g. auto-suspend job
    ]


class Live(State[AppState, App, Role]):
    value = AppState.live
    transitions = [Transition(to=AppState.suspended, roles={Role.STAFF})]


class Suspended(State[AppState, App, Role]):
    value = AppState.suspended
    transitions = [Transition(to=AppState.live, roles={Role.STAFF})]


app_machine = StateMachine(
    enum_type=AppState,
    states={
        AppState.registered: Registered,
        AppState.provisioning: Provisioning,
        AppState.live: Live,
        AppState.suspended: Suspended,
    },
)
