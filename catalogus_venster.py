"""Keuzevenster met uitleg per code en beheer van eigen aanvullingen."""

import tkinter as tk
from tkinter import messagebox, ttk

from catalogus import CATEGORIES, CatalogStore
from ui_components import BACKGROUND, BORDER, INK, MUTED, SURFACE, WHITE, YELLOW, ActionButton, Card


class CatalogPicker(tk.Toplevel):
    def __init__(self, parent, store: CatalogStore, categories: tuple[str, ...],
                 title: str, initial: set[str] | None = None, role_code: str = "",
                 manage_only: bool = False):
        super().__init__(parent)
        self.store, self.categories, self.chosen = store, categories, set(initial or ())
        self.role_code = role_code
        self.manage_only = manage_only
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
        tk.Label(body, text=("Bekijk alle codes en hun uitleg. Voeg nieuwe codes toe of beheer je eigen aanvullingen."
                             if self.manage_only else
                             "Klik op een regel voor de uitleg; selecteer uitsluitend via het rondje links. Code en naam komen in het formulier."),
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
        self.tree.heading("check", text="" if self.manage_only else "Kies")
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

        tk.Label(body, text=("Vaste codes komen uit het aanwijzingsmodel. Eigen aanvullingen blijven bewaard voor deze gebruiker."
                             if self.manage_only else
                             "Beschikbare codes zijn voorstellen; leg de toegestane taken per machine persoonlijk vast."),
                 bg=SURFACE, fg=MUTED, font=("Arial", 9),
                 wraplength=780, justify="left").pack(anchor="w", pady=(12, 6))
        buttons = tk.Frame(body, bg=SURFACE)
        buttons.pack(fill="x")
        ActionButton(buttons, "Toevoegen", self._add, width=114).pack(side="left")
        ActionButton(buttons, "Bewerken", self._edit, width=105).pack(side="left", padx=(7, 0))
        ActionButton(buttons, "Verwijderen", self._delete, width=112).pack(side="left", padx=(7, 0))
        if self.manage_only:
            ActionButton(buttons, "Sluiten", self._cancel, primary=True, width=110).pack(side="right")
        else:
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
            if (self.role_code in ("LEEK", "ZZP") and item.category == "S"
                    and item.code != "S02"):
                continue
            if term and term not in (item.code + " " + item.name + " " + item.explanation).casefold():
                continue
            self.tree.insert("", "end", iid=item.code,
                             values=("" if self.manage_only else
                                     "●" if item.code in self.chosen else "○", item.code, item.name))
        if focused and self.tree.exists(focused):
            self.tree.focus(focused)
        self._show_detail()

    def _clicked(self, event):
        code = self.tree.identify_row(event.y)
        if code:
            self.tree.focus(code)
            self.tree.selection_set(code)
            self._show_detail()
            if not self.manage_only and self.tree.identify_column(event.x) == "#1":
                self._toggle(code)
        return "break" if code else None

    def _toggle_focused(self, _event):
        self._toggle(self.tree.focus())
        return "break"

    def _toggle(self, code):
        if not code or self.manage_only:
            return
        item = self.store.get(code)
        if not item.selectable:
            messagebox.showinfo("Rubriektitel", "S01 is alleen een rubriektitel. Kies een concrete taak uit L01–L08.", parent=self)
            return
        if code in self.chosen:
            self.chosen.remove(code)
        else:
            self.chosen.add(code)
        self.tree.set(code, "check", "●" if code in self.chosen else "○")
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
                       and (self.role_code not in ("LEEK", "ZZP") or item.category != "S" or item.code == "S02")]
        self.grab_release()
        self.destroy()

    def _cancel(self):
        self.grab_release()
        self.destroy()


def choose_codes(parent, store, categories, title, selected=None, role_code=""):
    window = CatalogPicker(parent, store, categories, title, selected, role_code)
    parent.wait_window(window)
    return window.answer


def manage_codes(parent, store):
    window = CatalogPicker(parent, store, tuple(CATEGORIES), "Alle codes beheren", manage_only=True)
    parent.wait_window(window)


def format_machine_permissions(machine, tasks):
    """Eén machine met uitsluitend de voor deze persoon gekozen bevoegdheden."""
    if not tasks:
        raise ValueError("Kies ten minste één taak voor deze machine.")
    return f"Machine: {machine.line}\nBevoegdheden:\n" + "\n".join(
        f"• {task.line}" for task in tasks
    )


