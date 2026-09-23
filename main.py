"""Startvenster voor het invullen van NEN 3140-aanwijzingssjablonen."""

from datetime import datetime
from pathlib import Path
import re
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import traceback

from config import APP_TITLE, DATE_FIELDS, SECTIONS, TYPES, template_path
from document_generator import TemplateError, export_pdf, generate_docx


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
        self.geometry("720x790")
        self.minsize(610, 540)
        self.widgets = {}
        self.type_var = tk.StringVar(value=next(iter(TYPES)))
        self._build()

    def _build(self):
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill="both", expand=True)

        select = ttk.Frame(outer)
        select.pack(fill="x", pady=(0, 12))
        ttk.Label(select, text="Type aanwijzing:").pack(side="left", padx=(0, 12))
        ttk.Combobox(select, textvariable=self.type_var, values=list(TYPES),
                     state="readonly", width=38).pack(side="left", fill="x", expand=True)

        area = ttk.Frame(outer)
        area.pack(fill="both", expand=True)
        canvas = tk.Canvas(area, highlightthickness=0)
        scrollbar = ttk.Scrollbar(area, orient="vertical", command=canvas.yview)
        content = ttk.Frame(canvas)
        content.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        window = canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for heading, fields in SECTIONS:
            frame = ttk.LabelFrame(content, text=heading, padding=10)
            frame.pack(fill="x", pady=(0, 10))
            frame.columnconfigure(1, weight=1)
            for row, (label, key, _required, multiline) in enumerate(fields):
                ttk.Label(frame, text=label + ":").grid(row=row, column=0, sticky="nw", padx=(0, 12), pady=4)
                if multiline:
                    widget = tk.Text(frame, height=3, width=40, wrap="word")
                else:
                    widget = ttk.Entry(frame)
                widget.grid(row=row, column=1, sticky="ew", pady=4)
                self.widgets[key] = widget

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(buttons, text="Document maken", command=self.create_document).pack(side="left")
        ttk.Button(buttons, text="Velden wissen", command=self.clear_fields).pack(side="left", padx=10)
        ttk.Button(buttons, text="Afsluiten", command=self.destroy).pack(side="right")

    def _values(self):
        return {
            key: (widget.get("1.0", "end-1c") if isinstance(widget, tk.Text)
                  else widget.get()).strip()
            for key, widget in self.widgets.items()
        }

    def _validate(self, values):
        missing = [label for _heading, fields in SECTIONS
                   for label, key, required, _multi in fields if required and not values[key]]
        if missing:
            raise ValueError("Vul eerst de verplichte velden in:\n\n" + "\n".join("• " + label for label in missing))
        parsed = {}
        for key in DATE_FIELDS:
            if values[key]:
                try:
                    parsed[key] = valid_date(values[key])
                except ValueError:
                    label = next(label for _section, fields in SECTIONS
                                 for label, field_key, *_ in fields if field_key == key)
                    raise ValueError(f"Ongeldige datum bij {label}. Gebruik dd-mm-jjjj.") from None
        if parsed["GELDIG_TOT"] < parsed["INGANGSDATUM"]:
            raise ValueError("'Geldig tot' mag niet vóór de ingangsdatum liggen.")

    def clear_fields(self):
        for widget in self.widgets.values():
            if isinstance(widget, tk.Text):
                widget.delete("1.0", "end")
            else:
                widget.delete(0, "end")

    def create_document(self):
        values = self._values()
        try:
            self._validate(values)
            choice = TYPES[self.type_var.get()]
            template = template_path(choice["template"])
            if not template.is_file():
                raise FileNotFoundError(f"Sjabloon ontbreekt:\n{template}\n\nPlaats daar je eigen Word-sjabloon.")
            filename = (f"Aanwijzing {choice['code']} - {safe_filename(values['VOLLEDIGE_NAAM'])}"
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
                generate_docx(template, temporary, values)
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
    """Controleren dat de ingebundelde code en het sjabloon echt samenwerken."""
    template = template_path(TYPES["Installatieverantwoordelijke (IV)"]["template"])
    values = {key: "CONTROLE" for _heading, fields in SECTIONS
              for _label, key, _required, _multi in fields}
    values.update(INGANGSDATUM="01-01-2026", GELDIG_TOT="01-01-2027",
                  DATUM_AANWIJZER="01-01-2026", DATUM_AANGEWEZENE="01-01-2026")
    with tempfile.TemporaryDirectory() as folder:
        result = Path(folder) / "controle.docx"
        generate_docx(template, result, values)
        if result.stat().st_size < 1000:
            raise RuntimeError("Het gemaakte Word-document is niet geldig.")


def start():
    if sys.argv[1:] == ["--self-test"]:
        try:
            self_test()
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
