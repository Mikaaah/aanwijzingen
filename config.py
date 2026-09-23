"""Velden en sjablonen. De inhoud van de aanwijzing staat uitsluitend in Word."""

from pathlib import Path
import sys


APP_TITLE = "NEN 3140 Aanwijzingen"

# Voeg hier later WV, VP en VOP toe zodra de bijbehorende sjablonen bestaan.
TYPES = {
    "Installatieverantwoordelijke (IV)": {
        "code": "IV",
        "template": "Aanwijzing_IV.docx",
    },
}

SECTIONS = (
    ("Gegevens aangewezene", (
        ("Organisatie", "ORGANISATIE", True, False),
        ("Volledige naam", "VOLLEDIGE_NAAM", True, False),
        ("Functie", "FUNCTIE", True, False),
        ("Afdeling", "AFDELING", False, False),
        ("Ingangsdatum (dd-mm-jjjj)", "INGANGSDATUM", True, False),
        ("Geldig tot (dd-mm-jjjj)", "GELDIG_TOT", True, False),
    )),
    ("Omvang aanwijzing", (
        ("Locatie / gebouw", "LOCATIE", True, False),
        ("Installatie(s) / installatiedelen", "INSTALLATIES", True, True),
        ("Verantwoordelijkheidsgebied", "VERANTWOORDELIJKHEIDSGEBIED", False, True),
        ("Beperkingen / opmerkingen", "BEPERKINGEN", False, True),
    )),
    ("Aanwijzer", (
        ("Naam aanwijzer", "NAAM_AANWIJZER", True, False),
        ("Functie aanwijzer", "FUNCTIE_AANWIJZER", True, False),
        ("Datum (dd-mm-jjjj)", "DATUM_AANWIJZER", False, False),
    )),
    ("Ondertekening aangewezene", (
        ("Datum (dd-mm-jjjj)", "DATUM_AANGEWEZENE", False, False),
    )),
)

DATE_FIELDS = ("INGANGSDATUM", "GELDIG_TOT", "DATUM_AANWIJZER", "DATUM_AANGEWEZENE")


def template_path(filename: str) -> Path:
    """Extern sjabloon naast de exe krijgt voorrang op een ingebundeld sjabloon."""
    program_dir = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent
    external = program_dir / "templates" / filename
    if external.is_file():
        return external
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundled = Path(sys._MEIPASS) / "templates" / filename
        if bundled.is_file():
            return bundled
    return external
