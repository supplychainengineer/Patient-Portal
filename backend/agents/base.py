"""The agent runtime: a Claude tool-use loop with full step logging.

Each agent is an AgentSpec (system prompt + tool belt). run_agent() drives the
conversation: Claude decides which tools to call, this loop executes them,
logs every step to the `agent_runs` collection (visible in the UI), and
returns Claude's final summary.
"""
import json
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import anthropic

import config
from agents import tools as T
from database import db


@dataclass
class AgentSpec:
    key: str
    name: str
    description: str
    system_prompt: str
    tools: list = field(default_factory=list)
    # UI hint: fields the frontend renders when triggering this agent manually
    input_fields: list = field(default_factory=list)


class AgentNotConfiguredError(Exception):
    pass


def _log_step(run_id: str, step: dict):
    step["at"] = datetime.now(timezone.utc).isoformat()
    db.agent_runs.update_one({"id": run_id}, {"$push": {"steps": step}})


def _tool_result_content(result) -> str:
    try:
        return json.dumps(result, default=str)
    except TypeError:
        return str(result)


def run_agent(spec: AgentSpec, task: str, payload: dict | None = None,
              triggered_by: str = "manual") -> dict:
    """Execute one agent run synchronously and return the run record."""
    if not config.ANTHROPIC_API_KEY:
        raise AgentNotConfiguredError(
            "Agents are not active yet: set ANTHROPIC_API_KEY in backend/.env "
            "(see the Settings page).")

    run_id = str(uuid.uuid4())
    started = datetime.now(timezone.utc).isoformat()
    db.agent_runs.insert_one({
        "id": run_id, "agent_key": spec.key, "agent_name": spec.name,
        "task": task, "payload": payload or {}, "triggered_by": triggered_by,
        "status": "running", "steps": [], "started_at": started,
    })

    ctx = {"run_id": run_id, "agent_key": spec.key}
    tool_map = {t["name"]: t["fn"] for t in spec.tools}
    tool_schemas = [T.serialize(t) for t in spec.tools]

    user_message = task
    if payload:
        user_message += "\n\nInput data:\n" + json.dumps(payload, indent=2, default=str)

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    messages = [{"role": "user", "content": user_message}]
    system = spec.system_prompt + "\n\n" + T.clinic_context()
    final_text = ""

    try:
        for _ in range(config.AGENT_MAX_ITERATIONS):
            response = client.messages.create(
                model=config.AGENT_MODEL,
                max_tokens=config.AGENT_MAX_TOKENS,
                thinking={"type": "adaptive"},
                system=system,
                tools=tool_schemas,
                messages=messages,
            )

            if response.stop_reason == "pause_turn":
                messages.append({"role": "assistant", "content": response.content})
                continue

            text_blocks = [b.text for b in response.content if b.type == "text"]
            if text_blocks:
                final_text = "\n".join(text_blocks)

            if response.stop_reason != "tool_use":
                break

            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                fn = tool_map.get(block.name)
                try:
                    if fn is None:
                        raise KeyError(f"Unknown tool: {block.name}")
                    result = fn(ctx, **block.input)
                    is_error = isinstance(result, dict) and "error" in result
                except Exception as exc:  # tool crashed — let Claude adapt
                    result = {"error": f"{type(exc).__name__}: {exc}"}
                    is_error = True
                _log_step(run_id, {"tool": block.name, "input": block.input,
                                   "result": result, "is_error": is_error})
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": _tool_result_content(result),
                    "is_error": is_error,
                })
            messages.append({"role": "user", "content": tool_results})
        else:
            final_text = final_text or "Stopped: reached the maximum number of agent iterations."

        status = "completed"
    except anthropic.AuthenticationError:
        status, final_text = "failed", ("Anthropic rejected the API key. Check "
                                        "ANTHROPIC_API_KEY in backend/.env.")
    except anthropic.APIError as exc:
        status, final_text = "failed", f"Anthropic API error: {exc}"
    except Exception:
        status, final_text = "failed", f"Unexpected error:\n{traceback.format_exc()}"

    db.agent_runs.update_one({"id": run_id}, {"$set": {
        "status": status, "summary": final_text,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }})
    return db.agent_runs.find_one({"id": run_id}, {"_id": 0})
