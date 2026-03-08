"""
Harbor-compatible external agent that uses Anthropic Claude to solve tasks.

Implements the BaseAgent interface. Claude receives the task instruction and
a bash tool, then iterates: think → bash command → observe output → repeat.
"""

import json
import os
import logging
from datetime import datetime, timezone
from pathlib import Path

from anthropic import Anthropic
from harbor.agents.base import BaseAgent, AgentContext
from harbor.environments.base import BaseEnvironment

AGENT_VERSION = "0.4.0"
MAX_TURNS = 15
COMMAND_TIMEOUT_SEC = 60

SYSTEM_PROMPT = """\
You are an expert autonomous agent running inside a Linux container.
You solve tasks by executing bash commands. You have access to a single tool
called "bash" that runs shell commands in the container.

Rules:
- Act immediately. Do NOT plan extensively before writing code.
- Write a SINGLE complete script on your FIRST tool call, then run it.
- Always use `python3` (not `python`) for all Python commands.
- You have a strict time limit. Every turn without a tool call is wasted.
- If a command fails, fix and retry quickly — do not re-analyze from scratch.
- When you are done, stop calling tools and respond with a short summary.
- Do NOT ask the user for input. You are fully autonomous.
"""


def load_skills() -> str:
    """Load all SKILL.md files from the agent/skills directory."""
    skills_dir = Path(__file__).parent / "skills"
    if not skills_dir.exists():
        return ""

    skill_texts = []
    for skill_file in sorted(skills_dir.rglob("SKILL.md")):
        content = skill_file.read_text().strip()
        # Strip YAML frontmatter for injection into prompt
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                content = content[end + 3:].strip()
        skill_texts.append(content)

    if not skill_texts:
        return ""

    return "\n\n<skills>\n" + "\n\n---\n\n".join(skill_texts) + "\n</skills>"

BASH_TOOL = {
    "name": "bash",
    "description": (
        "Execute a bash command in the container environment. "
        "Returns stdout, stderr, and the exit code."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The bash command to execute.",
            }
        },
        "required": ["command"],
    },
}



