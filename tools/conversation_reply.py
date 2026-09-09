"""Small, inert reply contract for local clarification controls; no native tool claim."""
import json

SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["message", "questions"],
    "properties": {
        "message": {"type": "string", "maxLength": 2400},
        "questions": {"type": "array", "maxItems": 3, "items": {
            "type": "object", "additionalProperties": False,
            "required": ["question", "options"], "properties": {
                "question": {"type": "string", "maxLength": 240},
                "options": {"type": "array", "minItems": 2, "maxItems": 4,
                            "items": {"type": "string", "maxLength": 160}}
            }
        }}
    }
}

def decode(raw):
    def pairs(rows):
        value = {}
        for key, item in rows:
            if key in value: raise ValueError("duplicate reply key")
            value[key] = item
        return value
    value = json.loads(raw, object_pairs_hook=pairs)
    if not isinstance(value, dict) or set(value) != {"message", "questions"}:
        raise ValueError("invalid reply envelope")
    message, questions = value['message'], value['questions']
    if not isinstance(message, str) or not message.strip() or len(message) > 2400:
        raise ValueError("invalid reply message")
    if not isinstance(questions, list) or len(questions) > 3:
        raise ValueError("at most three clarification questions")
    for row in questions:
        if not isinstance(row, dict) or set(row) != {'question', 'options'}:
            raise ValueError("invalid clarification")
        q, options = row['question'], row['options']
        if not isinstance(q, str) or not q.strip() or len(q) > 240:
            raise ValueError("invalid question")
        if not isinstance(options, list) or not 2 <= len(options) <= 4:
            raise ValueError("invalid options")
        if any(not isinstance(o, str) or not o.strip() or len(o) > 160 for o in options):
            raise ValueError("invalid option label")
        if len(set(options)) != len(options): raise ValueError("duplicate options")
    return value

def transcript(value):
    """Keep actual visible options in both actors' history and private exports."""
    lines = [value['message']]
    for row in value['questions']:
        lines.extend([row['question'], ' / '.join(row['options'])])
    return '\n\n'.join(lines)
