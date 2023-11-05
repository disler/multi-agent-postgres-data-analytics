from dataclasses import dataclass
from typing import List


@dataclass
class Chat:
    from_name: str
    to_name: str
    message: str


@dataclass
class ConversationResult:
    success: bool
    messages: List[Chat]
    cost: float
    tokens: int
    last_message_str: str
    error_message: str
