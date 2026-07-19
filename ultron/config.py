"""Configuration loader for ATLAS.

Reads the base64-encoded JSON configuration file (``ultron_config.json``)
and returns its contents as a plain Python dictionary.  The encoding keeps
credentials and model paths out of plain-text version control while still
being easily editable via a one-liner re-encode command.
"""

import base64
import json
from pathlib import Path
from typing import Any, Dict

CONFIG_PATH = Path(__file__).resolve().parent.parent / 'ultron_config.json'

def load_config(path: Path = CONFIG_PATH) -> Dict[str, Any]:
    """Load and decode the encrypted JSON configuration.

    The configuration file is expected to contain base64 encoded JSON. This
    function reads the file, decodes it and returns the resulting dictionary.
    """
    data = path.read_text().strip()
    if not data:
        return {}
    decoded = base64.b64decode(data)
    return json.loads(decoded)
