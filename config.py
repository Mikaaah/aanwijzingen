"""Sjabloonvelden en beknopte, eigen parafrases van NEN 3140+A3:2019."""

from pathlib import Path
import sys


APP_TITLE = "NEN 3140 Aanwijzingen"
TEMPLATE_NAME = "Aanwijzing_NEN3140.docx"

TYPES = {
    "Installatieverantwoordelijke (IV)": {
        "code": "IV", "template": TEMPLATE_NAME,
        "title": "Aanwijzing installatieverantwoordelijke",
        "role": "Installatieverantwoordelijke (IV)",
        "intro": "De hieronder genoemde persoon wordt voor het omschreven gebied aangewezen als installatieverantwoordelijke.",
        "responsibilities": (
            "De veiligheid van de omschreven elektrische installaties en arbeidsmiddelen beheren.\n"
            "Inspecties en tijdig herstel van gevonden gebreken organiseren.\n"
            "De frequentie van visuele controles bepalen en vastleggen.\n"
            "Toegangsregels voor ruimten met elektrisch gevaar en bedieningsprocedures organiseren."
        ),
        "authorities": (
            "Voor het afgebakende installatiegebied de regels voor bediening en toegang vaststellen, "
            "werkplannen beoordelen en in afstemming met de WV toestemming voor de aanvang van werk geven."
        ),
        "required_fields": ("VERANTWOORDELIJKHEIDSGEBIED", "WERKZAAMHEDEN", "PLAATS_AANWIJZING", "DATUM_AANWIJZER"),
    },
    "Werkverantwoordelijke (WV)": {
        "code": "WV", "template": TEMPLATE_NAME,
        "title": "Aanwijzing werkverantwoordelijke",
        "role": "Werkverantwoordelijke (WV)",
        "intro": "De hieronder genoemde persoon wordt voor de omschreven werkzaamheden aangewezen als werkverantwoordelijke.",
        "responsibilities": (
            "De risico's van het omschreven werk bepalen en een veilige werkplek regelen.\n"
            "Plannen, werkwijzen, hulpmiddelen en beschermingsmiddelen voor het werk bepalen.\n"
            "Geschikte uitvoerenden kiezen, hen instrueren en passend toezicht organiseren.\n"
            "Werkvoorbereiding en uitvoering vooraf met de IV afstemmen."
        ),
        "authorities": (
            "Binnen het afgesproken werk de uitvoering organiseren, de werkwijze en uitvoerenden "
            "bepalen en opdracht tot het beschreven werk geven volgens de geldende procedures."
        ),
        "required_fields": ("VERANTWOORDELIJKHEIDSGEBIED", "WERKZAAMHEDEN", "PLAATS_AANWIJZING", "DATUM_AANWIJZER"),
    },
    "Vakbekwaam persoon (VP)": {
        "code": "VP", "template": TEMPLATE_NAME,
        "title": "Aanwijzing vakbekwaam persoon",
        "role": "Vakbekwaam persoon (VP)",
        "intro": "De hieronder genoemde persoon wordt voor de omschreven taken aangewezen als vakbekwaam persoon.",
        "responsibilities": (
            "De gevaren en risico's van de eigen, omschreven werkzaamheden zelfstandig inschatten.\n"
            "Voor die werkzaamheden doeltreffende veiligheidsmaatregelen nemen en de geldende werkwijze volgen.\n"
            "De eigen taken veilig uitvoeren en verantwoording afleggen over de uitvoering.\n"
            "Bij onveilige omstandigheden stoppen en de werkverantwoordelijke informeren."
        ),
        "authorities": (
            "Na opdracht de omschreven elektrotechnische werkzaamheden aan de genoemde installaties "
            "uitvoeren. Bij eenvoudig werk de werkwijze zelfstandig bepalen als dit voor deze taak is vastgelegd."
        ),
        "required_fields": ("WERKZAAMHEDEN", "PLAATS_AANWIJZING", "DATUM_AANWIJZER"),
    },
    "Voldoende onderricht persoon (VOP)": {
        "code": "VOP", "template": TEMPLATE_NAME,
        "title": "Aanwijzing voldoende onderricht persoon",
        "role": "Voldoende onderricht persoon (VOP)",
        "intro": "De hieronder genoemde persoon wordt uitsluitend voor de beschreven en geïnstrueerde werkzaamheden aangewezen als voldoende onderricht persoon.",
        "responsibilities": (
            "Alleen de specifiek vastgelegde werkzaamheden uitvoeren waarvoor instructie is gegeven.\n"
            "De daarbij uitgelegde elektrische risico's herkennen en de opgedragen veiligheidsmaatregelen toepassen.\n"
            "Bij een onbekende situatie of afwijking het werk stoppen en afstemmen met de verantwoordelijke voor het werk."
        ),
        "authorities": (
            "Na gerichte instructie en opdracht uitsluitend de ingevulde werkzaamheden met beperkte "
            "elektrische risico's uitvoeren, in de vermelde ruimten en aan de vermelde installaties."
        ),
        "required_fields": ("WERKZAAMHEDEN", "PLAATS_AANWIJZING", "DATUM_AANWIJZER"),
    },
    "Leek (instructieregistratie)": {
        "code": "LEEK", "template": TEMPLATE_NAME,
        "title": "Registratie instructie leek",
        "role": "Leek (geen elektrotechnische aanwijzing)",
        "intro": "Dit document registreert de aan de hieronder genoemde persoon gegeven instructies en het afgesproken gebruik. Het is geen elektrotechnische aanwijzing.",
        "responsibilities": (
            "De gegeven instructies voor het afgesproken, normale gebruik opvolgen.\n"
            "Schade, storingen en onveilige situaties melden volgens de interne afspraken.\n"
            "Geen elektrotechnische werkzaamheden uitvoeren op grond van deze registratie."
        ),
        "authorities": (
            "Alleen het beschreven normale gebruik volgens de gegeven instructies. Deze registratie "
            "geeft geen bevoegdheid om elektrotechnische werkzaamheden uit te voeren."
        ),
        "required_fields": (),
    },
}

