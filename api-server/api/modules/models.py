from dataclasses import dataclass
from typing import Callable


@dataclass
class TurboTool:
    name: str
    config: dict
    function: Callable
