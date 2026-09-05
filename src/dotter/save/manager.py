"""Slot-based save manager with in-place deserialization and thumbnail support."""

import json
from dataclasses import dataclass
from pathlib import Path

from dotter.core.state import GameState
from dotter.save.serializer import deserialize_state, serialize_state


@dataclass(frozen=True, slots=True)
class SlotMetadata:
    """Header information for an existing save slot."""

    slot_id: str
    timestamp: str
    chapter_title: str
    playtime_seconds: float
    has_thumbnail: bool
    file_path: Path


class SaveManager:
    """Manages slot-based persistence, quick-save, auto-save, and metadata cataloging."""

    def __init__(self, save_dir: Path) -> None:
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def _get_paths(self, slot_id: str | int) -> tuple[Path, Path]:
        slot_str = str(slot_id)
        json_path = self.save_dir / f"slot_{slot_str}.json"
        thumb_path = self.save_dir / f"slot_{slot_str}.png"
        return json_path, thumb_path

    def save_slot(
        self,
        slot_id: str | int,
        state: GameState,
        thumbnail: bytes | None = None,
    ) -> Path:
        """Serialize state and write to slot file with optional companion thumbnail."""
        json_path, thumb_path = self._get_paths(slot_id)
        payload = serialize_state(state)

        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        if thumbnail is not None:
            thumb_path.write_bytes(thumbnail)

        return json_path

    def load_slot(self, slot_id: str | int, state: GameState) -> bool:
        """Restore state in-place from the specified save slot."""
        json_path, _ = self._get_paths(slot_id)
        if not json_path.exists():
            return False

        payload = json.loads(json_path.read_text(encoding="utf-8"))
        deserialize_state(payload, state)
        return True

    def quick_save(self, state: GameState, thumbnail: bytes | None = None) -> Path:
        """Save to dedicated 'quick' slot."""
        return self.save_slot("quick", state, thumbnail)

    def quick_load(self, state: GameState) -> bool:
        """Restore in-place from dedicated 'quick' slot."""
        return self.load_slot("quick", state)

    def auto_save(self, state: GameState, thumbnail: bytes | None = None) -> Path:
        """Save to dedicated 'auto' slot."""
        return self.save_slot("auto", state, thumbnail)

    def auto_load(self, state: GameState) -> bool:
        """Restore in-place from dedicated 'auto' slot."""
        return self.load_slot("auto", state)

    def delete_slot(self, slot_id: str | int) -> bool:
        """Delete save slot and its thumbnail if present."""
        json_path, thumb_path = self._get_paths(slot_id)
        deleted = False

        if json_path.exists():
            json_path.unlink()
            deleted = True

        if thumb_path.exists():
            thumb_path.unlink()

        return deleted

    def list_slots(self) -> list[SlotMetadata]:
        """Enumerate all available save slots sorted by slot identifier."""
        slots: list[SlotMetadata] = []

        for json_path in self.save_dir.glob("slot_*.json"):
            slot_id = json_path.stem.removeprefix("slot_")
            thumb_path = json_path.with_suffix(".png")

            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                slots.append(
                    SlotMetadata(
                        slot_id=slot_id,
                        timestamp=str(data.get("timestamp", "")),
                        chapter_title=str(data.get("chapter_title", "")),
                        playtime_seconds=float(data.get("playtime_seconds", 0.0)),
                        has_thumbnail=thumb_path.exists(),
                        file_path=json_path,
                    )
                )
            except (json.JSONDecodeError, OSError):
                continue

        return sorted(slots, key=lambda s: s.slot_id)
