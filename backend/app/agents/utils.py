from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)


_JSON_RE = re.compile(r"\{[\s\S]*\}\s*$")


def parse_json_model(text: str, model: type[T]) -> T:
    """
    Best-effort extraction of a single JSON object from model output.
    """
    s = (text or "").strip()
    m = _JSON_RE.search(s)
    if m:
        s = m.group(0)
    data = json.loads(s)
    return model.model_validate(data)

