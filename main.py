"""Eqraft-formulier voor het invullen van NEN 3140-aanwijzingssjablonen."""

from datetime import datetime
import os
from pathlib import Path
import re
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import traceback

from catalogus import CatalogStore, MODEL_NAME, merge_selected_lines
from catalogus_venster import choose_codes, make_combination, manage_codes, format_machine_permissions
from config import (APP_TITLE, DATE_FIELDS, PICKER_FIELDS, SECTIONS, TYPES,
                    document_values, template_path, resource_path)
from document_generator import TemplateError, _all_paragraphs, export_pdf, generate_docx
from settings import AppSettings, EXPORT_MODES, load_settings, output_paths, save_settings
from ui_components import (ActionButton, BACKGROUND, BORDER, Card, DARK, ERROR,
                           INK, InputBox, MUTED, NavItem, SelectBox, SIDEBAR,
                           SURFACE, SummaryTile, WHITE, YELLOW, rounded_rect)


SECTION_TIPS = {
    "Gegevens persoon": "Vul de persoon en de periode van deze aanwijzing in.",
    "Omvang en werkzaamheden": "Baken locatie, machines en de toegestane werkzaamheden concreet af.",
    "Bevoegdheden en grenzen": "Leg hier vast wat deze persoon mag doen en welke grenzen gelden.",
    "Namens de organisatie": "Gegevens van degene die de aanwijzing afgeeft.",
    "Ondertekening betrokkene": "De datum waarop de betrokken persoon ondertekent.",
}

FIELD_TIPS = {
    "INSTALLATIES": "Welke machine, gebouwinstallatie of installatiedelen vallen hieronder?",
    "VERANTWOORDELIJKHEIDSGEBIED": (
        "Beschrijf voor welk deel van het pand, welke machines en welke mensen deze rol geldt. "
        "Vermeld waar het gebied eindigt en wie verantwoordelijk is voor het overige deel. "
        "Voorbeeld: WV voor VOP en VP in de assemblagehal; gebouwinstallatie valt onder de IV van het pand."
    ),
    "WERKZAAMHEDEN": "Voor VOP: beschrijf elke toegestane taak en de gegeven instructie.",
    "PROCEDURES": "Kies P-codes. Vul documentnummer, revisie en gegeven instructie ook concreet in.",
    "BEVOEGDHEDEN": "Vul persoonlijke toestemming in. Het automatische rolkader staat apart in Word.",
    "COMBINATIES": "Kies per machine alle taken die deze persoon daar mag doen. Voeg voor een andere machine een volgende regel toe.",
    "BEPERKINGEN": "Noem uitgesloten taken, toezicht of afspraken bij afwijkingen.",
}


def valid_date(text: str):
    if not re.fullmatch(r"\d{2}-\d{2}-\d{4}", text):
        raise ValueError("gebruik dd-mm-jjjj")
    return datetime.strptime(text, "%d-%m-%Y").date()


