from dataclasses import dataclass


@dataclass(frozen=True)
class NewsSettings:
    """Editorial preferences that shape every generated Hindi article."""

    location: str = "Delhi"
    department: str = "General"
    language: str = "Hindi"

    def as_dict(self) -> dict[str, str]:
        return {
            "location": self.location.strip() or "Delhi",
            "department": self.department.strip() or "General",
            "language": "Hindi",
        }
