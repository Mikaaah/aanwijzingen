"""Startvenster voor het invullen van NEN 3140-aanwijzingssjablonen."""

from datetime import datetime
from pathlib import Path
import re
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import traceback

from config import APP_TITLE, DATE_FIELDS, SECTIONS, TYPES, document_values, template_path
from document_generator import TemplateError, _all_paragraphs, export_pdf, generate_docx


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
        self.geometry("820x820")
        self.minsize(650, 550)
        self.configure(background="#FFFFFF")
        self.widgets = {}
        self.field_labels = {}
        self.type_var = tk.StringVar(value=next(iter(TYPES)))
        self.role_preview = tk.StringVar()
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("Eq.TCombobox", padding=6, fieldbackground="#FFFFFF")
        self.style.configure("Eq.TEntry", padding=5, fieldbackground="#FFFFFF")
        self._build()
        self.type_var.trace_add("write", self._update_role)
        self._update_role()

    def _build(self):
        banner = tk.Frame(self, bg="#121212", height=82)
        banner.pack(fill="x")
        banner.pack_propagate(False)
        tk.Frame(banner, bg="#FFDE00", width=8).pack(side="left", fill="y")
        tk.Label(banner, text="EQRAFT", font=("Segoe UI", 18, "bold"),
                 fg="#FFDE00", bg="#121212").pack(side="left", padx=(20, 20))
        tk.Label(banner, text=APP_TITLE, font=("Segoe UI", 15, "bold"),
                 fg="#FFFFFF", bg="#121212").pack(side="left")

        outer = tk.Frame(self, bg="#FFFFFF", padx=22, pady=18)
        outer.pack(fill="both", expand=True)

        select = tk.Frame(outer, bg="#FFFFFF")
        select.pack(fill="x", pady=(0, 9))
        tk.Label(select, text="Type aanwijzing / registratie", font=("Segoe UI", 10, "bold"),
                 bg="#FFFFFF", fg="#171717").pack(anchor="w", pady=(0, 5))
        ttk.Combobox(select, textvariable=self.type_var, values=list(TYPES), style="Eq.TCombobox",
                     state="readonly", width=45).pack(fill="x")
        tk.Label(outer, textvariable=self.role_preview, justify="left", wraplength=730,
                 bg="#FFF7CD", fg="#202020", anchor="w", padx=12, pady=9,
                 font=("Segoe UI", 9)).pack(fill="x", pady=(0, 12))

        area = tk.Frame(outer, bg="#FFFFFF")
        area.pack(fill="both", expand=True)
        canvas = tk.Canvas(area, bg="#FFFFFF", highlightthickness=0)
        scrollbar = ttk.Scrollbar(area, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg="#FFFFFF")
        content.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        window = canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(-int(event.delta / 120), "units"))

        for heading, fields in SECTIONS:
            card = tk.Frame(content, bg="#FFFFFF", highlightbackground="#E0E0E0",
                            highlightthickness=1, padx=15, pady=12)
            card.pack(fill="x", pady=(0, 12), padx=(0, 5))
            tk.Label(card, text=heading.upper(), bg="#FFFFFF", fg="#111111",
                     font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 8))
            tk.Frame(card, bg="#FFDE00", height=3).pack(fill="x", pady=(0, 9))
            frame = tk.Frame(card, bg="#FFFFFF")
            frame.pack(fill="x")
            frame.columnconfigure(1, weight=1)
            for row, (label, key, _required, multiline) in enumerate(fields):
                label_widget = tk.Label(frame, text=label + ":",
                                        bg="#FFFFFF", fg="#202020", anchor="w",
                                        font=("Segoe UI", 9))
                label_widget.grid(row=row, column=0, sticky="nw", padx=(0, 14), pady=5)
                self.field_labels[key] = (label_widget, label, _required)
                if multiline:
                    widget = tk.Text(frame, height=3, width=42, wrap="word",
                                     relief="solid", borderwidth=1, font=("Segoe UI", 10),
                                     bg="#FFFFFF", fg="#111111", insertbackground="#111111")
                else:
                    widget = ttk.Entry(frame, style="Eq.TEntry", font=("Segoe UI", 10))
                widget.grid(row=row, column=1, sticky="ew", pady=5)
                self.widgets[key] = widget

        buttons = tk.Frame(outer, bg="#FFFFFF")
        buttons.pack(fill="x", pady=(12, 0))
        tk.Button(buttons, text="Document maken", command=self.create_document,
                  bg="#FFDE00", fg="#111111", activebackground="#F2D000",
                  relief="flat", padx=18, pady=9, font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Button(buttons, text="Velden wissen", command=self.clear_fields,
                  bg="#FFFFFF", fg="#222222", relief="flat", padx=12, pady=9).pack(side="left", padx=10)
        tk.Button(buttons, text="Afsluiten", command=self.destroy,
                  bg="#FFFFFF", fg="#222222", relief="flat", padx=12, pady=9).pack(side="right")

    def _update_role(self, *_args):
        role = TYPES[self.type_var.get()]
        for key, (widget, label, required) in self.field_labels.items():
            widget.configure(text=label + (" *" if required or key in role["required_fields"] else "") + ":")
        prefix = "Instructieregistratie" if role["code"] == "LEEK" else "Aanwijzing"
        extra = (" Vul de specifiek geïnstrueerde werkzaamheden in."
                 if role["code"] == "VOP" else "")
        self.role_preview.set(
            f"{prefix}: {role['role']}. De verantwoordelijkheden worden automatisch ingevuld. "
            f"Leg bevoegdheden en grenzen zelf concreet vast.{extra}"
        )

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