def safe_filename(text: str) -> str:
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text).strip(" .")
    return text or "Onbekend"


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        screen_width, screen_height = self.winfo_screenwidth(), self.winfo_screenheight()
        width = min(1180, max(760, screen_width - 44))
        height = min(840, max(520, screen_height - 120))
        self.geometry(f"{width}x{height}+{max(0, (screen_width-width)//2)}"
                      f"+{max(0, (screen_height-height-42)//2)}")
        self.minsize(760, 520)
        self.configure(bg=BACKGROUND)
        self.widgets = {}
        self.field_labels = {}
        self.field_frames = {}
        self.error_keys = set()
        self.selected_codes = {key: [] for key in PICKER_FIELDS}
        self.inserted_lines = {key: [] for key in PICKER_FIELDS}
        self.logo_image = None
        self.settings = load_settings()
        self.type_var = tk.StringVar(value=next(iter(TYPES)))
        self.role_preview = tk.StringVar()
        self.progress_text = tk.StringVar()
        self.summary = {name: tk.StringVar() for name in ("person", "role", "location", "authority")}
        self.summary_status = tk.StringVar()
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("Eq.Flat.TCombobox", fieldbackground=WHITE, background=WHITE,
                             foreground=INK, arrowcolor=INK, borderwidth=0, padding=2)
        self.style.map("Eq.Flat.TCombobox", fieldbackground=[("readonly", WHITE)],
                       selectbackground=[("readonly", WHITE)],
                       selectforeground=[("readonly", INK)])
        icon = resource_path("assets/eqraft_icon.png")
        if icon.is_file():
            try:
                self.icon_image = tk.PhotoImage(file=str(icon))
                self.iconphoto(True, self.icon_image)
            except tk.TclError:
                pass
        self._build()
        self.type_var.trace_add("write", self._update_role)
        self._update_role()

    def _build(self):
        self._build_sidebar()
        main = tk.Frame(self, bg=BACKGROUND)
        main.pack(side="left", fill="both", expand=True)

        heading = tk.Frame(main, bg=BACKGROUND, padx=30, pady=11)
        heading.pack(fill="x")
        tk.Label(heading, text="Aanwijzing aanmaken", font=("Arial", 19, "bold"),
                 bg=BACKGROUND, fg=INK).pack(anchor="w")
        tk.Label(heading, text="Leg de aanwijzing duidelijk vast en maak daarna het Word-document.",
                 font=("Arial", 9), bg=BACKGROUND, fg=MUTED).pack(anchor="w", pady=(2, 0))

        overview = Card(main, padding=11)
        overview.pack(fill="x", padx=28, pady=(0, 10))
        top = overview.body
        tk.Label(top, text="HUIDIGE AANWIJZING", bg=SURFACE, fg=INK,
                 font=("Arial", 9, "bold")).pack(anchor="w", pady=(0, 6))
        grid = tk.Frame(top, bg=SURFACE)
        grid.pack(fill="x")
        self.summary_grid = grid
        self.summary_tiles = []
        for key, label in (
            ("person", "PERSOON"), ("role", "TYPE"),
            ("location", "LOCATIE"), ("authority", "BEVOEGDHEDEN")
        ):
            self.summary_tiles.append(SummaryTile(grid, label, self.summary[key]))
        self._layout_summary(4)
        grid.bind("<Configure>", self._summary_resized)
        tk.Label(top, textvariable=self.summary_status, bg=SURFACE, fg=INK,
                 font=("Arial", 8)).pack(anchor="w", pady=(2, 0))

        action_bar = tk.Frame(main, bg=SURFACE, padx=28, pady=12)
        action_bar.pack(side="bottom", fill="x")
        tk.Frame(action_bar, bg=BORDER, height=1).pack(side="top", fill="x", pady=(0, 10))
        actions = tk.Frame(action_bar, bg=SURFACE)
        actions.pack(fill="x")
        self.primary_button = ActionButton(actions, "Document maken", self.create_document,
                                           primary=True, width=183)
        self.primary_button.pack(side="right", padx=(10, 0))
        ActionButton(actions, "Velden wissen", self.clear_fields, width=142).pack(side="right")
        tk.Label(actions, textvariable=self.progress_text, bg=SURFACE, fg=MUTED,
                 font=("Arial", 9)).pack(side="left")

        area = tk.Frame(main, bg=BACKGROUND)
        area.pack(fill="both", expand=True, padx=(28, 18))
        canvas = tk.Canvas(area, bg=BACKGROUND, highlightthickness=0)
        scrollbar = ttk.Scrollbar(area, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=BACKGROUND)
        self.scroll_canvas, self.content = canvas, content
        self.content_window = canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", self._resize_scroll_content)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        canvas.bind_all("<Button-4>", lambda _e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda _e: canvas.yview_scroll(1, "units"))

        role_card = Card(content, padding=15)
        role_card.pack(fill="x", pady=(0, 13))
        tk.Label(role_card.body, text="01  Type aanwijzing", bg=SURFACE, fg=INK,
                 font=("Arial", 13, "bold")).pack(anchor="w")
        tk.Label(role_card.body, text="Kies de rol. De bijbehorende verantwoordelijkheden worden automatisch ingevuld.",
                 bg=SURFACE, fg=MUTED, font=("Arial", 9),
                 wraplength=720, justify="left").pack(anchor="w", pady=(2, 6))
        selection = SelectBox(role_card.body, self.type_var, list(TYPES))
        selection.pack(fill="x")
        self.role_note = tk.Label(role_card.body, textvariable=self.role_preview,
                                  bg=SURFACE, fg=MUTED, font=("Arial", 9),
                                  anchor="w", justify="left", wraplength=700)
        self.role_note.pack(fill="x", pady=(6, 0))

        for number, (section_name, fields) in enumerate(SECTIONS, start=2):
            card = Card(content)
            card.pack(fill="x", pady=(0, 18))
            body = card.body
            tk.Label(body, text=f"{number:02d}  {section_name}", bg=SURFACE, fg=INK,
                     font=("Arial", 13, "bold")).pack(anchor="w")
            tk.Label(body, text=SECTION_TIPS[section_name], bg=SURFACE, fg=MUTED,
                     font=("Arial", 9), wraplength=720,
                     justify="left").pack(anchor="w", pady=(5, 19))
            fields_grid = tk.Frame(body, bg=SURFACE)
            fields_grid.pack(fill="x")
            fields_grid.columnconfigure(0, weight=1, uniform="fields")
            fields_grid.columnconfigure(1, weight=1, uniform="fields")
            row = col = 0
            for label, key, required, multiline in fields:
                if multiline and col:
                    row, col = row + 1, 0
                field = tk.Frame(fields_grid, bg=SURFACE)
                field.grid(row=row, column=0 if multiline else col,
                           columnspan=2 if multiline else 1, sticky="ew",
                           padx=(0, 0 if multiline or col else 18), pady=(0, 18))
                label_row = tk.Frame(field, bg=SURFACE)
                label_row.pack(fill="x", pady=(0, 7))
                label_widget = tk.Label(label_row, text=label, bg=SURFACE, fg=INK,
                                        font=("Arial", 9, "bold"), anchor="w",
                                        wraplength=260, justify="left")
                label_widget.pack(side="left", anchor="w")
                if key in PICKER_FIELDS:
                    ActionButton(label_row, "Kies codes", lambda chosen_key=key: self._choose_for(chosen_key),
                                 width=124).pack(side="right")
                elif key == "COMBINATIES":
                    ActionButton(label_row, "Machine en taken kiezen", self._add_combination,
                                 width=195).pack(side="right")
                field.bind("<Configure>", lambda e, target=label_widget:
                           target.configure(wraplength=max(160, e.width - 8)))
                self.field_labels[key] = (label_widget, label, required)
                wrapper = InputBox(field, multiline=multiline,
                                   on_change=lambda *_args, field_key=key: self._field_changed(field_key))
                wrapper.pack(fill="x")
                self.field_frames[key] = wrapper
                self.widgets[key] = wrapper.widget
                if key in FIELD_TIPS:
                    tk.Label(field, text=FIELD_TIPS[key], bg=SURFACE, fg=MUTED,
                             font=("Arial", 8), wraplength=710,
                             justify="left").pack(anchor="w", pady=(5, 0))
                if multiline:
                    row += 1
                elif col:
                    row, col = row + 1, 0
                else:
                    col = 1

    def _build_sidebar(self):
        sidebar_canvas = tk.Canvas(self, bg=BACKGROUND, width=236,
                                   highlightthickness=0, borderwidth=0)
        sidebar_canvas.pack(side="left", fill="y", padx=(12, 0), pady=12)
        sidebar = tk.Frame(sidebar_canvas, bg=SIDEBAR)
        sidebar_window = sidebar_canvas.create_window(14, 14, anchor="nw", window=sidebar)

        def draw_sidebar(event):
            sidebar_canvas.delete("sidebar_shape")
            rounded_rect(sidebar_canvas, 0, 0, event.width, event.height, 18, SIDEBAR)
            for item in sidebar_canvas.find_all():
                if item != sidebar_window:
                    sidebar_canvas.addtag_withtag("sidebar_shape", item)
            sidebar_canvas.tag_lower("sidebar_shape", sidebar_window)
            sidebar_canvas.itemconfigure(sidebar_window, width=max(1, event.width - 28),
                                         height=max(1, event.height - 28))

        sidebar_canvas.bind("<Configure>", draw_sidebar)
        logo = resource_path("assets/eqraft_logo_sidebar.png")
        if logo.is_file():
            try:
                self.logo_image = tk.PhotoImage(file=str(logo))
                logo_canvas = tk.Canvas(sidebar, width=180, height=62, bg=SIDEBAR,
                                        highlightthickness=0, borderwidth=0)
                # De witte binnenzijde van het beeldmerk is in de aangeleverde
                # transparante PNG uitgespaard. Vul uitsluitend dat vlak in.
                logo_canvas.create_polygon(30, 22, 50, 15, 50, 39,
                                           40, 44, 40, 34, 30, 39,
                                           fill=WHITE, outline="")
                logo_canvas.create_image(0, 0, image=self.logo_image, anchor="nw")
                logo_canvas.pack(anchor="w", padx=14, pady=(18, 24))
            except tk.TclError:
                pass
        if self.logo_image is None:
            tk.Label(sidebar, text="EQRAFT", bg=SIDEBAR, fg=INK,
                     font=("Arial", 19, "bold")).pack(anchor="w", padx=18, pady=(30, 28))
        tk.Label(sidebar, text="WERKOMGEVING", bg=SIDEBAR, fg="#51491D",
                 font=("Arial", 8, "bold")).pack(anchor="w", padx=17, pady=(0, 13))
        NavItem(sidebar, "Aanwijzing maken", lambda: self.scroll_canvas.yview_moveto(0),
                selected=True).pack(fill="x", padx=6, pady=(0, 7))
        NavItem(sidebar, "Uitleg en werkwijze", self._show_guide).pack(fill="x", padx=6)
        NavItem(sidebar, "Aanwijzingsmodel", self._open_model).pack(fill="x", padx=6, pady=(7, 0))
        NavItem(sidebar, "Alle codes beheren", self._manage_catalog).pack(fill="x", padx=6, pady=(7, 0))
        NavItem(sidebar, "Instellingen", self._show_settings).pack(fill="x", padx=6, pady=(7, 0))

        bottom = tk.Frame(sidebar, bg=SIDEBAR)
        bottom.pack(side="bottom", fill="x", padx=7, pady=(0, 12))
        tk.Frame(bottom, bg="#D3BB40", height=1).pack(fill="x", padx=8, pady=(0, 12))
        NavItem(bottom, "Afsluiten", self.destroy).pack(fill="x")
        tk.Label(bottom, text="NEN 3140  ·  EQRAFT", bg=SIDEBAR, fg="#51491D",
                 font=("Arial", 8)).pack(anchor="w", padx=16, pady=(14, 0))

    def _layout_summary(self, columns):
        for col in range(4):
            self.summary_grid.columnconfigure(col, weight=1 if col < columns else 0,
                                              uniform="summary" if col < columns else "")
        for index, tile in enumerate(self.summary_tiles):
            tile.grid(row=index // columns, column=index % columns,
                      sticky="ew", padx=(0, 8), pady=(0, 8))
        self.summary_columns = columns

    def _summary_resized(self, event):
        columns = 4 if event.width >= 590 else 2
        if columns != self.summary_columns:
            self._layout_summary(columns)

    def _resize_scroll_content(self, event):
        width = max(1, min(900, event.width - 12))
        self.scroll_canvas.coords(self.content_window, (event.width - width) / 2, 0)
        self.scroll_canvas.itemconfigure(self.content_window, width=width)
        self.role_note.configure(wraplength=max(200, width - 100))

    def _on_mousewheel(self, event):
        widget = self.winfo_containing(event.x_root, event.y_root)
        while widget is not None and widget != self.scroll_canvas:
            widget = getattr(widget, "master", None)
        if widget == self.scroll_canvas and event.delta:
            self.scroll_canvas.yview_scroll(-int(event.delta / 120), "units")

    def _field_changed(self, key):
        self.error_keys.discard(key)
        box = self.field_frames[key]
        if box.state == "error":
            box.state = "focus"
            box._draw()
        self._update_progress()

    def _update_progress(self, *_args):
        role = TYPES[self.type_var.get()]
        required = {key for _, fields in SECTIONS for _, key, mandatory, _ in fields
                    if mandatory or key in role["required_fields"]}
        values = self._values()
        count = sum(bool(values[key]) for key in required)
        self.progress_text.set(f"{count} / {len(required)} verplichte velden ingevuld")
        missing = len(required) - count
        if missing:
            self.summary_status.set(f"Nog {missing} verplichte velden invullen voordat je het document kunt maken.")
        else:
            try:
                start, until = valid_date(values["INGANGSDATUM"]), valid_date(values["GELDIG_TOT"])
                if until < start:
                    raise ValueError("einddatum voor ingangsdatum")
                for field in DATE_FIELDS:
                    if values[field]:
                        valid_date(values[field])
            except ValueError:
                self.summary_status.set("Alle velden ingevuld · controleer de datums (dd-mm-jjjj).")
            else:
                self.summary_status.set("Alle verplichte velden ingevuld · klaar voor controle en opslag.")
        self.summary["person"].set(self._short(values["VOLLEDIGE_NAAM"]) or "Nog invullen")
        self.summary["role"].set(role["code"])
        self.summary["location"].set(self._short(values["LOCATIE"]) or "Nog invullen")
        self.summary["authority"].set("Ingevuld" if values["BEVOEGDHEDEN"] else "Nog invullen")

    @staticmethod
    def _short(value, maximum=23):
        return value if len(value) <= maximum else value[:maximum - 1] + "…"

    def _update_role(self, *_args):
        role = TYPES[self.type_var.get()]
        for key, (label_widget, label, required) in self.field_labels.items():
            label_widget.configure(text=label + ("  *" if required or key in role["required_fields"] else ""))
        if role["code"] in ("LEEK", "ZZP"):
            self.role_preview.set("Leg de toegestane taken en machines persoonlijk vast. "
                                  "Deze keuze geeft geen elektrotechnische bevoegdheid.")
        else:
            self.role_preview.set("De rolteksten worden automatisch ingevuld. "
                                  "Vul persoonlijke taken, bevoegdheden en grenzen hieronder in.")
        self._update_progress()

    def _show_guide(self):
        self._dialog(
            "Zo werkt het",
            "1. Kies IV, WV, VP, VOP, Leek of ZZP'er. Leek en ZZP'er registreren inzet of instructie; "
            "voor elektrisch werk is daarnaast een passende NEN-aanwijzing nodig.\n\n"
            "2. Vul de velden met * in. Met Kies codes selecteer je machines (M), taken (L/S), "
            "procedures (P) en aanvullende bevoegdheden (R). Klik op de tekst voor uitleg; "
            "alleen via het rondje links selecteer je een code. Beheer nieuwe codes via de zijbalk.\n\n"
            "3. Kies bij Bevoegdheden per machine één machine en meerdere toegestane taken. "
            "Voor M12 zijn uitsluitend mechanische L-taken mogelijk. De procedures elders in het formulier "
            "zijn optioneel; de bevoegdheidsregel vraagt er niet om.\n\n"
            "4. Kies bij Instellingen de hoofdmap AANWIJZINGEN en het gewenste bestandsformaat. "
            "Document maken slaat daarna automatisch op onder rol / persoonsnaam. Controleer voor ondertekening.",
            kind="info",
        )

    def _open_model(self):
        model = resource_path(MODEL_NAME)
        if not model.is_file():
            self._dialog("Aanwijzingsmodel ontbreekt", f"Het Word-bestand is niet gevonden:\n{model}", kind="error")
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(model))
            else:
                self._dialog("Aanwijzingsmodel", f"Het model staat op:\n{model}")
        except OSError as exc:
            self._dialog("Aanwijzingsmodel niet geopend", f"Open het bestand zelf in Word:\n{model}\n\n{exc}", kind="error")

    def _manage_catalog(self):
        try:
            manage_codes(self, CatalogStore())
        except (OSError, ValueError, FileNotFoundError) as exc:
            self._dialog("Codelijst niet beschikbaar", str(exc), kind="error")

    def _show_settings(self):
        window = tk.Toplevel(self)
        window.title("Instellingen")
        window.configure(bg=BACKGROUND)
        window.geometry(f"590x385+{self.winfo_rootx()+60}+{self.winfo_rooty()+45}")
        window.minsize(530, 355)
        window.transient(self)
        card = Card(window, padding=21, expand=True)
        card.pack(fill="both", expand=True, padx=12, pady=12)
        body = card.body
        tk.Label(body, text="Instellingen", bg=SURFACE, fg=INK,
                 font=("Arial", 16, "bold")).pack(anchor="w", pady=(0, 6))
        tk.Label(body, text="Bepaal waar de documenten komen en welke bestanden je maakt.",
                 bg=SURFACE, fg=MUTED, font=("Arial", 9)).pack(anchor="w", pady=(0, 19))
        tk.Label(body, text="Hoofdmap aanwijzingen", bg=SURFACE, fg=INK,
                 font=("Arial", 10, "bold")).pack(anchor="w")
        tk.Label(body, text="Kies je bestaande map AANWIJZINGEN. Daaronder maakt de app rol / persoonsnaam aan.",
                 bg=SURFACE, fg=MUTED, font=("Arial", 9), wraplength=515,
                 justify="left").pack(anchor="w", pady=(2, 7))
        folder = tk.StringVar(value=self.settings.output_root)
        folder_row = tk.Frame(body, bg=SURFACE)
        folder_row.pack(fill="x", pady=(0, 20))
        tk.Entry(folder_row, textvariable=folder, font=("Arial", 10),
                 bg=WHITE, fg=INK, relief="solid", bd=1).pack(side="left", fill="x", expand=True, ipady=8)

        def browse():
            start = folder.get().strip()
            initial = start if start and Path(start).is_dir() else str(Path.home() / "Documents")
            selected = filedialog.askdirectory(parent=window, title="Kies hoofdmap AANWIJZINGEN",
                                               initialdir=initial if Path(initial).is_dir() else str(Path.home()))
            if selected:
                folder.set(selected)

        ActionButton(folder_row, "Bladeren", browse, width=110).pack(side="left", padx=(8, 0))
        tk.Label(body, text="Bestanden maken", bg=SURFACE, fg=INK,
                 font=("Arial", 10, "bold")).pack(anchor="w")
        options = list(EXPORT_MODES)
        format_choice = ttk.Combobox(body, state="readonly", values=options, font=("Arial", 10))
        format_choice.set(next(label for label, value in EXPORT_MODES.items()
                               if value == self.settings.export_mode))
        format_choice.pack(fill="x", pady=(5, 7))
        tk.Label(body, text="Voor PDF is Microsoft Word op deze pc nodig. Zonder Word bewaren we altijd de Word-versie.",
                 bg=SURFACE, fg=MUTED, font=("Arial", 9),
                 wraplength=515, justify="left").pack(anchor="w")

        def close():
            window.grab_release()
            window.destroy()

        def save():
            selected = folder.get().strip()
            if selected and not Path(selected).is_dir():
                messagebox.showerror("Map ontbreekt", "Kies een bestaande hoofdmap voor de aanwijzingen.", parent=window)
                return
            next_settings = AppSettings(selected, EXPORT_MODES[format_choice.get()])
            try:
                save_settings(next_settings)
            except (OSError, ValueError) as exc:
                messagebox.showerror("Niet opgeslagen", str(exc), parent=window)
                return
            self.settings = next_settings
            close()

        buttons = tk.Frame(body, bg=SURFACE)
        buttons.pack(side="bottom", fill="x", pady=(10, 0))
        ActionButton(buttons, "Opslaan", save, primary=True, width=120).pack(side="right")
        ActionButton(buttons, "Annuleren", close, width=120).pack(side="right", padx=(0, 8))
        window.protocol("WM_DELETE_WINDOW", close)
        window.bind("<Escape>", lambda _e: close())
        window.grab_set()
        self.wait_window(window)

    def _output_root(self):
        root = self.settings.output_root
        if root and Path(root).is_dir():
            return root
        initial = str(Path.home() / "Documents")
        selected = filedialog.askdirectory(
            parent=self, title="Kies de hoofdmap AANWIJZINGEN (eenmalig)",
            initialdir=initial if Path(initial).is_dir() else str(Path.home()),
        )
        if selected:
            self.settings.output_root = selected
            save_settings(self.settings)
        return selected

    def _choose_for(self, key):
        try:
            store = CatalogStore()
        except (OSError, ValueError, FileNotFoundError) as exc:
            self._dialog("Codelijst niet beschikbaar", str(exc), kind="error")
            return
        selected = choose_codes(self, store, PICKER_FIELDS[key], self.field_labels[key][1],
                                set(self.selected_codes[key]), role_code=TYPES[self.type_var.get()]["code"])
        if selected is None:
            return
        previous = self.inserted_lines[key]
        current = [store.get(code).line for code in selected if store.get(code)]
        widget = self.widgets[key]
        merged = merge_selected_lines(widget.get("1.0", "end-1c"), previous, current)
        widget.delete("1.0", "end")
        widget.insert("1.0", merged)
        self.selected_codes[key] = selected
        self.inserted_lines[key] = current
        self._field_changed(key)

    def _add_combination(self):
        try:
            store = CatalogStore()
        except (OSError, ValueError, FileNotFoundError) as exc:
            self._dialog("Codelijst niet beschikbaar", str(exc), kind="error")
            return
        result = make_combination(self, store,
                                  is_leek=TYPES[self.type_var.get()]["code"] in ("LEEK", "ZZP"))
        if not result:
            return
        widget = self.widgets["COMBINATIES"]
        if widget.get("1.0", "end-1c").strip():
            widget.insert("end", "\n\n")
        widget.insert("end", result)
        widget.see("end")
        self._field_changed("COMBINATIES")

    def _dialog(self, title, message, kind="info", confirm=False):
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.configure(bg=BACKGROUND)
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.geometry("510x460" if len(message) > 500 else
                        "510x390" if len(message) > 260 else "510x275")
        dialog.minsize(510, 245)
        dialog.update_idletasks()
        dialog.geometry(f"+{self.winfo_rootx() + max(0, (self.winfo_width() - 510) // 2)}"
                        f"+{self.winfo_rooty() + max(0, (self.winfo_height() - dialog.winfo_height()) // 2)}")
        card = Card(dialog, padding=24, expand=True)
        card.pack(fill="both", expand=True, padx=15, pady=15)
        tk.Label(card.body, text=title, bg=SURFACE, fg=INK,
                 font=("Arial", 15, "bold")).pack(anchor="w", pady=(0, 13))
        label = tk.Label(card.body, text=message, bg=SURFACE,
                         fg=ERROR if kind == "error" else INK,
                         font=("Arial", 10), wraplength=430,
                         justify="left", anchor="nw")
        label.pack(fill="x", pady=(0, 15))
        result = {"value": False}

        def close(value=False):
            result["value"] = value
            dialog.grab_release()
            dialog.destroy()

        buttons = tk.Frame(card.body, bg=SURFACE)
        buttons.pack(side="bottom", anchor="e", fill="x")
        if confirm:
            ActionButton(buttons, "Nee, behouden", lambda: close(False),
                         width=145).pack(side="right", padx=(10, 0))
            ActionButton(buttons, "Ja, doorgaan", lambda: close(True),
                         primary=True, width=145).pack(side="right")
        else:
            ActionButton(buttons, "Sluiten", close, primary=True,
                         width=115).pack(side="right")
        dialog.protocol("WM_DELETE_WINDOW", lambda: close(False))
        dialog.bind("<Escape>", lambda _e: close(False))
        dialog.grab_set()
        dialog.wait_window()
        return result["value"]

    def _values(self):
        return {
            key: (widget.get("1.0", "end-1c") if isinstance(widget, tk.Text)
                  else widget.get()).strip()
            for key, widget in self.widgets.items()
        }

    def _validate(self, values):
        role = TYPES[self.type_var.get()]
        if role["code"] in ("LEEK", "ZZP"):
            chosen_skill_codes = set(re.findall(
                r"\bS\d{2,4}[A-Z]?\b",
                values["WERKZAAMHEDEN"] + "\n" + values["COMBINATIES"]
                + "\n" + values["BEVOEGDHEDEN"],
            ))
            if chosen_skill_codes - {"S02"}:
                self._focus_field("WERKZAAMHEDEN")
                raise ValueError("Deze registratie geeft geen elektrotechnische S-taken. "
                                 "Gebruik L-codes voor mechanische taken; S02 alleen voor geïnstrueerd normaal gebruik. "
                                 "Kies voor elektrisch werk ook een passende formele NEN 3140-aanwijzing.")
        for segment in re.split(r"(?=\bMachine:\s*)", values["COMBINATIES"]):
            if re.match(r"Machine:\s*M12\b", segment) and re.search(r"\bS\d{2,4}[A-Z]?\b", segment):
                self._focus_field("COMBINATIES")
                raise ValueError("M12 geldt uitsluitend voor mechanische taken (L-codes), niet voor elektrische S-taken.")
        missing = [label for _heading, fields in SECTIONS
                   for label, key, required, _multi in fields
                   if (required or key in role["required_fields"]) and not values[key]]
        if missing:
            first_key = next(key for _heading, fields in SECTIONS
                             for _label, key, required, _multi in fields
                             if (required or key in role["required_fields"]) and not values[key])
            self._focus_field(first_key)
            raise ValueError("Vul eerst de verplichte velden in:\n\n" + "\n".join("• " + label for label in missing))
        parsed = {}
        for key in DATE_FIELDS:
            if values[key]:
                try:
                    parsed[key] = valid_date(values[key])
                except ValueError:
                    self._focus_field(key)
                    label = next(label for _section, fields in SECTIONS
                                 for label, field_key, *_ in fields if field_key == key)
                    raise ValueError(f"Ongeldige datum bij {label}. Gebruik dd-mm-jjjj.") from None
        if parsed["GELDIG_TOT"] < parsed["INGANGSDATUM"]:
            self._focus_field("GELDIG_TOT")
            raise ValueError("'Geldig tot' mag niet vóór de ingangsdatum liggen.")
        selections_in_use = any(line in values[key].splitlines()
                                for key in ("INSTALLATIES", "WERKZAAMHEDEN")
                                for line in self.inserted_lines[key])
        if selections_in_use and not values["COMBINATIES"]:
            self._focus_field("COMBINATIES")
            raise ValueError("Je hebt machines of taken gekozen. Leg bij Bevoegdheden per machine "
                             "vast welke gekozen taken op welke machine zijn toegestaan.")

    def _focus_field(self, key):
        widget = self.widgets[key]
        widget.focus_set()
        self.error_keys.add(key)
        self.field_frames[key].set_error()
        self.update_idletasks()
        offset = widget.winfo_rooty() - self.content.winfo_rooty()
        total = max(1, self.content.winfo_height())
        self.scroll_canvas.yview_moveto(max(0, (offset - 45) / total))

    def clear_fields(self):
        for widget in self.widgets.values():
            if isinstance(widget, tk.Text):
                widget.delete("1.0", "end")
            else:
                widget.delete(0, "end")
        self.error_keys.clear()
        for key in PICKER_FIELDS:
            self.selected_codes[key] = []
            self.inserted_lines[key] = []
        for box in self.field_frames.values():
            box.state = "normal"
            box._draw()
        self._update_progress()
        self.scroll_canvas.yview_moveto(0)

    def create_document(self):
        values = self._values()
        try:
            self._validate(values)
            choice = TYPES[self.type_var.get()]
            template = template_path(choice["template"])
            if not template.is_file():
                raise FileNotFoundError(f"Sjabloon ontbreekt:\n{template}\n\nPlaats daar je eigen Word-sjabloon.")
            root = self._output_root()
            if not root:
                return
            mode = self.settings.export_mode
            destination, pdf = output_paths(
                root, choice["code"], values["VOLLEDIGE_NAAM"], values["INGANGSDATUM"],
                registration=choice["code"] == "LEEK",
            )
            if destination.resolve() == template.resolve():
                raise ValueError("Kies een andere bestandsnaam: het sjabloon mag niet worden overschreven.")
            existing = [path for path in (destination if mode != "pdf" else None,
                                           pdf if mode != "docx" else None)
                        if path is not None and path.exists()]
            if existing and not self._dialog(
                "Bestand bestaat al", "Deze bestanden bestaan al:\n" +
                "\n".join(str(path) for path in existing) + "\n\nOverschrijven?",
                confirm=True,
            ):
                return
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(suffix=".docx", prefix="nen3140_",
                                             dir=destination.parent, delete=False) as handle:
                temporary = Path(handle.name)
            try:
                generate_docx(template, temporary, document_values(values, choice))
                if mode in ("both", "docx"):
                    temporary.replace(destination)
                if mode == "docx":
                    self._dialog("Document gemaakt", f"Word-document opgeslagen:\n{destination}")
                    return

                # Word schrijft eerst een nieuwe tijdelijke PDF. Een bestaande
                # gescande of ondertekende PDF blijft zo intact bij een fout.
                with tempfile.NamedTemporaryFile(suffix=".pdf", prefix="nen3140_",
                                                 dir=destination.parent, delete=False) as handle:
                    temp_pdf = Path(handle.name)
                temp_pdf.unlink()
                try:
                    success, reason = export_pdf(destination if mode == "both" else temporary, temp_pdf)
                    if success:
                        temp_pdf.replace(pdf)
                finally:
                    temp_pdf.unlink(missing_ok=True)

                if success:
                    detail = (f"Word-document:\n{destination}\n\n" if mode == "both" else "")
                    self._dialog("Documenten gemaakt" if mode == "both" else "PDF gemaakt",
                                 detail + f"PDF:\n{pdf}")
                else:
                    if mode == "pdf":
                        fallback = destination
                        if fallback.exists():
                            fallback = destination.with_name(destination.stem + " (PDF niet beschikbaar).docx")
                            number = 2
                            while fallback.exists():
                                fallback = destination.with_name(destination.stem + f" (PDF niet beschikbaar {number}).docx")
                                number += 1
                        temporary.replace(fallback)
                        destination = fallback
                    self._dialog("Word-document gemaakt",
                                 f"Word-document opgeslagen:\n{destination}\n\nGeen PDF gemaakt. {reason}",
                                 kind="warning")
            finally:
                temporary.unlink(missing_ok=True)
        except (ValueError, FileNotFoundError, TemplateError) as exc:
            self._dialog("Controleer de gegevens", str(exc), kind="error")
        except Exception as exc:
            self._dialog("Document niet gemaakt", f"Er is iets misgegaan:\n{exc}", kind="error")