def make_combination(parent, store, is_leek=False):
    """Kies één machine en meerdere uitdrukkelijk toegestane taken."""
    window = tk.Toplevel(parent)
    window.title("Bevoegdheden per machine toevoegen")
    window.configure(bg=BACKGROUND)
    width = min(750, max(610, parent.winfo_screenwidth() - 100))
    height = min(650, max(490, parent.winfo_screenheight() - 110))
    top = max(10, min(parent.winfo_rooty() + 30, parent.winfo_screenheight() - height - 45))
    window.geometry(f"{width}x{height}+{parent.winfo_rootx()+45}+{top}")
    window.minsize(610, 490)
    window.transient(parent)
    answer = {"text": None}
    card = Card(window, padding=18, expand=True)
    card.pack(fill="both", expand=True, padx=12, pady=12)
    body = card.body
    tk.Label(body, text="Persoonlijke bevoegdheden per machine", bg=SURFACE, fg=INK,
             font=("Arial", 15, "bold")).pack(anchor="w")
    tk.Label(body, text="Kies een machine en vink de taken aan die deze persoon daar mag uitvoeren. Klik een taak voor de uitleg.",
             bg=SURFACE, fg=MUTED, font=("Arial", 9), wraplength=660,
             justify="left").pack(anchor="w", pady=(2, 12))

    machines = [item for item in store.items(("M",)) if item.selectable]
    tk.Label(body, text="Machine / installatie", bg=SURFACE, fg=INK,
             font=("Arial", 9, "bold")).pack(anchor="w")
    machine = ttk.Combobox(body, state="readonly", font=("Arial", 10),
                           values=[item.line for item in machines])
    machine.pack(fill="x", pady=(4, 7))
    machine_info = tk.Label(body, text="Selecteer eerst de machine.", bg=SURFACE,
                            fg=MUTED, font=("Arial", 9), wraplength=650, justify="left")
    machine_info.pack(anchor="w", pady=(0, 11))

    tk.Label(body, text="Taken voor deze machine · selecteer via het rondje", bg=SURFACE,
             fg=INK, font=("Arial", 9, "bold")).pack(anchor="w", pady=(0, 5))
    tasks = [item for item in store.items(("L", "S") if is_leek else ("S", "L"))
             if item.selectable and (not is_leek or item.category == "L" or item.code == "S02")]
    chosen = set()
    table_frame = tk.Frame(body, bg=SURFACE)
    table_frame.pack(fill="both", expand=True, pady=(0, 9))
    table = ttk.Treeview(table_frame, columns=("choose", "code", "name"),
                         show="headings", height=9, selectmode="browse")
    for key, label, size in (("choose", "", 47), ("code", "Code", 74), ("name", "Taak", 420)):
        table.heading(key, text=label)
        table.column(key, width=size, minwidth=size if key != "name" else 180,
                     stretch=key == "name", anchor="center" if key == "choose" else "w")
    scroll = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
    table.configure(yscrollcommand=scroll.set)
    table.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    info = tk.Label(body, text="Kies een taak voor de uitleg uit het aanwijzingsmodel.", bg="#F0F1F1",
                    fg=INK, font=("Arial", 9), wraplength=640, justify="left",
                    padx=11, pady=10, anchor="nw", height=4)
    info.pack(fill="x", pady=(0, 12))

    def refresh_tasks(_event=None):
        selected_machine = machines[machine.current()] if machine.current() >= 0 else None
        machine_info.configure(text=selected_machine.explanation if selected_machine else "Selecteer eerst de machine.")
        chosen.clear()
        table.delete(*table.get_children())
        for item in tasks:
            if selected_machine and selected_machine.code == "M12" and item.category != "L":
                continue
            table.insert("", "end", iid=item.code, values=("○", item.code, item.name))
        info.configure(text="Kies een taak voor de uitleg uit het aanwijzingsmodel.")

    def clicked(event):
        code = table.identify_row(event.y)
        if code:
            table.focus(code)
            table.selection_set(code)
            item = store.get(code)
            info.configure(text=f"{item.line}\n{item.explanation}")
            if table.identify_column(event.x) == "#1":
                if code in chosen:
                    chosen.remove(code)
                else:
                    chosen.add(code)
                table.set(code, "choose", "●" if code in chosen else "○")
            return "break"
        return None

    table.bind("<Button-1>", clicked)
    machine.bind("<<ComboboxSelected>>", refresh_tasks)
    refresh_tasks()

    def close():
        window.grab_release()
        window.destroy()

    def accept():
        if machine.current() < 0:
            messagebox.showerror("Nog niet volledig", "Kies eerst een machine.", parent=window)
            return
        if not chosen:
            messagebox.showerror("Nog niet volledig", "Vink één of meer taken aan via het rondje links.", parent=window)
            return
        selected = [item for item in tasks if item.code in chosen]
        answer["text"] = format_machine_permissions(machines[machine.current()], selected)
        close()

    buttons = tk.Frame(body, bg=SURFACE)
    buttons.pack(fill="x")
    ActionButton(buttons, "Bevoegdheden overnemen", accept, primary=True, width=220).pack(side="right")
    ActionButton(buttons, "Annuleren", close, width=108).pack(side="right", padx=(0, 9))
    window.protocol("WM_DELETE_WINDOW", close)
    window.bind("<Escape>", lambda _e: close())
    window.grab_set()
    parent.wait_window(window)
    return answer["text"]
