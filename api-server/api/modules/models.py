from dataclasses import dataclass, field
import time
from typing import Callable


@dataclass
class TurboTool:
    name: str
    config: dict
    function: Callable


@dataclass
class Chat:
    from_name: str
    to_name: str
    message: str
    created: int = field(default_factory=time.time)
