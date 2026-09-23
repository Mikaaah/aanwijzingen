# Eqraft | NEN 3140 Aanwijzingen

Windows-programma voor het maken van een aanwijzing voor IV, WV, VP of VOP en
voor het vastleggen van een instructie aan een leek. De ingevoerde bevoegdheden,
werkzaamheden en grenzen worden letterlijk in het Word-sjabloon gezet;
rolgebonden verantwoordelijkheden en een beknopt bevoegdheidskader worden
automatisch ingevuld.

**Let op:** 'Leek' is in dit programma een **instructieregistratie**, geen
elektrotechnische aanwijzing. De exacte toegestane taken en installaties worden
door de organisatie ingevuld. Bekijk het resultaat voordat het wordt ondertekend.

## Zonder Python op je werkcomputer

Download via de [GitHub Actions-pagina](https://github.com/Mikaaah/aanwijzingen/actions)
de nieuwste succesvolle uitvoering van **Bouw Windows exe**. Download onder
**Artifacts** `NEN3140_Aanwijzingen-Windows`, pak de ZIP uit en start
`NEN3140_Aanwijzingen.exe`. Op de gebruikerscomputer hoeft Python niet te zijn
geïnstalleerd. Het programma werkt zonder internet. Een PDF wordt ook gemaakt
als Microsoft Word op die computer beschikbaar is; anders krijg je alleen de
DOCX en een duidelijke melding.

Je kunt ook de kant-en-klare exe uit deze conversatie downloaden.

## Indeling

```text
NEN3140_Aanwijzingen/
├── main.py
├── config.py
├── document_generator.py
├── requirements.txt
├── README.md
├── .github/workflows/build-windows-exe.yml
├── templates/
│   └── Aanwijzing_NEN3140.docx
└── output/
```

Er is één bewerkbaar Word-sjabloon voor alle vijf keuzemogelijkheden. Het
originele sjabloon wordt nooit overschreven. Het meegeleverde Eqraft-logo staat
in de koptekst van het sjabloon. Het formulier heeft een zelfstandig vak voor
**Bevoegdheden en toegestane handelingen** en een apart, automatisch gevuld vak
voor **Verantwoordelijkheden per rol**. Binnen het bevoegdhedenvak staan het
automatische rolkader en jullie concrete toestemming los van elkaar.
Organisatie is een invoerveld in de documentinhoud.

## Velden invullen en sjabloon aanpassen

Selecteer de rol en vul de gegevens in. Velden met een sterretje zijn verplicht.
Bij iedere formele aanwijzing moeten **Specifieke werkzaamheden / instructies**
en de **plaats en datum van aanwijzing** zijn ingevuld; bij IV en WV is ook het
**Verantwoordelijkheidsgebied** verplicht. Vul in het vak **Bevoegdheden /
toegestane handelingen** de daadwerkelijk door Eqraft toegestane handelingen
in. Alle data hebben formaat `dd-mm-jjjj`.

Wil je de opmaak of vaste tekst wijzigen, open dan
`templates/Aanwijzing_NEN3140.docx` in Word. Zet desgewenst een kopie van
`templates\Aanwijzing_NEN3140.docx` naast de exe; die externe versie krijgt
voorrang boven het ingebouwde sjabloon.

Beschikbare invulvelden:

```text
{{ORGANISATIE}}                  {{VOLLEDIGE_NAAM}}
{{FUNCTIE}}                      {{AFDELING}}
{{INGANGSDATUM}}                 {{GELDIG_TOT}}
{{LOCATIE}}                      {{INSTALLATIES}}
{{VERANTWOORDELIJKHEIDSGEBIED}}  {{WERKZAAMHEDEN}}
{{BEVOEGDHEDEN}}                 {{BEPERKINGEN}}
{{NAAM_AANWIJZER}}               {{FUNCTIE_AANWIJZER}}
{{PLAATS_AANWIJZING}}            {{DATUM_AANWIJZER}}
{{DATUM_AANGEWEZENE}}
```

De automatische velden zijn `{{DOCUMENTTITEL}}`, `{{INLEIDING}}`,
`{{ROL}}`, `{{VERANTWOORDELIJKHEDEN}}` en `{{ROLBEVOEGDHEDEN}}`. De app vervangt placeholders in
paragrafen, tabellen en kop- en voetteksten; ook gesplitste Word-runs worden
afgehandeld. Een onbekende placeholder geeft een melding.

Voor een nieuw invoerveld: voeg een regel toe aan `SECTIONS` in `config.py`
met `("Veldnaam", "SLEUTEL", verplicht, meerregelig)` en zet `{{SLEUTEL}}`
in het Word-sjabloon. Voeg een datumveld ook aan `DATE_FIELDS` toe. Pas voor
een extra rol de `TYPES`-configuratie aan; een nieuw Word-sjabloon is daarvoor
niet nodig.

## Bron en grenzen van de automatische rolteksten

Deze teksten zijn **beknopte eigen parafrases** op basis van de door de gebruiker
aangeleverde NEN 3140+A3:2019 (vooral 4.2, 4.3 en bijlagen D en F); ze zijn
geen letterlijke herdruk van de norm. Controleer de persoonlijke aanwijzing en
de bedrijfsspecifieke bevoegdheden met een bevoegde persoon. Het programma
beoordeelt niet automatisch of iemand voor een rol geschikt is.

- [NEN: normuitgave (1 juli 2019)](https://www.nen.nl/nen-3140-2011-a3-2019-nl-261555)
- [NEN: toelichting per aanwijzingsrol en de wijziging van 2019](https://www.nen.nl/elektrotechniek/werkvoorschriften/laagspanninginstallaties)
- [NEN: onderscheid tussen IV en WV](https://www.nen.nl/nieuws/elektrotechniek/de-belangrijke-competenties-voor-de-nen-3140-installatieverantwoordelijke-en-werkverantwoordelijke/)

De rolteksten staan in `config.py` onder `TYPES`. Na een wijziging moet een
nieuwe exe worden gebouwd.

## Ontwikkelaars: starten en bouwen

Voor ontwikkelwerk op een computer waar Python wel mag worden gebruikt:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

De exacte opdracht voor één Windows-exe:

```powershell
python -m PyInstaller --onefile --noconsole --name NEN3140_Aanwijzingen --add-data "templates;templates" main.py
```

De Windows-bouwserver van GitHub voert deze opdracht automatisch uit bij een
push naar `main`; je hoeft lokaal niets te installeren om de exe te gebruiken.
Met `NEN3140_Aanwijzingen.exe --self-test` controleer je alle vijf rollen en
het meegeleverde sjabloon zonder het venster te openen.
