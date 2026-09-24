"""Codelijsten uit het meegeleverde aanwijzingsmodel en eigen aanvullingen.

De Word-bron bevat de betekenis en de voorwaarden. Deze module verleent geen
bevoegdheid: die wordt per persoon en per combinatie vastgesteld.
"""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import tempfile

from docx import Document

from config import resource_path


CATEGORIES = {
    "L": (2, "Mechanische taken (Leek)"),
    "S": (3, "Vaardigheden en werkzaamheden"),
    "M": (4, "Machines en installaties"),
    "P": (5, "Procedures"),
    "R": (6, "Aanvullende bevoegdheden"),
}
CODE_PATTERN = re.compile(r"^[LSMPR]\d{2,4}[A-Z]?$")
MODEL_NAME = "documents/Aanwijzingsmodel.docx"


@dataclass(frozen=True)
class CatalogItem:
    code: str
    name: str
    explanation: str
    custom: bool = False
    selectable: bool = True

    @property
    def category(self) -> str:
        return self.code[0]

    @property
    def line(self) -> str:
        return f"{self.code} – {self.name}"


def user_catalog_path() -> Path:
    """Eén gedeelde lijst voor deze Windows-gebruiker, ook bij een onefile-exe."""
    override = os.environ.get("EQRAFT_CATALOG_PATH")
    if override:
        return Path(override)
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share")
    return base / "Eqraft" / "NEN3140_Aanwijzingen" / "catalogus.json"


class CatalogStore:
    def __init__(self, model_path: Path | None = None, custom_path: Path | None = None):
        self.model_path = model_path or resource_path(MODEL_NAME)
        self.custom_path = custom_path or user_catalog_path()
        if not self.model_path.is_file():
            raise FileNotFoundError(f"Aanwijzingsmodel ontbreekt: {self.model_path}")
        self.builtin = self._read_model()
        self.custom = self._read_custom()

    def _read_model(self) -> dict[str, CatalogItem]:
        tables = Document(self.model_path).tables
        if len(tables) < 7:
            raise ValueError("Het aanwijzingsmodel bevat niet alle codelijsten (L, S, M, P, R).")
        result = {}
        for category, (table_index, _) in CATEGORIES.items():
            for row in tables[table_index].rows[1:]:
                code, name, explanation = (
                    re.sub(r"\s+", " ", cell.text).strip() for cell in row.cells[:3]
                )
                if not CODE_PATTERN.fullmatch(code) or not code.startswith(category):
                    continue
                # M04 en M06 hebben in het aangeleverde model geen benaming;
                # neem die letterlijk over uit hun eigen omschrijving.
                if not name and code in ("M04", "M06"):
                    name = re.sub(r"^Werkzaamheden aan ", "", explanation).rstrip(".")
                    name = name[0].upper() + name[1:]
                if not name:
                    raise ValueError(f"Geen benaming gevonden in het aanwijzingsmodel bij {code}.")
                if not explanation:
                    explanation = "Geen nadere toelichting in het aanwijzingsmodel; specificeer het object en de grenzen."
                result[code] = CatalogItem(
                    code, name, explanation,
                    selectable=(code != "S01"),
                )
        return result

    def _read_custom(self) -> dict[str, CatalogItem]:
        if not self.custom_path.exists():
            return {}
        try:
            contents = json.loads(self.custom_path.read_text(encoding="utf-8"))
            if contents.get("version") != 1 or not isinstance(contents.get("items"), list):
                raise ValueError("onbekende bestandsindeling")
            custom = {}
            for row in contents["items"]:
                code = row["code"].strip().upper()
                name = row["name"].strip()
                explanation = row["explanation"].strip()
                self._validate(code, name, explanation)
                if code in self.builtin or code in custom:
                    raise ValueError(f"dubbele code {code}")
                custom[code] = CatalogItem(code, name, explanation, custom=True)
            return custom
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ValueError(f"Eigen codelijst kan niet worden gelezen: {exc}") from exc

    @staticmethod
    def _validate(code: str, name: str, explanation: str) -> None:
        if not CODE_PATTERN.fullmatch(code):
            raise ValueError("Gebruik een code uit de gekozen rubriek, bijvoorbeeld M12 of S24A.")
        if not 1 <= len(name) <= 150 or not 1 <= len(explanation) <= 1000:
            raise ValueError("Vul een naam (max. 150 tekens) en uitleg (max. 1000 tekens) in.")

    def items(self, categories: tuple[str, ...]) -> list[CatalogItem]:
        all_items = {**self.builtin, **self.custom}
        return [item for item in all_items.values() if item.category in categories]

    def get(self, code: str) -> CatalogItem | None:
        return self.custom.get(code) or self.builtin.get(code)

    def put(self, code: str, name: str, explanation: str, old_code: str | None = None) -> None:
        code, name, explanation = code.strip().upper(), name.strip(), explanation.strip()
        self._validate(code, name, explanation)
        if old_code is not None and old_code not in self.custom:
            raise ValueError("Alleen eigen aanvullingen kunnen worden gewijzigd.")
        if code in self.builtin or (code in self.custom and code != old_code):
            raise ValueError(f"Code {code} bestaat al. Kies een nieuwe code.")
        next_items = dict(self.custom)
        if old_code:
            del next_items[old_code]
        next_items[code] = CatalogItem(code, name, explanation, custom=True)
        self._save(next_items)
        self.custom = next_items

    def delete(self, code: str) -> None:
        if code not in self.custom:
            raise ValueError("Alleen eigen aanvullingen kunnen worden verwijderd.")
        next_items = dict(self.custom)
        del next_items[code]
        self._save(next_items)
        self.custom = next_items

    def _save(self, entries: dict[str, CatalogItem]) -> None:
        self.custom_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "items": [
            {"code": item.code, "name": item.name, "explanation": item.explanation}
            for item in entries.values()
        ]}
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", prefix="catalogus_", suffix=".json",
                dir=self.custom_path.parent, delete=False,
            ) as handle:
                temporary = Path(handle.name)
                json.dump(payload, handle, ensure_ascii=False, indent=2)
            temporary.replace(self.custom_path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def merge_selected_lines(text: str, previous: list[str], current: list[str]) -> str:
    """Vervang alleen onaangepaste regels die de keuzehulp zelf heeft ingevoegd."""
    previous_set = set(previous)
    lines = [line for line in text.splitlines() if line.strip() not in previous_set]
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines + current)
