"""Herbruikbare Tkinter-onderdelen voor de Eqraft-interface."""

import tkinter as tk
from tkinter import ttk


BACKGROUND = "#E9EAEC"
SURFACE = "#FAFAF9"
WHITE = "#FFFFFF"
DARK = "#28292A"
SIDEBAR = "#F4DE58"
INK = "#1C1C1C"
MUTED = "#555C63"
BORDER = "#C8CBD0"
YELLOW = "#FFDE00"
ERROR = "#CC5757"


def rounded_rect(canvas, left, top, right, bottom, radius, color):
    """Teken een gevuld paneel zonder een extra GUI-afhankelijkheid."""
    radius = max(0, min(radius, (right - left) / 2, (bottom - top) / 2))
    opts = {"fill": color, "outline": ""}
    canvas.create_rectangle(left + radius, top, right - radius, bottom, **opts)
    canvas.create_rectangle(left, top + radius, right, bottom - radius, **opts)
    for x in (left, right - 2 * radius):
        for y in (top, bottom - 2 * radius):
            canvas.create_oval(x, y, x + 2 * radius, y + 2 * radius, **opts)


class Card(tk.Canvas):
    """Een kaart met afgeronde hoeken die meegroeit met de inhoud."""

    def __init__(self, parent, padding=24, expand=False, **kwargs):
        super().__init__(parent, bg=BACKGROUND, highlightthickness=0,
                         borderwidth=0, height=50, **kwargs)
        self.padding = padding
        self.expand = expand
        self.body = tk.Frame(self, bg=SURFACE)
        self.window = self.create_window(padding, padding, window=self.body, anchor="nw")
        self.bind("<Configure>", self._resize)
        self.body.bind("<Configure>", self._content_changed)

    def _content_changed(self, _event=None):
        if self.expand:
            self._draw()
            return
        height = self.body.winfo_reqheight() + self.padding * 2 + 2
        if abs(self.winfo_reqheight() - height) > 1:
            self.configure(height=height)
        self._draw()

    def _resize(self, event):
        self.itemconfigure(self.window, width=max(1, event.width - 2 * self.padding - 2))
        if self.expand:
            self.itemconfigure(self.window, height=max(1, event.height - 2 * self.padding))
        self._draw()

    def _draw(self):
        width, height = self.winfo_width(), self.winfo_height()
        if width <= 3 or height <= 3:
            return
        self.delete("shape")
        rounded_rect(self, 2, 2, width - 1, height - 1, 16, BORDER)
        rounded_rect(self, 3, 3, width - 2, height - 2, 15, SURFACE)
        for item in self.find_all():
            if item != self.window:
                self.addtag_withtag("shape", item)
        self.tag_lower("shape", self.window)


class InputBox(tk.Canvas):
    """Afgeronde rand om een gewone, selecteerbare Tk-invoer."""

    def __init__(self, parent, multiline=False, on_change=None):
        super().__init__(parent, bg=SURFACE, highlightthickness=0, borderwidth=0,
                         height=106 if multiline else 44)
        self.state = "normal"
        self.multiline = multiline
        if multiline:
            self.widget = tk.Text(self, height=3, wrap="word", bg=WHITE, fg=INK,
                                  font=("Arial", 10), relief="flat", borderwidth=0,
                                  highlightthickness=0, padx=1, pady=1,
                                  insertbackground=INK, undo=True)
        else:
            self.widget = tk.Entry(self, bg=WHITE, fg=INK, font=("Arial", 10),
                                   relief="flat", borderwidth=0, highlightthickness=0,
                                   insertbackground=INK)
        self.window = self.create_window(13, 10, anchor="nw", window=self.widget)
        self.bind("<Configure>", self._resize)
        self.widget.bind("<FocusIn>", self._focus_on, add="+")
        self.widget.bind("<FocusOut>", self._focus_off, add="+")
        if on_change:
            self.widget.bind("<KeyRelease>", on_change, add="+")
            self.widget.bind("<<Paste>>", lambda _e: self.after_idle(on_change), add="+")
            self.widget.bind("<<Cut>>", lambda _e: self.after_idle(on_change), add="+")

    def _focus_on(self, _event):
        if self.state != "error":
            self.state = "focus"
        self._draw()

    def _focus_off(self, _event):
        if self.state != "error":
            self.state = "normal"
        self._draw()

    def set_error(self):
        self.state = "error"
        self._draw()

    def _resize(self, event):
        self.itemconfigure(self.window, width=max(1, event.width - 26),
                           height=max(1, event.height - 20))
        self._draw()

    def _draw(self):
        width, height = self.winfo_width(), self.winfo_height()
        if width <= 3 or height <= 3:
            return
        self.delete("shape")
        color = {"normal": "#AEB3BA", "focus": "#B99B00", "error": ERROR}[self.state]
        rounded_rect(self, 0, 0, width, height, 9, color)
        rounded_rect(self, 2, 2, width - 2, height - 2, 8, WHITE)
        for item in self.find_all():
            if item != self.window:
                self.addtag_withtag("shape", item)
        self.tag_lower("shape", self.window)


