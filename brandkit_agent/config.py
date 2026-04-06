from pathlib import Path
import yaml

_config_path = Path(__file__).parent / "config.yaml"

with open(_config_path) as f:
    _cfg = yaml.safe_load(f)

AGENT_MODEL: str = _cfg["agent"]["model"]
IMAGE_MODEL: str = _cfg["image_generation"]["model"]
