"""Eqraft-formulier voor het invullen van NEN 3140-aanwijzingssjablonen."""

from datetime import datetime
from pathlib import Path
import re
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import traceback

from config import APP_TITLE, DATE_FIELDS, SECTIONS, TYPES, document_values, template_path, resource_path
from document_generator import TemplateError, _all_paragraphs, export_pdf, generate_docx
from ui_components import (ActionButton, BACKGROUND, BORDER, Card, DARK, ERROR,
                           INK, InputBox, MUTED, NavItem, SelectBox, SIDEBAR,
                           SURFACE, SummaryTile, WHITE, YELLOW, rounded_rect)


SECTION_TIPS = {
    "Gegevens persoon": "Vul de persoon en de periode van deze aanwijzing in.",
    "Omvang en werkzaamheden": "Baken locatie, installaties en de toegestane werkzaamheden concreet af.",
    "Bevoegdheden en grenzen": "Leg hier vast wat deze persoon mag doen en welke grenzen gelden.",
    "Namens de organisatie": "Gegevens van degene die de aanwijzing afgeeft.",
    "Ondertekening betrokkene": "De datum waarop de betrokken persoon ondertekent.",
}

FIELD_TIPS = {
    "INSTALLATIES": "Welke machine, gebouwinstallatie of installatiedelen vallen hieronder?",
    "VERANTWOORDELIJKHEIDSGEBIED": "Waar begint en eindigt de verantwoordelijkheid van deze persoon?",
    "WERKZAAMHEDEN": "Voor VOP: beschrijf elke toegestane taak en de gegeven instructie.",
    "BEVOEGDHEDEN": "Vul persoonlijke toestemming in. Het automatische rolkader staat apart in Word.",
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
        self.logo_image = None
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

        heading = tk.Frame(main, bg=BACKGROUND, padx=30, pady=19)
        heading.pack(fill="x")
        tk.Label(heading, text="EQRAFT  /  NEN 3140", font=("Arial", 9, "bold"),
                 bg=BACKGROUND, fg="#6A6040").pack(anchor="w", pady=(0, 7))
        tk.Label(heading, text="Aanwijzing aanmaken", font=("Arial", 21, "bold"),
                 bg=BACKGROUND, fg=INK).pack(anchor="w")
        tk.Label(heading, text="Leg de aanwijzing duidelijk vast en maak daarna het Word-document.",
                 font=("Arial", 10), bg=BACKGROUND, fg=MUTED).pack(anchor="w", pady=(4, 0))

        overview = Card(main, padding=17)
        overview.pack(fill="x", padx=28, pady=(0, 16))
        top = overview.body
        tk.Label(top, text="HUIDIGE AANWIJZING", bg=SURFACE, fg=INK,
                 font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 12))
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
        tk.Frame(top, bg=BORDER, height=1).pack(fill="x", pady=(14, 10))
        tk.Label(top, textvariable=self.summary_status, bg=SURFACE, fg=INK,
                 font=("Arial", 9)).pack(anchor="w")

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

        role_card = Card(content, padding=24)
        role_card.pack(fill="x", pady=(0, 18))
        tk.Label(role_card.body, text="01  Type aanwijzing", bg=SURFACE, fg=INK,
                 font=("Arial", 13, "bold")).pack(anchor="w")
        tk.Label(role_card.body, text="Kies de rol. De bijbehorende verantwoordelijkheden worden automatisch ingevuld.",
                 bg=SURFACE, fg=MUTED, font=("Arial", 9),
                 wraplength=720, justify="left").pack(anchor="w", pady=(4, 11))
        selection = SelectBox(role_card.body, self.type_var, list(TYPES))
        selection.pack(fill="x")
        self.role_note = tk.Label(role_card.body, textvariable=self.role_preview,
                                  bg=SURFACE, fg=MUTED, font=("Arial", 9),
                                  anchor="w", justify="left", wraplength=700)
        self.role_note.pack(fill="x", pady=(9, 0))

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
                label_widget = tk.Label(field, text=label, bg=SURFACE, fg=INK,
                                        font=("Arial", 9, "bold"), anchor="w",
                                        wraplength=260, justify="left")
                label_widget.pack(anchor="w", pady=(0, 7))
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
                logo_card = tk.Canvas(sidebar, width=192, height=80, bg=SIDEBAR,
                                      highlightthickness=0, borderwidth=0)
                rounded_rect(logo_card, 0, 0, 192, 80, 12, WHITE)
                logo_card.create_image(96, 40, image=self.logo_image)
                logo_card.pack(anchor="w", padx=8, pady=(12, 29))
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
        if role["code"] == "LEEK":
            self.role_preview.set("Dit is een instructieregistratie en geen elektrotechnische aanwijzing. "
                                  "Leg het toegestane normale gebruik concreet vast.")
        else:
            self.role_preview.set("De rolteksten worden automatisch ingevuld. "
                                  "Vul persoonlijke taken, bevoegdheden en grenzen hieronder in.")
        self._update_progress()

    def _show_guide(self):
        self._dialog(
            "Zo werkt het",
            "1. Kies IV, WV, VP, VOP of Leek. Leek is een instructieregistratie.\n\n"
            "2. Vul alle velden met * in. Beschrijf installaties, werkzaamheden en persoonlijke "
            "bevoegdheden concreet. De rolteksten worden automatisch ingevuld.\n\n"
            "3. Klik op Document maken en kies een opslagplaats. Controleer het Word-document "
            "voordat het wordt ondertekend. Staat Microsoft Word op deze computer, dan wordt "
            "ook een PDF gemaakt.",
            kind="info",
        )

    def _dialog(self, title, message, kind="info", confirm=False):
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.configure(bg=BACKGROUND)
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.geometry("510x390" if len(message) > 260 else "510x275")
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
            prefix = "Registratie" if choice["code"] == "LEEK" else "Aanwijzing"
            filename = (f"{prefix} {choice['code']} - {safe_filename(values['VOLLEDIGE_NAAM'])}"
                        f" - {values['INGANGSDATUM']}.docx")
            selected = filedialog.asksaveasfilename(
                title="Sla het aanwijzingsformulier op", defaultextension=".docx",
                initialfile=filename, filetypes=[("Word-document", "*.docx")],
            )
            if not selected:
                return
            destination = Path(selected)
            if destination.resolve() == template.resolve():
                raise ValueError("Kies een andere bestandsnaam: het sjabloon mag niet worden overschreven.")
            if destination.exists() and not self._dialog(
                "Bestand bestaat al", f"Dit document bestaat al:\n{destination}\n\nOverschrijven?",
                confirm=True
            ):
                return

            # Eerst volledig in een tijdelijk bestand maken. Fouten laten een
            # reeds bestaand document daardoor intact.
            with tempfile.NamedTemporaryFile(suffix=".docx", prefix="nen3140_",
                                             dir=destination.parent, delete=False) as handle:
                temporary = Path(handle.name)
            try:
                generate_docx(template, temporary, document_values(values, choice))
                temporary.replace(destination)
            finally:
                temporary.unlink(missing_ok=True)

            pdf = destination.with_suffix(".pdf")
            if pdf.exists() and not self._dialog(
                "PDF bestaat al", f"Deze PDF bestaat al:\n{pdf}\n\nOverschrijven?",
                confirm=True
            ):
                self._dialog("Document gemaakt", f"Word-document opgeslagen:\n{destination}\n\nPDF overgeslagen.")
                return

            success, reason = export_pdf(destination, pdf)
            if success:
                self._dialog("Documenten gemaakt", f"Word-document:\n{destination}\n\nPDF:\n{pdf}")
            else:
                self._dialog("Word-document gemaakt", f"Word-document opgeslagen:\n{destination}\n\nGeen PDF gemaakt. {reason}", kind="warning")
        except (ValueError, FileNotFoundError, TemplateError) as exc:
            self._dialog("Controleer de gegevens", str(exc), kind="error")
        except Exception as exc:
            self._dialog("Document niet gemaakt", f"Er is iets misgegaan:\n{exc}", kind="error")


def self_test():
    """Genereer alle rollen en controleer op achtergebleven placeholders."""
    from docx import Document
    template = template_path(next(iter(TYPES.values()))["template"])
    values = {key: "CONTROLE" for _heading, fields in SECTIONS
              for _label, key, _required, _multi in fields}
    values.update(INGANGSDATUM="01-01-2026", GELDIG_TOT="01-01-2027")
    with tempfile.TemporaryDirectory() as folder:
        for role in TYPES.values():
            result = Path(folder) / (role["code"] + ".docx")
            generate_docx(template, result, document_values(values, role))
            text = "\n".join(p.text for p in _all_paragraphs(Document(result)))
            if result.stat().st_size < 1000 or "{{" in text or role["responsibilities"] not in text:
                raise RuntimeError(f"Controle van het Word-document voor {role['code']} mislukt.")


def start():
    if sys.argv[1:] in (["--self-test"], ["--ui-smoke-test"]):
        try:
            if sys.argv[1:] == ["--self-test"]:
                self_test()
            else:
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
