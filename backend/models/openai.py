import json
import os


DELIBERATION_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["ACT", "WAIT"]},
        "reason": {"type": "string"},
        "intent": {"type": ["string", "null"]},
        "next_wakeup_minutes": {"type": "integer", "minimum": 1},
    },
    "required": ["decision", "reason", "intent", "next_wakeup_minutes"],
    "additionalProperties": False,
}


class OpenAIStructuredModel:
    """OpenAI Responses API adapter behind the provider-neutral model protocol."""

    def __init__(self, client=None, model: str = "gpt-5.4-mini"):
        if client is None:
            from openai import OpenAI
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.client = client
        self.model = model

    def generate_json(self, *, system: str, payload: dict, schema: dict | None = None, schema_name: str = "deliberation_result") -> dict:
        response = self.client.responses.create(
            model=self.model,
            instructions=system,
            input=json.dumps(payload, ensure_ascii=False),
            reasoning={"effort": "low"},
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": schema or DELIBERATION_SCHEMA,
                }
            },
            store=False,
        )
        return json.loads(response.output_text)
