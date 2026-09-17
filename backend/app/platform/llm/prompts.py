"""System prompts for the platform's LLM surfaces.

The two LLM surfaces (text/SSE via Anthropic, voice/WS via OpenAI Realtime)
share a persona but have different formatting and turn-taking needs. We
model this as a base prompt + a modality overlay rather than a single
monolithic string, so neither surface drifts and neither pollutes the other
with rules that don't apply to it.

The persona/domain-vocabulary block comes from `Config.LLM_PERSONA` — the default
is generic, and a deployment overrides it with its own product and domain.

`build_system_prompt(modality, ...)` is the single entry point — both
`service.py` (text) and `routes.py` (voice) call it.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from app.platform.state_machine.roles import Actor

Modality = Literal["text", "voice"]


@dataclass(frozen=True, slots=True)
class PromptContext:
    user: Actor[Any] | None = None
    current_page: str | None = None


_BASE_TEMPLATE = """\
{persona}

How to be useful here:
- Prefer narrow, specific tools over freeform updates. If a tool exists for
  "create X" or "send X", use it; do not synthesise the same
  effect by editing fields directly.
- When the user asks for something ambiguous (which record? which item?),
  ask one clarifying question rather than guessing. Wrong actions are
  expensive to undo.
- When a tool errors, tell the user what failed in plain language. Do not
  retry the same call with the same arguments.
- Respect the user's role. If a tool says "not available for your role",
  surface that clearly rather than reinterpreting the request.

Default to English.
"""

_TEXT_OVERLAY = """\
Output guidance:
- Markdown is fine — lists, bold, inline code, code blocks.
- Be concise but complete. The user can scroll; trailing context is OK.
- When you call a tool, briefly say what you're doing in one short sentence
  before the call, not a paragraph.
"""

_VOICE_OVERLAY = """\
You are speaking out loud through a real-time voice interface. The user
hears you; they do not read you.

Speech rules:
- No markdown, no asterisks, no bullet points, no code blocks — these get
  read aloud verbatim and sound broken.
- Be terse. One or two short sentences per turn is the target. The user
  can ask for more if they want it.
- Do not preamble ("Sure! I'd be happy to help…"). Start with the answer
  or the action.
- Numbers and IDs: read them naturally ("item forty-two"), not digit by
  digit, unless the user reads them out that way.

Turn-taking:
- Do not speak first. Wait for the user. Do not greet, introduce yourself,
  or fill silence. Stay silent until the user says something.
- The user may pause mid-thought. If their turn ends but the request feels
  incomplete, ask one short clarifying question rather than guessing.

Ending the session:
- When the user signals the conversation is over ("thanks, bye", "that's
  all", "hang up", "we're done"), call the end_session tool and say a
  brief farewell in the same response. The session closes after your
  audio finishes.
- Do not call end_session on a pause, an unclear utterance, or a single
  word. It is a deliberate hang-up, not a fallback.
"""


def _context_block(ctx: PromptContext | None) -> str:
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    lines = [f"Today's date is {today} (UTC)."]
    if ctx and ctx.user is not None:
        # Role is the most important fact about the user for the model — it determines
        # which tools the executor will run. Surfacing it lets the model
        # avoid suggesting actions the user can't take.
        lines.append(f"The current user's role is: {ctx.user.role}.")
    if ctx and ctx.current_page:
        lines.append(f"The user is currently viewing: {ctx.current_page}.")
    return "\n".join(lines)


def build_system_prompt(modality: Modality, ctx: PromptContext | None = None, *, persona: str) -> str:
    overlay = _VOICE_OVERLAY if modality == "voice" else _TEXT_OVERLAY
    base = _BASE_TEMPLATE.format(persona=persona)
    return f"{base}\n{_context_block(ctx)}\n\n{overlay}"
