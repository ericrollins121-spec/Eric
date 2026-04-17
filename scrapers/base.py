from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Listing:
    source: str
    title: str
    url: str
    price: Optional[int]
    location: Optional[str]
    bedrooms: Optional[float]
    posted_at: Optional[str]
    image: Optional[str]
    description: Optional[str]

    def to_dict(self) -> dict:
        return asdict(self)
