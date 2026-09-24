"""Keuzevenster met uitleg per code en beheer van eigen aanvullingen."""

import tkinter as tk
from tkinter import messagebox, ttk

from catalogus import CATEGORIES, CatalogStore
from ui_components import BACKGROUND, BORDER, INK, MUTED, SURFACE, WHITE, YELLOW, ActionButton, Card


class CatalogPicker(tk.Toplevel):
    def __init__(self, parent, store: CatalogStore, categories: tuple[str, ...],
                 title: str, initial: set[str] | None = None, role_code: str = ""):
        super().__init__(parent)
        self.store, self.categories, self.chosen = store, categories, set(initial or ())
        self.role_code = role_code
        self.answer = None
        self.title(title)
        width = min(920, max(690, parent.winfo_screenwidth() - 100))
        height = min(690, max(500, parent.winfo_screenheight() - 140))
        self.geometry(f"{width}x{height}+{parent.winfo_rootx()+35}+{parent.winfo_rooty()+25}")
        self.minsize(690, 500)
        self.configure(bg=BACKGROUND)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda _e: self._cancel())
        self._build(title)
        self._refresh()
        self.grab_set()

    def _build(self, title):
        card = Card(self, padding=18, expand=True)
        card.pack(fill="both", expand=True, padx=12, pady=12)
        body = card.body
        tk.Label(body, text=title, bg=SURFACE, fg=INK,
                 font=("Arial", 16, "bold")).pack(anchor="w")
        tk.Label(body, text="Klik op een regel om deze aan of uit te zetten. De uitleg staat rechts; code en benaming komen in het formulier.",
                 bg=SURFACE, fg=MUTED, font=("Arial", 9),
                 wraplength=760, justify="left").pack(anchor="w", pady=(4, 10))

        search_row = tk.Frame(body, bg=SURFACE)
        search_row.pack(fill="x", pady=(0, 9))
        tk.Label(search_row, text="Zoeken", bg=SURFACE, fg=INK,
                 font=("Arial", 9, "bold")).pack(side="left", padx=(0, 12))
        self.search = tk.StringVar()
        search = tk.Entry(search_row, textvariable=self.search, bg=WHITE,
                          fg=INK, font=("Arial", 10), relief="solid", bd=1)
        search.pack(side="left", fill="x", expand=True, ipady=6)
        self.search.trace_add("write", lambda *_args: self._refresh())

        middle = tk.Frame(body, bg=SURFACE)
        middle.pack(fill="both", expand=True)
        listing = tk.Frame(middle, bg=SURFACE)
        listing.pack(side="left", fill="both", expand=True, padx=(0, 12))
        self.tree = ttk.Treeview(listing, columns=("check", "code", "name"), show="headings",
                                 selectmode="browse", height=14)
        self.tree.heading("check", text="Kies")
        self.tree.heading("code", text="Code")
        self.tree.heading("name", text="Benaming")
        self.tree.column("check", width=43, minwidth=43, stretch=False, anchor="center")
        self.tree.column("code", width=74, minwidth=74, stretch=False)
        self.tree.column("name", width=400, minwidth=200)
        scrollbar = ttk.Scrollbar(listing, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<Button-1>", self._clicked)
        self.tree.bind("<space>", self._toggle_focused)

        detail = tk.Frame(middle, bg="#F0F1F1", highlightbackground=BORDER,
                          highlightthickness=1, padx=13, pady=13, width=240)
        detail.pack(side="right", fill="y")
        detail.pack_propagate(False)
        self.detail_title = tk.Label(detail, text="Selecteer een code", bg="#F0F1F1",
                                     fg=INK, font=("Arial", 11, "bold"),
                                     wraplength=205, justify="left", anchor="nw")
        self.detail_title.pack(fill="x", anchor="w")
        self.detail = tk.Label(detail, text="De voorwaarden uit het aanwijzingsmodel verschijnen hier.",
                               bg="#F0F1F1", fg=MUTED, font=("Arial", 9),
                               wraplength=205, justify="left", anchor="nw")
        self.detail.pack(fill="x", pady=(12, 0))

        tk.Label(body, text="Beschikbare codes zijn voorstellen; leg de toegestane taak, machine, procedure en voorwaarden per combinatie vast.",
                 bg=SURFACE, fg=MUTED, font=("Arial", 9),
                 wraplength=780, justify="left").pack(anchor="w", pady=(12, 6))
        buttons = tk.Frame(body, bg=SURFACE)
        buttons.pack(fill="x")
        ActionButton(buttons, "Toevoegen", self._add, width=114).pack(side="left")
        ActionButton(buttons, "Bewerken", self._edit, width=105).pack(side="left", padx=(7, 0))
        ActionButton(buttons, "Verwijderen", self._delete, width=112).pack(side="left", padx=(7, 0))
        ActionButton(buttons, "Overnemen", self._accept, primary=True, width=130).pack(side="right")
        ActionButton(buttons, "Annuleren", self._cancel, width=110).pack(side="right", padx=(0, 7))

    def _refresh(self):
        if not hasattr(self, "tree"):
            return
        term = self.search.get().casefold().strip()
        focused = self.tree.focus()
        children = self.tree.get_children()
        if children:
            self.tree.delete(*children)
        for item in self.store.items(self.categories):
            if (self.role_code == "LEEK" and item.category == "S"
                    and item.code != "S02"):
                continue
            if term and term not in (item.code + " " + item.name + " " + item.explanation).casefold():
                continue
            self.tree.insert("", "end", iid=item.code,
                             values=("✓" if item.code in self.chosen else "", item.code, item.name))
        if focused and self.tree.exists(focused):
            self.tree.focus(focused)
        self._show_detail()

    def _clicked(self, event):
        code = self.tree.identify_row(event.y)
        if code:
            self.tree.focus(code)
            self._toggle(code)
        return "break"

    def _toggle_focused(self, _event):
        self._toggle(self.tree.focus())
        return "break"

    def _toggle(self, code):
        if not code:
            return
        item = self.store.get(code)
        if not item.selectable:
            messagebox.showinfo("Rubriektitel", "S01 is alleen een rubriektitel. Kies een concrete taak uit L01–L08.", parent=self)
            return
        if code in self.chosen:
            self.chosen.remove(code)
        else:
            self.chosen.add(code)
        self.tree.set(code, "check", "✓" if code in self.chosen else "")
        self._show_detail()

    def _show_detail(self):
        focused = self.tree.focus()
        item = self.store.get(focused) if focused else None
        if item:
            self.detail_title.configure(text=item.line)
            category_name = CATEGORIES[item.category][1]
            self.detail.configure(text=f"{category_name}\n\n{item.explanation}\n\n"
                                       + ("Eigen toevoeging" if item.custom else "Uit het aanwijzingsmodel"))
        else:
            self.detail_title.configure(text="Selecteer een code")
            self.detail.configure(text="De voorwaarden uit het aanwijzingsmodel verschijnen hier.")

    def _selected_item(self):
        focused = self.tree.focus()
        return self.store.get(focused) if focused else None

    def _next_code(self, category):
        numbers = [int(item.code[1:].rstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
                   for item in self.store.items((category,))]
        next_number = max(numbers, default=0) + 1
        return f"{category}{next_number:02d}"

    def _add(self):
        self._editor(None)

    def _edit(self):
        item = self._selected_item()
        if item is None or not item.custom:
            messagebox.showinfo("Bewerken", "Selecteer eerst een eigen toevoeging. De vaste lijst komt uit het aanwijzingsmodel.", parent=self)
            return
        self._editor(item)

    def _delete(self):
        item = self._selected_item()
        if item is None or not item.custom:
            messagebox.showinfo("Verwijderen", "Alleen een eigen toevoeging kan worden verwijderd.", parent=self)
            return
        if not messagebox.askyesno("Eigen toevoeging verwijderen", f"{item.line} verwijderen uit de lijst?", parent=self):
            return
        try:
            self.store.delete(item.code)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Niet opgeslagen", str(exc), parent=self)
            return
        self.chosen.discard(item.code)
        self._refresh()

    def _editor(self, item):
        window = tk.Toplevel(self)
        window.title("Eigen code bewerken" if item else "Eigen code toevoegen")
        window.configure(bg=BACKGROUND)
        window.geometry(f"520x430+{self.winfo_rootx()+55}+{self.winfo_rooty()+70}")
        window.minsize(490, 410)
        window.transient(self)
        category = tk.StringVar(value=item.category if item else self.categories[0])
        code = tk.StringVar(value=item.code if item else self._next_code(category.get()))
        name = tk.StringVar(value=item.name if item else "")
        card = Card(window, padding=21, expand=True)
        card.pack(fill="both", expand=True, padx=12, pady=12)
        box = card.body
        tk.Label(box, text="Eigen aanvulling", bg=SURFACE, fg=INK,
                 font=("Arial", 15, "bold")).pack(anchor="w", pady=(0, 13))
        tk.Label(box, text="Rubriek", bg=SURFACE, fg=INK).pack(anchor="w")
        options = [f"{key} – {CATEGORIES[key][1]}" for key in self.categories]
        choice = ttk.Combobox(box, state="readonly", values=options, font=("Arial", 10))
        choice.current(self.categories.index(category.get()))
        choice.pack(fill="x", pady=(3, 10))

        def changed(_event):
            new_category = self.categories[choice.current()]
            old_category = category.get()
            if not item and code.get() == self._next_code(old_category):
                code.set(self._next_code(new_category))
            category.set(new_category)

        choice.bind("<<ComboboxSelected>>", changed)
        tk.Label(box, text="Code", bg=SURFACE, fg=INK).pack(anchor="w")
        tk.Entry(box, textvariable=code, font=("Arial", 10)).pack(fill="x", pady=(3, 10))
        tk.Label(box, text="Benaming", bg=SURFACE, fg=INK).pack(anchor="w")
        tk.Entry(box, textvariable=name, font=("Arial", 10)).pack(fill="x", pady=(3, 10))
        tk.Label(box, text="Uitleg en eventuele voorwaarden", bg=SURFACE, fg=INK).pack(anchor="w")
        explanation = tk.Text(box, height=5, wrap="word", font=("Arial", 10),
                              bg=WHITE, fg=INK, relief="solid", bd=1)
        explanation.pack(fill="both", expand=True, pady=(3, 12))
        if item:
            explanation.insert("1.0", item.explanation)

        def save():
            candidate = code.get().strip().upper()
            if not candidate.startswith(category.get()):
                messagebox.showerror("Verkeerde rubriek", "De code moet beginnen met de letter van de gekozen rubriek.", parent=window)
                return
            try:
                self.store.put(candidate, name.get(), explanation.get("1.0", "end-1c"), item.code if item else None)
            except (OSError, ValueError) as exc:
                messagebox.showerror("Niet opgeslagen", str(exc), parent=window)
                return
            if item:
                self.chosen.discard(item.code)
            self.chosen.add(candidate)
            self._refresh()
            window.grab_release()
            window.destroy()

        buttons = tk.Frame(box, bg=SURFACE)
        buttons.pack(fill="x")
        ActionButton(buttons, "Opslaan", save, primary=True, width=112).pack(side="right")
        ActionButton(buttons, "Annuleren", window.destroy, width=112).pack(side="right", padx=(0, 8))
        window.grab_set()
        window.wait_window()
        self.grab_set()

    def _accept(self):
        self.answer = [item.code for item in self.store.items(self.categories)
                       if item.code in self.chosen and item.selectable
                       and (self.role_code != "LEEK" or item.category != "S" or item.code == "S02")]
        self.grab_release()
        self.destroy()

    def _cancel(self):
        self.grab_release()
        self.destroy()


def choose_codes(parent, store, categories, title, selected=None, role_code=""):
    window = CatalogPicker(parent, store, categories, title, selected, role_code)
    parent.wait_window(window)
    return window.answer


def make_combination(parent, store, is_leek=False):
    """Vraag precies één taak, één object en de toepasselijke procedure."""
    window = tk.Toplevel(parent)
    window.title("Bevoegdheidsregel toevoegen")
    window.configure(bg=BACKGROUND)
    window.geometry(f"680x515+{parent.winfo_rootx()+45}+{parent.winfo_rooty()+30}")
    window.minsize(610, 490)
    window.transient(parent)
    answer = {"text": None}
    card = Card(window, padding=21, expand=True)
    card.pack(fill="both", expand=True, padx=12, pady=12)
    body = card.body
    tk.Label(body, text="Eén toegestane combinatie", bg=SURFACE, fg=INK,
             font=("Arial", 15, "bold")).pack(anchor="w")
    tk.Label(body, text="Een losse taak of machine geeft geen toestemming voor alle combinaties.",
             bg=SURFACE, fg=MUTED, font=("Arial", 9)).pack(anchor="w", pady=(2, 10))

    menus = {}
    for heading, categories in (
        ("Taak", ("L", "S") if is_leek else ("S",)),
        ("Machine / installatie", ("M",)),
        ("Procedure", ("P",)),
    ):
        items = [item for item in store.items(categories) if item.selectable
                 and (not is_leek or heading != "Taak" or item.category == "L" or item.code == "S02")]
        options = [(item.line, item) for item in items]
        if heading == "Procedure":
            options.insert(0, ("Geen procedure gekozen – toelichten bij voorwaarden", None))
        tk.Label(body, text=heading, bg=SURFACE, fg=INK,
                 font=("Arial", 9, "bold")).pack(anchor="w", pady=(3, 0))
        combo = ttk.Combobox(body, state="readonly", font=("Arial", 10),
                             values=[label for label, _item in options])
        combo.pack(fill="x", pady=(3, 5))
        menus[heading] = (combo, options)

    task_info = tk.Label(body, text="Bekijk bij de keuze van een taak ook de voorwaarden uit het model.",
                         bg=SURFACE, fg=MUTED, font=("Arial", 9),
                         wraplength=600, justify="left")
    task_info.pack(anchor="w", pady=(1, 5))

    def show_task_info(_event):
        combo, choices = menus["Taak"]
        item = choices[combo.current()][1] if combo.current() >= 0 else None
        task_info.configure(text=item.explanation if item else "")

    menus["Taak"][0].bind("<<ComboboxSelected>>", show_task_info)

    tk.Label(body, text="Voorwaarden: objectdeel / assetnummer, verantwoordelijke, toestand en toezicht",
             bg=SURFACE, fg=INK, font=("Arial", 9, "bold"),
             wraplength=590, justify="left").pack(anchor="w", pady=(5, 2))
    context = tk.Text(body, height=3, font=("Arial", 10), wrap="word",
                      bg=WHITE, fg=INK, relief="solid", bd=1)
    context.pack(fill="both", expand=True, pady=(0, 10))

    def close():
        window.grab_release()
        window.destroy()

    def accept():
        chosen = []
        for heading, (combo, options) in menus.items():
            if combo.current() < 0 or (heading != "Procedure" and options[combo.current()][1] is None):
                messagebox.showerror("Nog niet volledig", f"Kies een {heading.lower()}.", parent=window)
                return
            chosen.append(options[combo.current()][1])
        details = context.get("1.0", "end-1c").strip()
        if not details:
            messagebox.showerror("Nog niet volledig", "Beschrijf het objectdeel en de voorwaarden waaronder dit is toegestaan.", parent=window)
            return
        task, machine, procedure = chosen
        procedure_name = procedure.line if procedure else "geen procedure gekoppeld (toelichting vereist)"
        answer["text"] = (f"Taak: {task.line} | Object: {machine.line} | Procedure: {procedure_name}\n"
                          f"Voorwaarden: {details}")
        close()

    buttons = tk.Frame(body, bg=SURFACE)
    buttons.pack(fill="x")
    ActionButton(buttons, "Regel toevoegen", accept, primary=True, width=156).pack(side="right")
    ActionButton(buttons, "Annuleren", close, width=108).pack(side="right", padx=(0, 9))
    window.protocol("WM_DELETE_WINDOW", close)
    window.bind("<Escape>", lambda _e: close())
    window.grab_set()
    parent.wait_window(window)
    return answer["text"]
