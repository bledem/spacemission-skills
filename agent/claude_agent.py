"""
Harbor-compatible external agent that uses Anthropic Claude to solve tasks.

Implements the BaseAgent interface. Claude receives the task instruction and
a bash tool, then iterates: think → bash command → observe output → repeat.
"""

import os
import logging

from anthropic import Anthropic
from harbor.agents.base import BaseAgent, AgentContext
from harbor.environments.base import BaseEnvironment

AGENT_VERSION = "0.1.0"
MAX_TURNS = 30
COMMAND_TIMEOUT_SEC = 120

SYSTEM_PROMPT = """\
You are an expert autonomous agent running inside a Linux container.
You solve tasks by executing bash commands. You have access to a single tool
called "bash" that runs shell commands in the container.

Rules:
- Read the task instruction carefully before acting.
- Break complex problems into small steps.
- After each command, inspect the output before deciding the next step.
- If a command fails, diagnose the error and try a different approach.
- When you are done, stop calling tools and respond with a short summary.
- Do NOT ask the user for input. You are fully autonomous.
"""

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

        messages = [{"role": "user", "content": instruction}]
        total_input_tokens = 0
        total_output_tokens = 0

        for turn in range(MAX_TURNS):
            self.logger.info(f"Turn {turn + 1}/{MAX_TURNS}")

            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=[BASH_TOOL],
                messages=messages,
            )

            total_input_tokens += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens

            # Update context incrementally so data is preserved on timeout
            context.n_input_tokens = total_input_tokens
            context.n_output_tokens = total_output_tokens

            # Check if the model wants to use tools
            tool_use_blocks = [
                b for b in response.content if b.type == "tool_use"
            ]

            if response.stop_reason == "end_turn" or not tool_use_blocks:
                # Model is done — extract final text
                final_text = "".join(
                    b.text for b in response.content if hasattr(b, "text")
                )
                self.logger.info(f"Agent finished: {final_text[:200]}")
                break

            # Append assistant message (contains tool_use blocks)
            messages.append({"role": "assistant", "content": response.content})

            # Execute each tool call and collect results
            tool_results = []
            for block in tool_use_blocks:
                cmd = block.input.get("command", "")
                self.logger.info(f"Executing: {cmd[:120]}")

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
        else:
            self.logger.warning(f"Agent hit max turns ({MAX_TURNS})")
