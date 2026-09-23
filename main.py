"""Startvenster voor het invullen van NEN 3140-aanwijzingssjablonen."""

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

INK = "#181818"
MUTED = "#61656B"
YELLOW = "#FFDE00"
PAPER = "#FFFFFF"
CANVAS = "#F3F4F5"

SECTION_TIPS = {
    "Gegevens persoon": "Wie wordt aangewezen en voor welke periode?",
    "Omvang en werkzaamheden": "Noem de locatie, de installatiedelen en de concrete werkzaamheden.",
    "Bevoegdheden en grenzen": "Schrijf op wat deze persoon daadwerkelijk mag doen en waar de grens ligt.",
    "Namens de organisatie": "Wie geeft deze aanwijzing af? Vul ook plaats en datum in.",
    "Ondertekening betrokkene": "Datum waarop de betrokkene het document ondertekent.",
}

FIELD_TIPS = {
    "INSTALLATIES": "Bijvoorbeeld gebouwinstallaties, een machine of afzonderlijke besturingskasten.",
    "VERANTWOORDELIJKHEIDSGEBIED": "Baken af welke installaties en locaties bij deze persoon horen.",
    "WERKZAAMHEDEN": "Bij VOP: noem elke toegestane taak en bijbehorende instructie afzonderlijk.",
    "BEVOEGDHEDEN": "Leg eigen bevoegdheden vast; het automatische rolkader staat apart in het document.",
    "BEPERKINGEN": "Denk aan uitgesloten werkzaamheden, toezicht en afspraken bij afwijkingen.",
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
        self.geometry("1020x840")
        self.minsize(750, 590)
        self.configure(background=CANVAS)
        self.widgets = {}
        self.field_labels = {}
        self.logo_image = None
        self.type_var = tk.StringVar(value=next(iter(TYPES)))
        self.role_preview = tk.StringVar()
        self.progress_text = tk.StringVar()
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("Eq.TCombobox", padding=9, fieldbackground=PAPER,
                             foreground=INK, arrowcolor=INK, bordercolor="#C9CDD2")
        self.style.map("Eq.TCombobox", fieldbackground=[("readonly", PAPER)],
                       selectbackground=[("readonly", PAPER)], selectforeground=[("readonly", INK)])
        self.style.configure("Eq.TEntry", padding=9, fieldbackground=PAPER,
                             foreground=INK, bordercolor="#C9CDD2", lightcolor=YELLOW)
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
        banner = tk.Frame(self, bg=PAPER, padx=27, pady=12)
        banner.pack(fill="x")
        logo = resource_path("assets/eqraft_logo.png")
        if logo.is_file():
            try:
                self.logo_image = tk.PhotoImage(file=str(logo)).subsample(2, 2)
                tk.Label(banner, image=self.logo_image, bg=PAPER).pack(side="left", padx=(0, 28))
            except tk.TclError:
                pass
        if self.logo_image is None:
            tk.Label(banner, text="EQRAFT", font=("Segoe UI", 18, "bold"),
                     fg=INK, bg=PAPER).pack(side="left", padx=(0, 28))
        title = tk.Frame(banner, bg=PAPER)
        title.pack(side="left")
        tk.Label(title, text=APP_TITLE, font=("Segoe UI", 17, "bold"),
                 fg=INK, bg=PAPER).pack(anchor="w")
        tk.Label(title, text="Maak een aanwijzing op basis van het Eqraft Word-sjabloon",
                 font=("Segoe UI", 9), fg=MUTED, bg=PAPER).pack(anchor="w", pady=(2, 0))
        tk.Frame(self, bg=YELLOW, height=4).pack(fill="x")

        outer = tk.Frame(self, bg=CANVAS, padx=28, pady=19)
        outer.pack(fill="both", expand=True)

        select = tk.Frame(outer, bg=PAPER, padx=18, pady=13,
                          highlightthickness=1, highlightbackground="#E3E5E7")
        select.pack(fill="x", pady=(0, 12))
        tk.Label(select, text="1  KIES DE AANWIJZING", font=("Segoe UI", 10, "bold"),
                 bg=PAPER, fg=INK).pack(anchor="w", pady=(0, 6))
        ttk.Combobox(select, textvariable=self.type_var, values=list(TYPES), style="Eq.TCombobox",
                     state="readonly", font=("Segoe UI", 10)).pack(fill="x")
        tk.Label(select, textvariable=self.role_preview, justify="left", wraplength=860,
                 bg="#FFF8D4", fg=INK, anchor="w", padx=12, pady=10,
                 font=("Segoe UI", 9)).pack(fill="x", pady=(11, 0))

        tk.Label(outer, text="2  VUL DE GEGEVENS IN", font=("Segoe UI", 10, "bold"),
                 bg=CANVAS, fg=INK).pack(anchor="w", pady=(3, 9))
        area = tk.Frame(outer, bg=CANVAS)
        area.pack(fill="both", expand=True)
        canvas = tk.Canvas(area, bg=CANVAS, highlightthickness=0)
        scrollbar = ttk.Scrollbar(area, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=CANVAS)
        self.scroll_canvas, self.content = canvas, content
        content.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        window = canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        for number, (heading, fields) in enumerate(SECTIONS, start=1):
            card = tk.Frame(content, bg=PAPER, highlightbackground="#E3E5E7",
                            highlightthickness=1, padx=19, pady=14)
            card.pack(fill="x", pady=(0, 13), padx=(0, 7))
            tk.Label(card, text=f"{number:02d}  {heading}", bg=PAPER, fg=INK,
                     font=("Segoe UI", 11, "bold")).pack(anchor="w")
            tk.Label(card, text=SECTION_TIPS[heading], bg=PAPER, fg=MUTED,
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 12))
            frame = tk.Frame(card, bg=PAPER)
            frame.pack(fill="x")
            frame.columnconfigure(0, weight=1, uniform="fields")
            frame.columnconfigure(1, weight=1, uniform="fields")
            row = col = 0
            for label, key, required, multiline in fields:
                if multiline and col:
                    row, col = row + 1, 0
                box = tk.Frame(frame, bg=PAPER)
                box.grid(row=row, column=0 if multiline else col,
                         columnspan=2 if multiline else 1, sticky="ew",
                         padx=(0, 0 if multiline or col else 14), pady=(0, 12))
                label_widget = tk.Label(box, text=label + ":", bg=PAPER,
                                        fg=INK, anchor="w", font=("Segoe UI", 9, "bold"))
                label_widget.pack(anchor="w", pady=(0, 5))
                self.field_labels[key] = (label_widget, label, required)
                if multiline:
                    widget = tk.Text(box, height=3, wrap="word", relief="solid",
                                     borderwidth=1, highlightthickness=1,
                                     highlightbackground="#C9CDD2", highlightcolor=YELLOW,
                                     font=("Segoe UI", 10), bg=PAPER, fg=INK,
                                     insertbackground=INK, padx=8, pady=6)
                    widget.bind("<KeyRelease>", self._update_progress)
                else:
                    widget = ttk.Entry(box, style="Eq.TEntry", font=("Segoe UI", 10))
                    widget.bind("<KeyRelease>", self._update_progress)
                widget.pack(fill="x")
                self.widgets[key] = widget
                if key in FIELD_TIPS:
                    tk.Label(box, text=FIELD_TIPS[key], bg=PAPER, fg=MUTED,
                             anchor="w", font=("Segoe UI", 8),
                             wraplength=770).pack(anchor="w", pady=(4, 0))
                if multiline:
                    row += 1
                elif col:
                    row, col = row + 1, 0
                else:
                    col = 1

        buttons = tk.Frame(outer, bg=CANVAS)
        buttons.pack(fill="x", pady=(12, 0))
        tk.Label(buttons, text="3  CONTROLEER EN MAAK HET DOCUMENT",
                 bg=CANVAS, fg=INK, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 8))
        actions = tk.Frame(buttons, bg=CANVAS)
        actions.pack(fill="x")
        tk.Button(actions, text="Document maken", command=self.create_document,
                  bg=YELLOW, fg=INK, activebackground="#EFCF00", cursor="hand2",
                  relief="flat", padx=22, pady=11, font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Button(actions, text="Velden wissen", command=self.clear_fields,
                  bg=PAPER, fg=INK, cursor="hand2", relief="flat",
                  padx=15, pady=11, font=("Segoe UI", 9)).pack(side="left", padx=10)
        tk.Button(actions, text="Afsluiten", command=self.destroy,
                  bg=CANVAS, fg=INK, relief="flat", padx=12, pady=11).pack(side="right")
        tk.Label(buttons, textvariable=self.progress_text, bg=CANVAS,
                 fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(9, 0))

    def _on_mousewheel(self, event):
        if self.winfo_containing(event.x_root, event.y_root) and event.delta:
            self.scroll_canvas.yview_scroll(-int(event.delta / 120), "units")

    def _update_progress(self, *_args):
        role = TYPES[self.type_var.get()]
        required = {key for _, fields in SECTIONS for _, key, mandatory, _ in fields
                    if mandatory or key in role["required_fields"]}
        values = self._values()
        complete = sum(bool(values[key]) for key in required)
        self.progress_text.set(f"{complete} van {len(required)} verplichte velden ingevuld  ·  "
                               "Het Word-document wordt op een zelfgekozen plek opgeslagen.")

    def _update_role(self, *_args):
        role = TYPES[self.type_var.get()]
        for key, (widget, label, required) in self.field_labels.items():
            widget.configure(text=label + (" *" if required or key in role["required_fields"] else "") + ":")
        prefix = "Instructieregistratie" if role["code"] == "LEEK" else "Aanwijzing"
        extra = (" Vul de specifiek geïnstrueerde werkzaamheden in."
                 if role["code"] == "VOP" else "")
        self.role_preview.set(
            f"{prefix}: {role['role']}. Het rolkader en de verantwoordelijkheden worden "
            f"automatisch ingevuld. Leg de persoonlijke bevoegdheden, werkzaamheden en "
            f"beperkingen zelf concreet vast.{extra}"
        )
        self._update_progress()

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
            if destination.exists() and not messagebox.askyesno(
                "Bestand bestaat al", f"Dit document bestaat al:\n{destination}\n\nOverschrijven?"
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
            if pdf.exists() and not messagebox.askyesno(
                "PDF bestaat al", f"Deze PDF bestaat al:\n{pdf}\n\nOverschrijven?"
            ):
                messagebox.showinfo("Document gemaakt", f"Word-document opgeslagen:\n{destination}\n\nPDF overgeslagen.")
                return

            success, reason = export_pdf(destination, pdf)
            if success:
                messagebox.showinfo("Documenten gemaakt", f"Word-document:\n{destination}\n\nPDF:\n{pdf}")
            else:
                messagebox.showwarning("Word-document gemaakt", f"Word-document opgeslagen:\n{destination}\n\nGeen PDF gemaakt. {reason}")
        except (ValueError, FileNotFoundError, TemplateError) as exc:
            messagebox.showerror("Controleer de gegevens", str(exc))
        except Exception as exc:
            messagebox.showerror("Document niet gemaakt", f"Er is iets misgegaan:\n{exc}")


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
                        app.update_idletasks()
                        assert app.widgets and app.role_preview.get()
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
