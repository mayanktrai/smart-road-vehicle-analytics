"""Configuration loading and lightweight validation."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict

import yaml


@dataclass
class Config:
    """Parsed configuration with convenient attribute access."""

    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str) -> "Config":
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        cfg = cls(raw=data)
        cfg._validate()
        return cfg

    def _validate(self) -> None:
        required = ["source", "detector", "counter"]
        missing = [k for k in required if k not in self.raw]
        if missing:
            raise ValueError(f"Missing required config keys: {', '.join(missing)}")

    # Generic getter with dotted keys, e.g. cfg.get("speed.speed_limit_kmph", 60)
    def get(self, dotted: str, default: Any = None) -> Any:
        node: Any = self.raw
        for part in dotted.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return default
        return node

    def __getitem__(self, key: str) -> Any:
        return self.raw[key]