SECTIONS = (
    ("Gegevens persoon", (
        ("Organisatie", "ORGANISATIE", True, False),
        ("Volledige naam", "VOLLEDIGE_NAAM", True, False),
        ("Functie", "FUNCTIE", True, False),
        ("Afdeling", "AFDELING", False, False),
        ("Ingangsdatum (dd-mm-jjjj)", "INGANGSDATUM", True, False),
        ("Geldig tot (dd-mm-jjjj)", "GELDIG_TOT", True, False),
    )),
    ("Omvang en werkzaamheden", (
        ("Locatie / gebouw", "LOCATIE", True, False),
        ("Installatie(s) / installatiedelen", "INSTALLATIES", True, True),
        ("Verantwoordelijkheidsgebied", "VERANTWOORDELIJKHEIDSGEBIED", False, True),
        ("Specifieke werkzaamheden / instructies", "WERKZAAMHEDEN", False, True),
    )),
    ("Bevoegdheden en grenzen", (
        ("Bevoegdheden / toegestane handelingen", "BEVOEGDHEDEN", True, True),
        ("Beperkingen / opmerkingen", "BEPERKINGEN", False, True),
    )),
    ("Namens de organisatie", (
        ("Naam aanwijzer / instructiegever", "NAAM_AANWIJZER", True, False),
        ("Functie aanwijzer / instructiegever", "FUNCTIE_AANWIJZER", True, False),
        ("Plaats van aanwijzing / instructie", "PLAATS_AANWIJZING", False, False),
        ("Datum (dd-mm-jjjj)", "DATUM_AANWIJZER", False, False),
    )),
    ("Ondertekening betrokkene", (
        ("Datum (dd-mm-jjjj)", "DATUM_AANGEWEZENE", False, False),
    )),
)

DATE_FIELDS = ("INGANGSDATUM", "GELDIG_TOT", "DATUM_AANWIJZER", "DATUM_AANGEWEZENE")


def document_values(input_values: dict[str, str], role: dict) -> dict[str, str]:
    """Alleen de velden met een rolafhankelijke inhoud automatisch invullen."""
    values = dict(input_values)
    values.update(
        DOCUMENTTITEL=role["title"], ROL=role["role"],
        INLEIDING=role["intro"], VERANTWOORDELIJKHEDEN=role["responsibilities"],
        ROLBEVOEGDHEDEN=role["authorities"],
    )
    return values


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
