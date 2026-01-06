from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    id: int
    email: str

@dataclass
class Bar:
    id: int
    user_id: int
    name: str
    city: Optional[str] = None
    state: Optional[str] = None

@dataclass
class Upload:
    id: int
    bar_id: int
    created_at: str
    label: str

@dataclass
class Report:
    id: int
    bar_id: int
    created_at: str
    label: str
    report_json: str