class SelectBox(tk.Canvas):
    def __init__(self, parent, variable, options, style="Eq.Flat.TCombobox"):
        super().__init__(parent, bg=SURFACE, highlightthickness=0, height=44)
        self.combo = ttk.Combobox(self, textvariable=variable, values=options,
                                  state="readonly", style=style,
                                  font=("Arial", 10))
        self.window = self.create_window(9, 8, anchor="nw", window=self.combo)
        self.bind("<Configure>", self._resize)

    def _resize(self, event):
        self.delete("shape")
        rounded_rect(self, 0, 0, event.width, event.height, 9, "#AEB3BA")
        rounded_rect(self, 2, 2, event.width - 2, event.height - 2, 8, WHITE)
        for item in self.find_all():
            if item != self.window:
                self.addtag_withtag("shape", item)
        self.tag_lower("shape", self.window)
        self.itemconfigure(self.window, width=max(1, event.width - 18),
                           height=max(1, event.height - 16))


class ActionButton(tk.Canvas):
    def __init__(self, parent, text, command, primary=False, width=148, background=SURFACE):
        super().__init__(parent, width=width, height=46, bg=background,
                         highlightthickness=0, takefocus=1, cursor="hand2")
        self.text, self.command, self.primary = text, command, primary
        self.hover = False
        self.bind("<Configure>", lambda _e: self._draw())
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<Button-1>", lambda _e: self.command())
        self.bind("<Return>", lambda _e: self.command())
        self.bind("<space>", lambda _e: self.command())
        self.bind("<FocusIn>", lambda _e: self._draw())
        self.bind("<FocusOut>", lambda _e: self._draw())
        self._draw()

    def _enter(self, _event):
        self.hover = True
        self._draw()

    def _leave(self, _event):
        self.hover = False
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1:
            w, h = int(self.cget("width")), int(self.cget("height"))
        base = ("#E9CA00" if self.hover else YELLOW) if self.primary else ("#F0F1F2" if self.hover else WHITE)
        rounded_rect(self, 0, 0, w, h, 11, BORDER if not self.primary else base)
        rounded_rect(self, 2, 2, w - 2, h - 2, 10, base)
        self.create_text(w / 2, h / 2, text=self.text, fill=INK,
                         font=("Arial", 10, "bold"))


class NavItem(tk.Canvas):
    def __init__(self, parent, text, command, selected=False):
        super().__init__(parent, width=192, height=47, bg=SIDEBAR,
                         highlightthickness=0, cursor="hand2", takefocus=1)
        self.text, self.command, self.selected, self.hover = text, command, selected, False
        self.bind("<Configure>", lambda _e: self._draw())
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<Button-1>", lambda _e: self.command())
        self.bind("<Return>", lambda _e: self.command())
        self.bind("<space>", lambda _e: self.command())
        self._draw()

    def _enter(self, _event):
        self.hover = True
        self._draw()

    def _leave(self, _event):
        self.hover = False
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width() if self.winfo_width() > 1 else 192
        if self.selected or self.hover:
            rounded_rect(self, 0, 0, w, 47, 11, DARK if self.selected else "#FFE98A")
        if self.selected:
            rounded_rect(self, 7, 13, 11, 34, 2, YELLOW)
        self.create_text(20, 23, text="•", anchor="w", fill=YELLOW if self.selected else DARK,
                         font=("Arial", 13, "bold"))
        self.create_text(38, 24, text=self.text, anchor="w",
                         fill=WHITE if self.selected else INK,
                         font=("Arial", 10, "bold" if self.selected else "normal"))


class SummaryTile(tk.Canvas):
    """Compact overzichtsvak met eigen afgeronde achtergrond."""

    def __init__(self, parent, label, variable):
        super().__init__(parent, bg=SURFACE, height=70, highlightthickness=0)
        content = tk.Frame(self, bg="#F0F1F1")
        tk.Label(content, text=label, bg="#F0F1F1", fg=MUTED,
                 font=("Arial", 8, "bold")).pack(anchor="w")
        value = tk.Label(content, textvariable=variable, bg="#F0F1F1", fg=INK,
                         font=("Arial", 10, "bold"), anchor="w", justify="left")
        value.pack(fill="x", pady=(5, 0))
        self.window = self.create_window(12, 12, window=content, anchor="nw")
        self.bind("<Configure>", self._resize)

    def _resize(self, event):
        width, height = event.width, event.height
        self.delete("tile_shape")
        rounded_rect(self, 0, 0, width, height, 11, BORDER)
        rounded_rect(self, 1.5, 1.5, width - 1.5, height - 1.5, 10, "#F0F1F1")
        for item in self.find_all():
            if item != self.window:
                self.addtag_withtag("tile_shape", item)
        self.tag_lower("tile_shape", self.window)
        self.itemconfigure(self.window, width=max(1, width - 24), height=max(1, height - 20))