def self_test():
    """Genereer alle rollen en controleer op achtergebleven placeholders."""
    from docx import Document
    catalog = CatalogStore()
    for code in ("L01", "S03", "M01", "P01", "R01"):
        if not catalog.get(code) or not catalog.get(code).name:
            raise RuntimeError(f"Aanwijzingsmodel bevat geen bruikbare {code}.")
    combined = format_machine_permissions(catalog.get("M02"), [catalog.get("S03"), catalog.get("S02")])
    assert combined.startswith("Machine: M02 – Baxmatic\nBevoegdheden:\n• S03")
    from settings import AppSettings, load_settings, output_paths, save_settings
    template = template_path(next(iter(TYPES.values()))["template"])
    values = {key: "CONTROLE" for _heading, fields in SECTIONS
              for _label, key, _required, _multi in fields}
    values.update(INGANGSDATUM="01-01-2026", GELDIG_TOT="01-01-2027", COMBINATIES=combined)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "settings.json"
        save_settings(AppSettings(folder, "pdf"), path)
        assert load_settings(path).export_mode == "pdf"
        docx_path, pdf_path = output_paths(folder, "WV", "Mika van Eijken", "01-01-2026")
        assert docx_path.parent.name == "Mika van Eijken" and docx_path.parent.parent.name == "WV"
        assert pdf_path.suffix == ".pdf"
        for role in TYPES.values():
            result = Path(folder) / (role["code"] + ".docx")
            generate_docx(template, result, document_values(values, role))
            text = "\n".join(p.text for p in _all_paragraphs(Document(result)))
            if (result.stat().st_size < 1000 or "{{" in text or
                    document_values(values, role)["VERANTWOORDELIJKHEDEN"] not in text or
                    combined not in text):
                raise RuntimeError(f"Controle van het Word-document voor {role['code']} mislukt.")


