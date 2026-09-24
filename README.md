# Eqraft | NEN 3140 Aanwijzingen

Windows-programma voor het maken van een aanwijzing voor IV, WV, VP of VOP en
voor het vastleggen van instructie aan een leek of tijdelijke inzet van een zzp'er. De ingevoerde bevoegdheden,
werkzaamheden en grenzen worden letterlijk in het Word-sjabloon gezet;
rolgebonden verantwoordelijkheden en een beknopt bevoegdheidskader worden
automatisch ingevuld.

**Let op:** 'Leek' en 'ZZP'er' zijn in dit programma registraties van instructie
of tijdelijke inzet, **geen elektrotechnische aanwijzing**. Ook bij een ingehuurde
elektromonteur is voor elektrisch werk een afzonderlijke, passende rolgebonden
aanwijzing nodig. De exacte toegestane taken en installaties worden
door de organisatie ingevuld. Bekijk het resultaat voordat het wordt ondertekend.

## Zonder Python op je werkcomputer

Download via de [GitHub Actions-pagina](https://github.com/Mikaaah/aanwijzingen/actions)
de nieuwste succesvolle uitvoering van **Bouw Windows exe**. Download onder
**Artifacts** `NEN3140_Aanwijzingen-Windows`, pak de ZIP uit en start
`NEN3140_Aanwijzingen.exe`. Op de gebruikerscomputer hoeft Python niet te zijn
geïnstalleerd. Het programma werkt zonder internet. Een PDF wordt ook gemaakt
als Microsoft Word op die computer beschikbaar is; anders krijg je alleen de
DOCX en een duidelijke melding.

## Indeling

```text
NEN3140_Aanwijzingen/
├── main.py
├── ui_components.py
├── config.py
├── catalogus.py
├── catalogus_venster.py
├── settings.py
├── document_generator.py
├── requirements.txt
├── README.md
├── .github/workflows/build-windows-exe.yml
├── assets/
│   ├── eqraft_logo.png
│   ├── eqraft_logo_sidebar.png
│   ├── eqraft_icon.png
│   └── eqraft_icon.ico
├── templates/
│   └── Aanwijzing_NEN3140.docx
├── documents/
│   └── Aanwijzingsmodel.docx
└── output/
```

Er is één bewerkbaar Word-sjabloon voor alle zes keuzemogelijkheden. Het
originele sjabloon wordt nooit overschreven. Het meegeleverde Eqraft-logo staat
in de koptekst van het sjabloon. Het formulier heeft een zelfstandig vak voor
**Bevoegdheden en toegestane handelingen** en een apart, automatisch gevuld vak
voor **Verantwoordelijkheden per rol**. Binnen het bevoegdhedenvak staan het
automatische rolkader en jullie concrete toestemming los van elkaar.
Organisatie is een invoerveld in de documentinhoud. Persoonlijke taken staan
onder **Bevoegdheden per machine** als opsomming.

Het formulier gebruikt de Eqraft-kleuren en het logo. De Windows-exe heeft
het Eqraft-icoon. Boven beide handtekeningregels in het Word-sjabloon is extra
schrijfruimte vrijgemaakt. Links staan **Aanwijzing maken**, **Uitleg en werkwijze**,
**Aanwijzingsmodel**, **Alle codes beheren**, **Instellingen** en **Afsluiten**.
Boven het formulier zie je direct de
persoon, het type, de locatie en of de bevoegdheden zijn ingevuld. Kaarten en
invoervelden hebben een rustige, afgeronde Eqraft-opmaak. Onderaan zie je de
voortgang bij verplichte velden.

## Velden invullen en sjabloon aanpassen

Selecteer de rol en vul de gegevens in. Velden met een sterretje zijn verplicht.
Bij iedere formele aanwijzing moeten **Specifieke werkzaamheden / instructies**
en de **plaats en datum van aanwijzing** zijn ingevuld; bij IV en WV is ook het
**Verantwoordelijkheidsgebied** verplicht. Vul in het vak **Bevoegdheden /
toegestane handelingen** de daadwerkelijk door Eqraft toegestane handelingen
in. Alle data hebben formaat `dd-mm-jjjj`.

## Keuzevensters en eigen aanvullingen

Naast **Installaties**, **Werkzaamheden**, **Procedures** en **Bevoegdheden**
staat **Kies codes**. Daar kun je zoeken en via het rondje links meer dan één item kiezen.
Een klik op een regel toont uitleg, zonder de code te selecteren. Rechts
verschijnt per code de toelichting uit `documents/Aanwijzingsmodel.docx`:

| Veld | Codes |
| --- | --- |
| Installaties | M: machines en installatiedelen |
| Werkzaamheden | L: mechanische taken; S: specifieke vaardigheden |
| Procedures | P: procedureonderwerpen |
| Bevoegdheden | R: aanvullende bevoegdheden |

Via **Alle codes beheren** in de zijbalk bekijk je L-, S-, M-, P- en R-codes
op één plek en voeg je eigen codes en uitleg toe zonder het formulier te openen.
Eigen codes kun je later bewerken of verwijderen. Deze lijst
wordt per Windows-gebruiker opgeslagen in
`%LOCALAPPDATA%\Eqraft\NEN3140_Aanwijzingen\catalogus.json` en blijft na een
update van de exe bestaan. De ingebouwde codes komen rechtstreeks uit het
Word-model en zijn daarom alleen te wijzigen door dat document te vervangen.
Zet desgewenst een aangepaste kopie in `documents\Aanwijzingsmodel.docx` naast
de exe; die krijgt voorrang op de ingebouwde versie. In de zijbalk opent
**Aanwijzingsmodel** het volledige Word-bestand. De complete downloadbundel bevat
de bijgewerkte Word-bestanden; zet `documents/` en `templates/` uit die bundel
naast de exe als je alleen de exe van GitHub Actions gebruikt. De losse exe uit
de publieke repository bevat de oudere versie van die twee Word-bestanden.

De geselecteerde **code en benaming** komen in het tekstveld en daarna in de
aanwijzing. Vrije tekst kan daarnaast blijven staan. **S01** is volgens het
model alleen een rubriektitel en is daarom niet selecteerbaar. Het aangeleverde
model bevat geen aparte benaming voor M04 en M06; daarvoor gebruikt de app de
omschrijving uit dezelfde modelrij. Voor M07 is geen verdere uitleg ingevuld.

**M12 – Alle machines – uitsluitend mechanische taken** staat in het bijgewerkte
aanwijzingsmodel van de complete downloadbundel. De keuze geldt alleen voor de afgesproken werkplek en de
persoonlijk gekozen mechanische L-taken. Aansluiten, afkoppelen, meten,
schakelen en werken aan elektrische onderdelen vallen er niet onder.

Met **Machine en taken kiezen** kies je één machine en meerdere persoonlijk
toegestane taken tegelijk. Het document krijgt bijvoorbeeld deze indeling:

```text
Machine: M02 – Baxmatic
Bevoegdheden:
• S02 – [benaming uit het aanwijzingsmodel]
• S03 – [benaming uit het aanwijzingsmodel]
```

De keuze vraagt geen procedure of apart voorwaardenveld. Het algemene formulier
heeft nog een optioneel procedureveld voor situaties waar dat nuttig is. Losse
codes geven op zichzelf geen algemene toestemming. Bij M12 zijn alleen
mechanische L-taken selecteerbaar.

1. Kies IV, WV, VP, VOP, Leek of ZZP'er. Bij Leek en ZZP'er registreer je instructie en inzet; dit is geen elektrotechnische aanwijzing.
2. Vul gegevens, installaties, taken, persoonlijke bevoegdheden en beperkingen in. De rolgebonden teksten volgen automatisch uit de gekozen rol.
3. Kies in **Instellingen** één keer de bestaande hoofdmap **AANWIJZINGEN** en **Word en PDF**, **Alleen Word** of **Alleen PDF**. Daarna slaat **Document maken** op onder bijvoorbeeld `AANWIJZINGEN/WV/Mika van Eijken/`. Voor PDF is Microsoft Word nodig; bij **Alleen PDF** en zonder Word blijft een Word-document als terugvaloptie bewaard. Instellingen worden bewaard in `%LOCALAPPDATA%\Eqraft\NEN3140_Aanwijzingen\instellingen.json`.

De aanwijzer beoordeelt de kennis en ervaring van de persoon, de concrete
werkzaamheden en de grenzen vóór ondertekening. Het programma kan die
beoordeling niet voor de aanwijzer doen.

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
{{PROCEDURES}}                  {{COMBINATIES}}
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
python -m PyInstaller --onefile --noconsole --name NEN3140_Aanwijzingen --icon assets/eqraft_icon.ico --add-data "templates;templates" --add-data "assets;assets" --add-data "documents;documents" main.py
```

De Windows-bouwserver van GitHub voert deze opdracht automatisch uit bij een
push naar `main` of in een pull request; je hoeft lokaal niets te installeren.
Met `NEN3140_Aanwijzingen.exe --self-test` controleer je alle zes rollen en
het meegeleverde sjabloon zonder het venster te openen.