class ClaudeAgent(BaseAgent):
    """External Harbor agent powered by Anthropic Claude."""

    @staticmethod
    def name() -> str:
        return "claude-llm-agent"

    def version(self) -> str | None:
        return AGENT_VERSION

    async def setup(self, environment: BaseEnvironment) -> None:
        """No special setup needed — Claude runs externally via API."""
        self.logger.info("ClaudeAgent setup complete (no container-side install needed)")

    def _serialize_content_block(self, block) -> dict:
        """Convert an Anthropic content block to a JSON-serializable dict."""
        # Handle tool_use explicitly: model_dump() can return input:{} on some SDK versions
        if getattr(block, "type", None) == "tool_use":
            return {
                "type": "tool_use",
                "id": getattr(block, "id", None),
                "name": getattr(block, "name", None),
                "input": dict(getattr(block, "input", None) or {}),
            }
        if hasattr(block, "model_dump"):
            return block.model_dump()
        if hasattr(block, "text"):
            return {"type": "text", "text": block.text}
        return {"type": "unknown", "repr": repr(block)}

    def _serialize_messages(self, messages: list) -> list:
        """Convert the full messages list to JSON-serializable form."""
        serialized = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if isinstance(content, str):
                serialized.append({"role": role, "content": content})
            elif isinstance(content, list):
                serialized.append({
                    "role": role,
                    "content": [
                        self._serialize_content_block(b) if hasattr(b, "type") and not isinstance(b, dict) else b
                        for b in content
                    ],
                })
            else:
                serialized.append({"role": role, "content": str(content)})
        return serialized

    def _write_conversation_log(self, log_path: Path, turn: int, messages: list,
                                 response_content: list, usage: dict,
                                 tool_outputs: list | None = None) -> None:
        """Append a turn entry to the JSONL conversation log."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "turn": turn,
            "usage": usage,
            "response": [self._serialize_content_block(b) for b in response_content],
        }
        if tool_outputs is not None:
            entry["tool_outputs"] = tool_outputs

        try:
            with open(log_path, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            self.logger.warning(f"Failed to write conversation log: {e}")

    def _write_full_conversation(self, log_dir: Path, messages: list, system: str,
                                  model: str, total_input_tokens: int,
                                  total_output_tokens: int) -> None:
        """Write the complete conversation state to a JSON file (overwritten each turn)."""
        snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "system_prompt": system,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "messages": self._serialize_messages(messages),
        }
        try:
            snapshot_path = log_dir / "conversation.json"
            with open(snapshot_path, "w") as f:
                json.dump(snapshot, f, indent=2, default=str)
        except Exception as e:
            self.logger.warning(f"Failed to write conversation snapshot: {e}")

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not set. Export it or add it to .env.local"
            )

        model = self.model_name or "claude-sonnet-4-20250514"
        if "/" in model:
            # Harbor passes "anthropic/claude-sonnet-4-20250514" — strip the provider prefix
            model = model.split("/", 1)[1]

        client = Anthropic(api_key=api_key)

        # Inject loaded skills into the system prompt
        skill_content = load_skills()
        system = SYSTEM_PROMPT + skill_content

        # Set up conversation log directory using Harbor's logs_dir (the agent/ subdir within the trial)
        log_dir = self.logs_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        turn_log_path = log_dir / "conversation_turns.jsonl"

        messages = [{"role": "user", "content": instruction}]
        total_input_tokens = 0
        total_output_tokens = 0

        for turn in range(MAX_TURNS):
            self.logger.info(f"Turn {turn + 1}/{MAX_TURNS}")

            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=system,
                tools=[BASH_TOOL],
                messages=messages,
            )

            total_input_tokens += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens

            # Update context incrementally so data is preserved on timeout
            context.n_input_tokens = total_input_tokens
            context.n_output_tokens = total_output_tokens

            # Log assistant reasoning (text blocks) — full text, no truncation
            for block in response.content:
                if hasattr(block, "text") and block.text:
                    self.logger.info(f"[assistant] {block.text}")

            # Check if the model wants to use tools
            tool_use_blocks = [
                b for b in response.content if b.type == "tool_use"
            ]

            if response.stop_reason == "end_turn" or not tool_use_blocks:
                # Model is done — extract final text
                final_text = "".join(
                    b.text for b in response.content if hasattr(b, "text")
                )
                self.logger.info(f"Agent finished: {final_text}")

                # Log final turn
                self._write_conversation_log(
                    turn_log_path, turn + 1, messages, response.content,
                    {"input_tokens": response.usage.input_tokens,
                     "output_tokens": response.usage.output_tokens},
                )
                self._write_full_conversation(
                    log_dir, messages, system, model,
                    total_input_tokens, total_output_tokens,
                )
                break

            # Append assistant message (contains tool_use blocks)
            messages.append({"role": "assistant", "content": response.content})

            # Execute each tool call and collect results
            tool_results = []
            tool_outputs_for_log = []
            for block in tool_use_blocks:
                cmd = block.input.get("command", "")
                self.logger.info(f"Executing: {cmd}")

                result = await environment.exec(
                    command=cmd,
                    timeout_sec=COMMAND_TIMEOUT_SEC,
                )

                output = ""
                if result.stdout:
                    output += result.stdout
                if result.stderr:
                    output += f"\n[stderr]\n{result.stderr}"
                output += f"\n[exit_code: {result.return_code}]"

                # Log command output (truncated for the text log, full in JSON)
                output_preview = output[:1000] if len(output) > 1000 else output
                self.logger.info(f"Output: {output_preview}")

                tool_outputs_for_log.append({
                    "tool_use_id": block.id,
                    "command": cmd,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.return_code,
                })

                # Truncate very long outputs to stay within context limits
                if len(output) > 15000:
                    output = output[:7000] + "\n...[truncated]...\n" + output[-7000:]

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output,
                    }
                )

            messages.append({"role": "user", "content": tool_results})

            # Write turn to conversation logs
            self._write_conversation_log(
                turn_log_path, turn + 1, messages, response.content,
                {"input_tokens": response.usage.input_tokens,
                 "output_tokens": response.usage.output_tokens},
                tool_outputs=tool_outputs_for_log,
            )
            self._write_full_conversation(
                log_dir, messages, system, model,
                total_input_tokens, total_output_tokens,
            )
        else:
            self.logger.warning(f"Agent hit max turns ({MAX_TURNS})")
            # Still save conversation on max turns
            self._write_full_conversation(
                log_dir, messages, system, model,
                total_input_tokens, total_output_tokens,
            )

