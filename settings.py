"""Lokale gebruikersvoorkeuren en veilige doelpaden voor aanwijzingen."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import tempfile


EXPORT_MODES = {
    "Word en PDF": "both",
    "Alleen Word": "docx",
    "Alleen PDF": "pdf",
}

# De bestaande mappenstructuur van Eqraft onder AANWIJZINGEN.
ROLE_FOLDERS = {
    "IV": "01 - IV",
    "WV": "02 - WV",
    "VP": "03 - VP",
    "VOP": "04 - VOP",
    "LEEK": "05 - Leek",
    "ZZP": "06 - ZZP",
}


@dataclass
class AppSettings:
    output_root: str = ""
    export_mode: str = "both"


def settings_path() -> Path:
    override = os.environ.get("EQRAFT_SETTINGS_PATH")
    if override:
        return Path(override)
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share")
    return base / "Eqraft" / "NEN3140_Aanwijzingen" / "instellingen.json"


def load_settings(path: Path | None = None) -> AppSettings:
    file = path or settings_path()
    if not file.is_file():
        return AppSettings()
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
        mode = data.get("export_mode", "both")
        root = data.get("output_root", "")
        if data.get("version") != 1 or mode not in EXPORT_MODES.values() or not isinstance(root, str):
            raise ValueError("onbekende instellingen")
        return AppSettings(root, mode)
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        raise ValueError(f"Instellingen konden niet worden gelezen ({file}): {exc}") from exc


def save_settings(settings: AppSettings, path: Path | None = None) -> None:
    file = path or settings_path()
    if settings.export_mode not in EXPORT_MODES.values():
        raise ValueError("Ongeldige bestandskeuze.")
    file.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json",
                                         dir=file.parent, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump({"version": 1, "output_root": settings.output_root,
                       "export_mode": settings.export_mode}, handle, ensure_ascii=False, indent=2)
        temporary.replace(file)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def safe_component(text: str) -> str:
    component = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text).strip(" .")[:130].rstrip(" .")
    if not component or component.upper().split(".")[0] in {
        "CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }:
        raise ValueError("Vul een geldige volledige naam voor de persoonsmap in.")
    return component


def output_paths(root: str | Path, role: str, person: str, date: str,
                 registration: bool = False) -> tuple[Path, Path]:
    """Gebruik AANWIJZINGEN / bestaande rolmap / persoonsnaam, zonder map aan te maken."""
    if role not in ROLE_FOLDERS:
        raise ValueError(f"Onbekend aanwijzingstype: {role}.")
    folder = Path(root).expanduser() / ROLE_FOLDERS[role] / safe_component(person)
    prefix = "Registratie" if registration else "Aanwijzing"
    stem = f"{prefix} {role} - {safe_component(person)} - {date}"
    return folder / f"{stem}.docx", folder / f"{stem}.pdf"
