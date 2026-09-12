"""Config loader."""
import yaml
from pathlib import Path


class Config:
    def __init__(self, path="config.yaml"):
        self.path = Path(path)
        with open(self.path) as f:
            self._cfg = yaml.safe_load(f)

    def get(self, key, default=None):
        cur = self._cfg
        for k in key.split("."):
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                return default
        return cur

    @property
    def raw(self):
        return self._cfg