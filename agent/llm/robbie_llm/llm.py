"""
Robbie's LLM: the persona prompt plus a llama.cpp server, replying in RELM.

This is a spike. It talks to llama-server's OpenAI style chat endpoint, and can
constrain the reply with a GBNF grammar made by scripts/relm_grammar.py.
"""
import json
import urllib.request
from dataclasses import dataclass, field

from relm.table import Table


def system_prompt(persona_path: str, table: Table) -> str:
    """The persona prompt, with the RELM tag lists filled in from the table."""
    with open(persona_path, encoding="utf-8") as f:
        text = f.read()
    instants = [f"<{m.name}/>" for m in table.macros.values() if m.instant]
    spans = [m.name for m in table.macros.values() if not m.instant]
    return (text.replace("{{RELM_INSTANT_TAGS}}", " ".join(instants))
                .replace("{{RELM_SPAN_TAGS}}", " ".join(spans)))


@dataclass
class RobbieLLM:
    url: str                    # llama-server, e.g. http://127.0.0.1:8200
    system: str                 # the system prompt
    grammar: str = None         # GBNF; None means unconstrained
    temperature: float = 0.8
    max_tokens: int = 400
    history: list = field(default_factory=list)

    def reset(self):
        self.history.clear()

    def reply(self, user_text: str, constrained: bool = True):
        """Streams Robbie's reply (RELM) as text chunks, and adds the turn to the history."""
        self.history.append({"role": "user", "content": user_text})
        body = {
            "messages": [{"role": "system", "content": self.system}] + self.history,
            "stream": True,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            # Replies are spoken, so no thinking; it also clashes with the grammar.
            "chat_template_kwargs": {"enable_thinking": False},
        }
        if constrained and self.grammar:
            body["grammar"] = self.grammar
        request = urllib.request.Request(
            self.url.rstrip("/") + "/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        parts = []
        try:
            with urllib.request.urlopen(request) as response:
                for line in response:
                    line = line.decode("utf-8").strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    choices = json.loads(data).get("choices") or [{}]
                    chunk = (choices[0].get("delta") or {}).get("content")
                    if chunk:
                        parts.append(chunk)
                        yield chunk
        finally:
            self.history.append({"role": "assistant", "content": "".join(parts)})