def start():
    if sys.argv[1:] in (["--self-test"], ["--ui-smoke-test"]):
        try:
            if sys.argv[1:] == ["--self-test"]:
                self_test()
            else:
                from catalogus_venster import CatalogPicker
                app = Application()
                try:
                    for role in TYPES:
                        app.type_var.set(role)
                        app.update()
                        assert app.widgets and app.role_preview.get()
                        assert app.summary["role"].get() == TYPES[role]["code"]
                    app.widgets["VOLLEDIGE_NAAM"].insert(0, "Controlepersoon")
                    app.widgets["LOCATIE"].insert(0, "Emmeloord")
                    app._update_progress()
                    assert app.summary["person"].get() == "Controlepersoon"
                    assert app.summary["location"].get() == "Emmeloord"
                    picker = CatalogPicker(app, CatalogStore(), ("M",), "Machines")
                    picker.update()
                    assert picker.tree.exists("M01")
                    from types import SimpleNamespace
                    x, y, _w, h = picker.tree.bbox("M01")
                    picker._clicked(SimpleNamespace(x=110, y=y + h // 2))
                    assert "M01" not in picker.chosen  # klik op naam toont alleen uitleg
                    picker._clicked(SimpleNamespace(x=20, y=y + h // 2))
                    assert "M01" in picker.chosen  # rondje links kiest de code
                    picker._accept()
                    assert picker.answer == ["M01"]
                    picker = CatalogPicker(app, CatalogStore(), tuple("LSMPR"), "Alle codes beheren", manage_only=True)
                    picker.update()
                    assert picker.tree.exists("M01") and picker.tree.exists("R01")
                    picker._cancel()
                    app.geometry("900x620")
                    app.update()
                    assert app.scroll_canvas.winfo_width() > 400
                    app.geometry("760x520")
                    app.update()
                    assert app.primary_button.winfo_rooty() + app.primary_button.winfo_height() < app.winfo_screenheight()
                    app.geometry("1400x900")
                    app.update()
                    app.clear_fields()
                    assert app.summary["person"].get() == "Nog invullen"
                    with tempfile.TemporaryDirectory() as folder:
                        for key, value in {
                            "ORGANISATIE": "Eqraft", "VOLLEDIGE_NAAM": "Mika van Eijken",
                            "FUNCTIE": "Tijdelijke kracht", "INGANGSDATUM": "01-01-2026",
                            "GELDIG_TOT": "01-01-2027", "LOCATIE": "Emmeloord",
                            "INSTALLATIES": "M12 – Alle machines – uitsluitend mechanische taken",
                            "WERKZAAMHEDEN": "L01 – mechanisch werk",
                            "COMBINATIES": "Machine: M12 – Alle machines – uitsluitend mechanische taken\n"
                                           "Bevoegdheden:\n• L01 – mechanisch werk",
                            "BEVOEGDHEDEN": "Alleen mechanisch werk",
                            "NAAM_AANWIJZER": "Aanwijzer", "FUNCTIE_AANWIJZER": "WV",
                        }.items():
                            widget = app.widgets[key]
                            widget.insert("1.0" if isinstance(widget, tk.Text) else 0, value)
                        app.settings = AppSettings(folder, "pdf")
                        current_module = sys.modules[__name__]
                        old_export = current_module.export_pdf
                        old_dialog = app._dialog
                        current_module.export_pdf = lambda *_args: (False, "Word ontbreekt (test).")
                        app._dialog = lambda *_args, **_kwargs: True
                        try:
                            app.create_document()
                            destination, _ = output_paths(folder, "ZZP", "Mika van Eijken",
                                                          "01-01-2026")
                            assert destination.is_file()  # PDF-only valt terug op DOCX
                            app.settings.export_mode = "docx"
                            app.create_document()
                            assert destination.is_file() and destination.parent.parent.name == "ZZP"
                        finally:
                            current_module.export_pdf = old_export
                            app._dialog = old_dialog
                finally:
                    app.destroy()
        except Exception:
            log = Path(tempfile.gettempdir()) / "NEN3140_Aanwijzingen_fout.txt"
            log.write_text(traceback.format_exc(), encoding="utf-8")
            sys.exit(1)
        return
    try:
        Application().mainloop()
    except Exception:
        log = Path(tempfile.gettempdir()) / "NEN3140_Aanwijzingen_fout.txt"
        log.write_text(traceback.format_exc(), encoding="utf-8")
        # Werkt ook bij een executable zonder consolevenster.
        messagebox.showerror(APP_TITLE, f"Het programma kon niet starten.\n\nDetails: {log}")
        sys.exit(1)


if __name__ == "__main__":
    start()
