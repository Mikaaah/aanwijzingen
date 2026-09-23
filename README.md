# NEN 3140 Aanwijzingen

Dit programma neemt alle vaste teksten, opmaak, afbeeldingen, tabellen en verwijzingen rechtstreeks over uit je eigen Word-sjabloon. Het bevat zelf geen inhoudelijke aanwijzingsteksten.

## Mappen

```text
NEN3140_Aanwijzingen/
├── main.py
├── document_generator.py
├── config.py
├── requirements.txt
├── README.md
├── templates/
│   └── Aanwijzing_IV.docx    ← inbegrepen en bewerkbaar
└── output/                   ← optioneel
```

## Starten op Windows

Installeer Python 3.10 of nieuwer. Voer in PowerShell vanuit deze map uit:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

Na installatie werkt het programma zonder internet. Tkinter zit standaard in de officiële Windows-installatie van Python. Zonder Microsoft Word wordt wel een DOCX, maar geen PDF gemaakt.

## Sjabloon toevoegen

Het bewerkbare IV-sjabloon staat al onder `templates\Aanwijzing_IV.docx`. Pas de vaste tekst en opmaak rechtstreeks in Word aan. De gebruikte placeholders zijn:

```text
{{ORGANISATIE}}
{{VOLLEDIGE_NAAM}}
{{FUNCTIE}}
{{AFDELING}}
{{INGANGSDATUM}}
{{GELDIG_TOT}}
{{LOCATIE}}
{{INSTALLATIES}}
{{VERANTWOORDELIJKHEIDSGEBIED}}
{{BEPERKINGEN}}
{{NAAM_AANWIJZER}}
{{FUNCTIE_AANWIJZER}}
{{DATUM_AANWIJZER}}
{{DATUM_AANGEWEZENE}}
```

De namen moeten exact overeenkomen. Placeholders kunnen in gewone paragrafen, tabellen, kopteksten en voetteksten staan. Ook een placeholder die door Word over meerdere opmaakdelen is gesplitst wordt vervangen. Het programma meldt onbekende placeholders voordat het een document opslaat. Een veld dat niet in het sjabloon voorkomt, wordt genegeerd.

## Nieuwe placeholders toevoegen

Voeg in `config.py` onder de gewenste sectie van `SECTIONS` een veld toe in de vorm `("Getoonde naam", "SLEUTEL", verplicht, meerregelig)`. Gebruik `True` of `False` voor de laatste twee waarden. Plaats `{{SLEUTEL}}` in Word. Is het een datumveld? Voeg `SLEUTEL` ook toe aan `DATE_FIELDS`. Gebruik voor elke placeholder in één paragraaf één aaneengesloten reeks `{{...}}` zonder extra spaties.

## WV, VP en VOP toevoegen

Zet de Word-bestanden `Aanwijzing_WV.docx`, `Aanwijzing_VP.docx` en `Aanwijzing_VOP.docx` in `templates`. Voeg vervolgens bijvoorbeeld deze vermeldingen toe aan `TYPES` in `config.py`:

```python
"Werkverantwoordelijke (WV)": {"code": "WV", "template": "Aanwijzing_WV.docx"},
"Vakbekwaam persoon (VP)": {"code": "VP", "template": "Aanwijzing_VP.docx"},
"Voldoende onderricht persoon (VOP)": {"code": "VOP", "template": "Aanwijzing_VOP.docx"},
```

Dezelfde velden gelden dan voor elk type. Als andere velden nodig zijn, pas `SECTIONS` aan of breid de veldkeuze per type uit.

## Eén Windows-exe bouwen

Voer vanuit de projectmap in PowerShell uit:

```powershell
pyinstaller --onefile --noconsole --name "NEN3140_Aanwijzingen" --add-data "templates;templates" main.py
```

De exe staat dan in `dist\NEN3140_Aanwijzingen.exe`. Het sjabloon wordt ingebundeld. Om het sjabloon later te wijzigen zonder de exe opnieuw te bouwen, plaats `templates\Aanwijzing_IV.docx` naast de exe; dat externe bestand krijgt voorrang. Ook voor nieuwe aanwijzingstypen moet de code in `config.py` worden aangepast en de exe opnieuw worden gebouwd. De gebruiker kiest de opslaglocatie voor iedere nieuwe DOCX; met Microsoft Word en pywin32 maakt het programma daarnaast een PDF met dezelfde basisnaam.

Op een computer die alleen de gebouwde exe gebruikt, hoeft Python niet geïnstalleerd te worden. Voor het zelf bouwen van de exe is wel een Windows-computer met Python nodig.
