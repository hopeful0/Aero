from pathlib import Path

_SKILL_FILE = Path(__file__).parent / "aero_skill.md"
SKILL_MD = _SKILL_FILE.read_text(encoding="utf-8")
