"""CSV Tools - Batch add/remove characters in CSV columns and rows.

Workflow:
  1. Drop CSV files into the ./input folder.
  2. Pick a file from the list on the left.
  3. Click a column header to select the entire column (Shift+click to unselect).
     Click a row number to select the entire row.
     Ctrl+click cells / headers / row numbers to toggle individual items.
  4. Type text in the "Text" box and hit Add Before / Add After / Replace.
     Use Trim Start/End to chop N characters off each selected cell.
  5. Press "Save to Output" -- the modified CSV is written to ./output
     keeping the original file name.

Only the Python standard library is used.
"""

from __future__ import annotations

import csv
import os
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont
from tkinter import messagebox, simpledialog, ttk

APP_DIR = Path(__file__).resolve().parent
INPUT_DIR = APP_DIR / "input"
OUTPUT_DIR = APP_DIR / "output"

# -------- Dark theme palette --------
BG_BASE = "#1b1d2a"       # main window background
BG_ELEV = "#262936"       # toolbars / sidebar panels
BG_DEEP = "#121424"       # entries, listbox background
BORDER = "#3a3d4f"
FG_DEFAULT = "#e6e9ef"
FG_MUTED = "#8a90a6"
FG_HINT = "#6f7590"
ACCENT = "#60a5fa"
ACCENT_BG = "#2563eb"
ACCENT_ACTIVE = "#3b82f6"

HEADER_BG = "#1f2230"
HEADER_FG = "#f3f4f6"
HEADER_SEL_BG = ACCENT_BG
ROW_NUM_BG = "#232636"
ROW_NUM_FG = "#9ca3af"
ROW_NUM_SEL_BG = ACCENT_BG
ROW_NUM_SEL_FG = "#ffffff"
CELL_BG = "#1a1d2a"
CELL_ALT_BG = "#1f2230"
CELL_FG = "#e6e9ef"
SELECTED_BG = "#1e3a8a"
SELECTED_FG = "#f9fafb"
GRID_LINE = "#32364a"
CORNER_BG = "#0f1220"

CELL_HEIGHT = 24
CELL_PAD_X = 8
MIN_COL_WIDTH = 60
MAX_COL_WIDTH = 320

ALLOWED_EXT = {".csv", ".tsv", ".txt"}


class CSVTool:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("CSV Tools  —  Batch Text Editor")
        self.root.geometry("1320x780")
        self.root.minsize(980, 560)

        self.cell_font = tkfont.Font(family="Segoe UI", size=9)
        self.header_font = tkfont.Font(family="Segoe UI", size=9, weight="bold")

        self.data: list[list[str]] = []
        self.headers: list[str] = []
        self.selected: set[tuple[int, int]] = set()  # (row, col). row = -1 for header
        self.col_widths: list[int] = []
        self.col_x: list[int] = [0]
        self.row_num_width = 56
        self.current_file: Path | None = None
        self.dialect: type[csv.Dialect] | csv.Dialect = csv.excel
        self.modified = False
        self.undo_stack: list[tuple[list[str], list[list[str]], bool]] = []

        self.cell_rects: dict[tuple[int, int], int] = {}
        self.cell_texts: dict[tuple[int, int], int] = {}
        self.header_rects: dict[int, int] = {}
        self.header_texts: dict[int, int] = {}
        self.rownum_rects: dict[int, int] = {}
        self.rownum_texts: dict[int, int] = {}

        # Drag & drop state for reordering columns / rows.
        self._drag: dict | None = None
        self._drop_line_ids: list[tuple[tk.Canvas, int]] = []

        INPUT_DIR.mkdir(exist_ok=True)
        OUTPUT_DIR.mkdir(exist_ok=True)

        self._build_ui()
        self._refresh_input_files()
        self._update_info()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        self._apply_dark_theme()

        toolbar = ttk.Frame(self.root, style="Toolbar.TFrame", padding=(8, 6))
        toolbar.pack(side="top", fill="x")

        ttk.Label(toolbar, text="Text:", style="Toolbar.TLabel").pack(side="left")
        self.text_var = tk.StringVar()
        ttk.Entry(toolbar, textvariable=self.text_var, width=22).pack(
            side="left", padx=(4, 6)
        )
        ttk.Label(toolbar, text="Replace with:", style="Toolbar.TLabel").pack(
            side="left"
        )
        self.replace_var = tk.StringVar()
        ttk.Entry(toolbar, textvariable=self.replace_var, width=18).pack(
            side="left", padx=(4, 10)
        )

        self.overwrite_var = tk.BooleanVar(value=False)
        self.overwrite_chk = ttk.Checkbutton(
            toolbar,
            text="Overwrite",
            variable=self.overwrite_var,
            style="Toolbar.TCheckbutton",
            command=self._on_overwrite_toggled,
        )
        self.overwrite_chk.pack(side="left", padx=(0, 12))

        ttk.Button(toolbar, text="Add Before", command=self.op_add_before).pack(
            side="left", padx=2
        )
        ttk.Button(toolbar, text="Add After", command=self.op_add_after).pack(
            side="left", padx=2
        )
        ttk.Button(toolbar, text="Replace", command=self.op_replace).pack(
            side="left", padx=2
        )
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(toolbar, text="Trim Start N…", command=self.op_trim_start).pack(
            side="left", padx=2
        )
        ttk.Button(toolbar, text="Trim End N…", command=self.op_trim_end).pack(
            side="left", padx=2
        )
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(toolbar, text="Undo", command=self.undo).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Clear Sel.", command=self.clear_selection).pack(
            side="left", padx=2
        )
        ttk.Button(toolbar, text="Select All", command=self.select_all).pack(
            side="left", padx=2
        )
        ttk.Button(toolbar, text="Invert Sel.", command=self.invert_selection).pack(
            side="left", padx=2
        )

        self.save_btn = ttk.Button(
            toolbar,
            text="Save to Output",
            style="Accent.TButton",
            command=self.save_file,
        )
        self.save_btn.pack(side="right", padx=2)

        info = ttk.Frame(self.root, padding=(10, 2))
        info.pack(side="top", fill="x")
        self.info_label = ttk.Label(info, text="No file loaded", foreground=FG_MUTED)
        self.info_label.pack(side="left")
        self.sel_label = ttk.Label(
            info, text="Selection: 0 cells", foreground=ACCENT
        )
        self.sel_label.pack(side="right")

        self.hint_label = ttk.Label(
            self.root,
            padding=(10, 0),
            foreground=FG_HINT,
            text=self._default_hint_text(),
        )
        self.hint_label.pack(side="top", fill="x")

        main = ttk.Panedwindow(self.root, orient="horizontal")
        main.pack(fill="both", expand=True, padx=6, pady=(4, 6))

        # ---- Left pane: file list + output ----
        left = ttk.Frame(main, style="Sidebar.TFrame", padding=6)

        ttk.Label(
            left, text="Input Files", style="SidebarHeading.TLabel",
            font=self.header_font,
        ).pack(anchor="w")
        ttk.Label(
            left,
            text=f"Folder: .\\{INPUT_DIR.name}\\",
            style="SidebarMuted.TLabel",
        ).pack(anchor="w")

        list_frame = ttk.Frame(left, style="Sidebar.TFrame")
        list_frame.pack(fill="both", expand=True, pady=(4, 4))
        self.file_list = tk.Listbox(
            list_frame,
            activestyle="none",
            exportselection=False,
            bg=BG_DEEP,
            fg=FG_DEFAULT,
            selectbackground=ACCENT_BG,
            selectforeground="#ffffff",
            highlightthickness=0,
            relief="flat",
            borderwidth=0,
        )
        self.file_list.pack(side="left", fill="both", expand=True)
        fsb = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.file_list.yview
        )
        fsb.pack(side="right", fill="y")
        self.file_list.configure(yscrollcommand=fsb.set)
        self.file_list.bind("<<ListboxSelect>>", self._on_file_select)

        btn_row = ttk.Frame(left, style="Sidebar.TFrame")
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Refresh", command=self._refresh_input_files).pack(
            side="left", fill="x", expand=True, padx=1
        )
        ttk.Button(btn_row, text="Open Folder", command=self._open_input_folder).pack(
            side="left", fill="x", expand=True, padx=1
        )

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=8)
        ttk.Label(
            left, text="Sheet", style="SidebarHeading.TLabel",
            font=self.header_font,
        ).pack(anchor="w")
        self.has_header_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            left,
            text="First row is header",
            variable=self.has_header_var,
            style="Sidebar.TCheckbutton",
            command=self._on_has_header_toggle,
        ).pack(anchor="w", pady=(2, 0))

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=8)
        ttk.Label(
            left, text="Output", style="SidebarHeading.TLabel",
            font=self.header_font,
        ).pack(anchor="w")
        ttk.Label(
            left,
            text=f"Folder: .\\{OUTPUT_DIR.name}\\",
            style="SidebarMuted.TLabel",
        ).pack(anchor="w")

        self.suffix_var = tk.StringVar(value="")
        row = ttk.Frame(left, style="Sidebar.TFrame")
        row.pack(fill="x", pady=(6, 2))
        ttk.Label(row, text="File name suffix:", style="Sidebar.TLabel").pack(
            side="left"
        )
        ttk.Entry(row, textvariable=self.suffix_var, width=12).pack(
            side="left", padx=(4, 0)
        )

        ttk.Button(
            left, text="Open Output Folder", command=self._open_output_folder
        ).pack(fill="x", pady=4)

        main.add(left, weight=0)

        # ---- Right pane: grid ----
        right = ttk.Frame(main)

        self.h_scroll = ttk.Scrollbar(right, orient="horizontal")
        self.v_scroll = ttk.Scrollbar(right, orient="vertical")

        self.canvas = tk.Canvas(right, bg=CELL_BG, highlightthickness=0)
        self.header_canvas = tk.Canvas(
            right, bg=HEADER_BG, highlightthickness=0, height=CELL_HEIGHT
        )
        self.rownum_canvas = tk.Canvas(
            right, bg=ROW_NUM_BG, highlightthickness=0, width=self.row_num_width
        )
        self.corner_canvas = tk.Canvas(
            right,
            bg=CORNER_BG,
            highlightthickness=0,
            width=self.row_num_width,
            height=CELL_HEIGHT,
        )

        self.canvas.configure(
            xscrollcommand=self._on_canvas_x, yscrollcommand=self._on_canvas_y
        )
        self.h_scroll.configure(command=self._scrollbar_x)
        self.v_scroll.configure(command=self._scrollbar_y)

        right.rowconfigure(1, weight=1)
        right.columnconfigure(1, weight=1)
        self.corner_canvas.grid(row=0, column=0, sticky="nsew")
        self.header_canvas.grid(row=0, column=1, sticky="nsew")
        self.rownum_canvas.grid(row=1, column=0, sticky="nsew")
        self.canvas.grid(row=1, column=1, sticky="nsew")
        self.v_scroll.grid(row=1, column=2, sticky="ns")
        self.h_scroll.grid(row=2, column=1, sticky="ew")

        main.add(right, weight=1)

        self.canvas.create_text(
            30,
            30,
            anchor="nw",
            fill=FG_MUTED,
            font=self.cell_font,
            text=(
                "Pick a CSV from the left panel to start editing.\n\n"
                "Tip: drag files into the input\\ folder, then press Refresh."
            ),
        )

        # Mouse bindings
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Control-Button-1>", self._on_canvas_ctrl_click)
        self.canvas.bind("<Shift-Button-1>", self._on_canvas_shift_click)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Shift-MouseWheel>", self._on_shift_mousewheel)

        # Header press/motion/release drives both click-to-select and
        # drag-to-reorder. Right-click opens a context menu.
        self.header_canvas.bind("<ButtonPress-1>", self._header_press)
        self.header_canvas.bind("<B1-Motion>", self._header_motion)
        self.header_canvas.bind("<ButtonRelease-1>", self._header_release)
        self.header_canvas.bind("<Button-3>", self._header_right_click)
        self.header_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.header_canvas.bind("<Shift-MouseWheel>", self._on_shift_mousewheel)

        self.rownum_canvas.bind("<ButtonPress-1>", self._rownum_press)
        self.rownum_canvas.bind("<B1-Motion>", self._rownum_motion)
        self.rownum_canvas.bind("<ButtonRelease-1>", self._rownum_release)
        self.rownum_canvas.bind("<Button-3>", self._rownum_right_click)
        self.rownum_canvas.bind("<MouseWheel>", self._on_mousewheel)

        self.corner_canvas.bind("<Button-1>", lambda _e: self.select_all())

        self.root.bind("<Control-a>", lambda _e: self.select_all())
        self.root.bind("<Control-A>", lambda _e: self.select_all())
        self.root.bind("<Control-s>", lambda _e: self.save_file())
        self.root.bind("<Control-S>", lambda _e: self.save_file())
        self.root.bind("<Control-z>", lambda _e: self.undo())
        self.root.bind("<Control-Z>", lambda _e: self.undo())
        self.root.bind("<Escape>", lambda _e: self.clear_selection())

    # ------------------------------------------------------------------ theme
    def _apply_dark_theme(self) -> None:
        self.root.configure(bg=BG_BASE)
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure(
            ".",
            background=BG_BASE,
            foreground=FG_DEFAULT,
            fieldbackground=BG_DEEP,
            bordercolor=BORDER,
            lightcolor=BG_ELEV,
            darkcolor=BG_ELEV,
            troughcolor=BG_BASE,
            insertcolor=FG_DEFAULT,
            focuscolor=ACCENT,
        )

        style.configure("TFrame", background=BG_BASE)
        style.configure("Toolbar.TFrame", background=BG_ELEV)
        style.configure("Sidebar.TFrame", background=BG_ELEV)

        style.configure("TLabel", background=BG_BASE, foreground=FG_DEFAULT)
        style.configure(
            "Toolbar.TLabel", background=BG_ELEV, foreground=FG_DEFAULT
        )
        style.configure(
            "Sidebar.TLabel", background=BG_ELEV, foreground=FG_DEFAULT
        )
        style.configure(
            "SidebarHeading.TLabel",
            background=BG_ELEV,
            foreground=FG_DEFAULT,
        )
        style.configure(
            "SidebarMuted.TLabel", background=BG_ELEV, foreground=FG_MUTED
        )

        style.configure(
            "TButton",
            background=BG_ELEV,
            foreground=FG_DEFAULT,
            bordercolor=BORDER,
            lightcolor=BG_ELEV,
            darkcolor=BG_ELEV,
            padding=(10, 4),
            relief="flat",
        )
        style.map(
            "TButton",
            background=[
                ("pressed", BG_DEEP),
                ("active", "#30344a"),
                ("disabled", BG_ELEV),
            ],
            foreground=[("disabled", FG_HINT)],
            bordercolor=[("focus", ACCENT), ("active", ACCENT)],
        )
        style.configure(
            "Accent.TButton",
            background=ACCENT_BG,
            foreground="#ffffff",
            bordercolor=ACCENT_BG,
            lightcolor=ACCENT_BG,
            darkcolor=ACCENT_BG,
        )
        style.map(
            "Accent.TButton",
            background=[
                ("pressed", "#1d4ed8"),
                ("active", ACCENT_ACTIVE),
            ],
            bordercolor=[("active", ACCENT)],
        )

        style.configure(
            "TEntry",
            fieldbackground=BG_DEEP,
            foreground=FG_DEFAULT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            insertcolor=FG_DEFAULT,
        )
        style.map(
            "TEntry",
            bordercolor=[("focus", ACCENT)],
            lightcolor=[("focus", ACCENT)],
            darkcolor=[("focus", ACCENT)],
        )

        style.configure(
            "TCheckbutton",
            background=BG_BASE,
            foreground=FG_DEFAULT,
            indicatorbackground=BG_DEEP,
            indicatorforeground=FG_DEFAULT,
            bordercolor=BORDER,
            focuscolor=ACCENT,
        )
        style.configure(
            "Toolbar.TCheckbutton",
            background=BG_ELEV,
            foreground=FG_DEFAULT,
            indicatorbackground=BG_DEEP,
            indicatorforeground=FG_DEFAULT,
            bordercolor=BORDER,
        )
        style.configure(
            "Sidebar.TCheckbutton",
            background=BG_ELEV,
            foreground=FG_DEFAULT,
            indicatorbackground=BG_DEEP,
            indicatorforeground=FG_DEFAULT,
            bordercolor=BORDER,
        )
        style.map(
            "Sidebar.TCheckbutton",
            background=[("active", "#30344a")],
            indicatorbackground=[
                ("selected", ACCENT_BG),
                ("pressed", ACCENT_ACTIVE),
            ],
            indicatorforeground=[("selected", "#ffffff")],
        )
        style.map(
            "TCheckbutton",
            background=[("active", BG_ELEV)],
            indicatorbackground=[
                ("selected", ACCENT_BG),
                ("pressed", ACCENT_ACTIVE),
            ],
            indicatorforeground=[("selected", "#ffffff")],
        )
        style.map(
            "Toolbar.TCheckbutton",
            background=[("active", "#30344a")],
            indicatorbackground=[
                ("selected", ACCENT_BG),
                ("pressed", ACCENT_ACTIVE),
            ],
            indicatorforeground=[("selected", "#ffffff")],
        )

        style.configure(
            "TScrollbar",
            background=BG_ELEV,
            troughcolor=BG_BASE,
            bordercolor=BG_BASE,
            arrowcolor=FG_DEFAULT,
            lightcolor=BG_ELEV,
            darkcolor=BG_ELEV,
        )
        style.map(
            "TScrollbar",
            background=[("active", "#30344a")],
            arrowcolor=[("disabled", FG_HINT)],
        )

        style.configure("TSeparator", background=BORDER)
        style.configure("TPanedwindow", background=BG_BASE)
        style.configure("Sash", sashthickness=6, background=BORDER)

    def _default_hint_text(self) -> str:
        return (
            "Click header/row# = select  •  Drag header or row# = reorder  •  "
            "Right-click header/row# = menu (copy / move / insert / delete)  •  "
            "Ctrl+Click = toggle  •  Shift+Click header = drop just the header  •  "
            "Top-left = Select All"
        )

    def _on_overwrite_toggled(self) -> None:
        """Update the hint label so users see the current mode at a glance."""
        if not hasattr(self, "hint_label"):
            return
        if self.overwrite_var.get():
            self.hint_label.configure(
                foreground=ACCENT,
                text=(
                    "OVERWRITE MODE: Add Before / Add After / Replace will "
                    "replace every selected cell with the Text value."
                ),
            )
        else:
            self.hint_label.configure(
                foreground=FG_HINT,
                text=self._default_hint_text(),
            )

    # --------------------------------------------------------- scroll sync
    def _on_canvas_x(self, *args: str) -> None:
        self.h_scroll.set(*args)
        self.header_canvas.xview_moveto(args[0])

    def _on_canvas_y(self, *args: str) -> None:
        self.v_scroll.set(*args)
        self.rownum_canvas.yview_moveto(args[0])

    def _scrollbar_x(self, *args: str) -> None:
        self.canvas.xview(*args)
        self.header_canvas.xview(*args)

    def _scrollbar_y(self, *args: str) -> None:
        self.canvas.yview(*args)
        self.rownum_canvas.yview(*args)

    def _on_mousewheel(self, event: tk.Event) -> str:
        delta = -1 * (event.delta // 120)
        self.canvas.yview_scroll(delta, "units")
        self.rownum_canvas.yview_scroll(delta, "units")
        return "break"

    def _on_shift_mousewheel(self, event: tk.Event) -> str:
        delta = -1 * (event.delta // 120)
        self.canvas.xview_scroll(delta, "units")
        self.header_canvas.xview_scroll(delta, "units")
        return "break"

    # --------------------------------------------------------- file list
    def _refresh_input_files(self) -> None:
        self.file_list.delete(0, "end")
        if INPUT_DIR.exists():
            for p in sorted(INPUT_DIR.iterdir(), key=lambda x: x.name.lower()):
                if p.is_file() and p.suffix.lower() in ALLOWED_EXT:
                    self.file_list.insert("end", p.name)

    def _on_file_select(self, _event: tk.Event) -> None:
        sel = self.file_list.curselection()
        if not sel:
            return
        name = self.file_list.get(sel[0])
        self.load_csv(INPUT_DIR / name)

    def _open_input_folder(self) -> None:
        try:
            os.startfile(str(INPUT_DIR))  # type: ignore[attr-defined]
        except Exception as e:
            messagebox.showerror("Open folder", str(e))

    def _open_output_folder(self) -> None:
        try:
            os.startfile(str(OUTPUT_DIR))  # type: ignore[attr-defined]
        except Exception as e:
            messagebox.showerror("Open folder", str(e))

    # --------------------------------------------------------- CSV I/O
    def load_csv(self, path: Path) -> None:
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as f:
                sample = f.read(8192)
                f.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
                except csv.Error:
                    dialect = csv.excel
                rows = list(csv.reader(f, dialect))
        except Exception as e:
            messagebox.showerror("Open CSV", f"Failed to open:\n{e}")
            return

        if not rows:
            messagebox.showwarning("Empty file", "The selected file is empty.")
            return

        if self.has_header_var.get():
            self.headers = list(rows[0])
            self.data = [list(r) for r in rows[1:]]
        else:
            ncols = max((len(r) for r in rows), default=0)
            self.headers = [f"Col {i + 1}" for i in range(ncols)]
            self.data = [list(r) for r in rows]
        self.dialect = dialect
        self.current_file = path
        self.selected.clear()
        self.undo_stack.clear()
        self.modified = False
        self._compute_column_widths()
        self._redraw_all()
        self._update_info()

    def save_file(self) -> None:
        if not self.current_file:
            messagebox.showwarning("Nothing to save", "Load a CSV first.")
            return

        suffix = self.suffix_var.get().strip()
        stem = self.current_file.stem + suffix
        out_path = OUTPUT_DIR / f"{stem}{self.current_file.suffix}"

        delim = getattr(self.dialect, "delimiter", ",")
        quotechar = getattr(self.dialect, "quotechar", '"')
        try:
            OUTPUT_DIR.mkdir(exist_ok=True)
            with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(
                    f,
                    delimiter=delim,
                    quotechar=quotechar,
                    quoting=csv.QUOTE_MINIMAL,
                )
                if self.has_header_var.get():
                    writer.writerow(self.headers)
                writer.writerows(self.data)
        except Exception as e:
            messagebox.showerror("Save", f"Failed to save:\n{e}")
            return

        self.modified = False
        messagebox.showinfo("Saved", f"Saved to:\n{out_path}")

    # --------------------------------------------------------- grid draw
    def _compute_column_widths(self) -> None:
        ncols = max(len(self.headers), max((len(r) for r in self.data), default=0))
        self.headers = self.headers + [""] * (ncols - len(self.headers))
        for i, r in enumerate(self.data):
            if len(r) < ncols:
                self.data[i] = r + [""] * (ncols - len(r))

        widths: list[int] = []
        for c in range(ncols):
            longest = self.headers[c] if c < len(self.headers) else ""
            for r in self.data[:300]:  # sample for performance
                cell = r[c]
                if len(cell) > len(longest):
                    longest = cell
            w = self.header_font.measure(longest) + CELL_PAD_X * 2
            widths.append(max(MIN_COL_WIDTH, min(MAX_COL_WIDTH, w)))

        self.col_widths = widths
        xs = [0]
        for w in widths:
            xs.append(xs[-1] + w)
        self.col_x = xs

    def _fit_text(self, text: str, max_width: int) -> str:
        if not text:
            return ""
        if self.cell_font.measure(text) <= max_width:
            return text
        ellipsis = "…"
        elps_w = self.cell_font.measure(ellipsis)
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.cell_font.measure(text[:mid]) + elps_w <= max_width:
                lo = mid
            else:
                hi = mid - 1
        return (text[:lo] + ellipsis) if lo > 0 else ellipsis

    def _redraw_all(self) -> None:
        self.canvas.delete("all")
        self.header_canvas.delete("all")
        self.rownum_canvas.delete("all")
        self.corner_canvas.delete("all")

        self.cell_rects.clear()
        self.cell_texts.clear()
        self.header_rects.clear()
        self.header_texts.clear()
        self.rownum_rects.clear()
        self.rownum_texts.clear()

        total_w = self.col_x[-1] if len(self.col_x) > 1 else 0
        total_h = CELL_HEIGHT * len(self.data)

        self.canvas.configure(scrollregion=(0, 0, total_w, total_h))
        self.header_canvas.configure(scrollregion=(0, 0, total_w, CELL_HEIGHT))
        self.rownum_canvas.configure(
            scrollregion=(0, 0, self.row_num_width, total_h)
        )

        # Corner ("select all")
        self.corner_canvas.create_rectangle(
            0, 0, self.row_num_width, CELL_HEIGHT, fill=CORNER_BG, outline=GRID_LINE
        )
        self.corner_canvas.create_text(
            self.row_num_width / 2,
            CELL_HEIGHT / 2,
            text="#",
            fill=HEADER_FG,
            font=self.header_font,
        )

        # Headers
        for c in range(len(self.headers)):
            self._draw_header_cell(c)

        # Rows + data cells
        for r in range(len(self.data)):
            self._draw_row_num(r)
            for c in range(len(self.headers)):
                self._draw_data_cell(r, c)

    def _draw_header_cell(self, c: int) -> None:
        x1 = self.col_x[c]
        x2 = self.col_x[c + 1]
        sel = (-1, c) in self.selected
        bg = HEADER_SEL_BG if sel else HEADER_BG
        rect = self.header_canvas.create_rectangle(
            x1, 0, x2, CELL_HEIGHT, fill=bg, outline=GRID_LINE
        )
        max_w = self.col_widths[c] - CELL_PAD_X * 2
        label = self._fit_text(self.headers[c], max_w)
        txt = self.header_canvas.create_text(
            x1 + CELL_PAD_X,
            CELL_HEIGHT / 2,
            text=label,
            anchor="w",
            fill=HEADER_FG,
            font=self.header_font,
        )
        self.header_rects[c] = rect
        self.header_texts[c] = txt

    def _draw_row_num(self, r: int) -> None:
        y1 = r * CELL_HEIGHT
        y2 = y1 + CELL_HEIGHT
        sel = self._row_fully_selected(r)
        bg = ROW_NUM_SEL_BG if sel else ROW_NUM_BG
        fg = ROW_NUM_SEL_FG if sel else ROW_NUM_FG
        rect = self.rownum_canvas.create_rectangle(
            0, y1, self.row_num_width, y2, fill=bg, outline=GRID_LINE
        )
        txt = self.rownum_canvas.create_text(
            self.row_num_width - CELL_PAD_X,
            y1 + CELL_HEIGHT / 2,
            text=str(r + 1),
            anchor="e",
            fill=fg,
            font=self.cell_font,
        )
        self.rownum_rects[r] = rect
        self.rownum_texts[r] = txt

    def _draw_data_cell(self, r: int, c: int) -> None:
        x1 = self.col_x[c]
        x2 = self.col_x[c + 1]
        y1 = r * CELL_HEIGHT
        y2 = y1 + CELL_HEIGHT
        sel = (r, c) in self.selected
        if sel:
            bg, fg = SELECTED_BG, SELECTED_FG
        else:
            bg = CELL_ALT_BG if (r % 2) else CELL_BG
            fg = CELL_FG
        rect = self.canvas.create_rectangle(
            x1, y1, x2, y2, fill=bg, outline=GRID_LINE
        )
        value = self.data[r][c] if c < len(self.data[r]) else ""
        max_w = self.col_widths[c] - CELL_PAD_X * 2
        display = self._fit_text(value, max_w)
        txt = self.canvas.create_text(
            x1 + CELL_PAD_X,
            y1 + CELL_HEIGHT / 2,
            text=display,
            anchor="w",
            fill=fg,
            font=self.cell_font,
        )
        self.cell_rects[(r, c)] = rect
        self.cell_texts[(r, c)] = txt

    # --------------------------------------------------------- helpers
    def _row_fully_selected(self, r: int) -> bool:
        if not self.headers:
            return False
        return all((r, c) in self.selected for c in range(len(self.headers)))

    def _update_cell_visuals(self, r: int, c: int) -> None:
        key = (r, c)
        if key not in self.cell_rects:
            return
        sel = key in self.selected
        if sel:
            bg, fg = SELECTED_BG, SELECTED_FG
        else:
            bg = CELL_ALT_BG if (r % 2) else CELL_BG
            fg = CELL_FG
        self.canvas.itemconfig(self.cell_rects[key], fill=bg)
        self.canvas.itemconfig(self.cell_texts[key], fill=fg)

    def _update_header_visuals(self, c: int) -> None:
        if c not in self.header_rects:
            return
        sel = (-1, c) in self.selected
        self.header_canvas.itemconfig(
            self.header_rects[c], fill=HEADER_SEL_BG if sel else HEADER_BG
        )

    def _update_rownum_visuals(self, r: int) -> None:
        if r not in self.rownum_rects:
            return
        sel = self._row_fully_selected(r)
        self.rownum_canvas.itemconfig(
            self.rownum_rects[r], fill=ROW_NUM_SEL_BG if sel else ROW_NUM_BG
        )
        self.rownum_canvas.itemconfig(
            self.rownum_texts[r], fill=ROW_NUM_SEL_FG if sel else ROW_NUM_FG
        )

    def _apply_selection_change(
        self, old: set[tuple[int, int]], new: set[tuple[int, int]]
    ) -> None:
        """Repaint only the cells whose selection state toggled."""
        diff = old.symmetric_difference(new)
        self.selected = new
        header_cols: set[int] = set()
        rows_touched: set[int] = set()
        for (r, c) in diff:
            if r == -1:
                header_cols.add(c)
            else:
                self._update_cell_visuals(r, c)
                rows_touched.add(r)
        for c in header_cols:
            self._update_header_visuals(c)
        for r in rows_touched:
            self._update_rownum_visuals(r)
        self._update_info()

    def _update_info(self) -> None:
        if self.current_file:
            dirty = " *" if self.modified else ""
            self.info_label.config(
                text=(
                    f"{self.current_file.name}{dirty}  "
                    f"({len(self.data)} rows × {len(self.headers)} cols)"
                )
            )
        else:
            self.info_label.config(text="No file loaded")
        self.sel_label.config(text=f"Selection: {len(self.selected)} cells")

    # --------------------------------------------------------- coord lookup
    def _find_col(self, x: float) -> int | None:
        if not self.col_widths:
            return None
        if x < 0 or x >= self.col_x[-1]:
            return None
        lo, hi = 0, len(self.col_widths) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if x < self.col_x[mid]:
                hi = mid - 1
            elif x >= self.col_x[mid + 1]:
                lo = mid + 1
            else:
                return mid
        return None

    def _event_to_cell(self, event: tk.Event) -> tuple[int, int] | None:
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        col = self._find_col(x)
        row = int(y // CELL_HEIGHT)
        if col is None or row < 0 or row >= len(self.data):
            return None
        return row, col

    # --------------------------------------------------------- mouse ops
    def _on_canvas_click(self, event: tk.Event) -> None:
        cell = self._event_to_cell(event)
        if cell is None:
            return
        new = {cell}
        self._apply_selection_change(self.selected, new)

    def _on_canvas_ctrl_click(self, event: tk.Event) -> None:
        cell = self._event_to_cell(event)
        if cell is None:
            return
        new = set(self.selected)
        if cell in new:
            new.discard(cell)
        else:
            new.add(cell)
        self._apply_selection_change(self.selected, new)

    def _on_canvas_shift_click(self, event: tk.Event) -> None:
        cell = self._event_to_cell(event)
        if cell is None:
            return
        new = set(self.selected)
        new.discard(cell)
        self._apply_selection_change(self.selected, new)

    # --- Header actions (selection) ----------------------------------
    def _do_header_select(self, col: int) -> None:
        new = {(r, col) for r in range(len(self.data))}
        if self.has_header_var.get():
            new.add((-1, col))
        self._apply_selection_change(self.selected, new)

    def _do_header_toggle(self, col: int) -> None:
        col_set = {(r, col) for r in range(len(self.data))}
        if self.has_header_var.get():
            col_set.add((-1, col))
        new = set(self.selected)
        if col_set.issubset(new):
            new -= col_set
        else:
            new |= col_set
        self._apply_selection_change(self.selected, new)

    def _do_header_drop_header(self, col: int) -> None:
        """Shift+click on a column header removes ONLY the header cell from
        the selection so operations apply to data rows only."""
        if not self.has_header_var.get():
            return
        if (-1, col) not in self.selected:
            return
        new = set(self.selected)
        new.discard((-1, col))
        self._apply_selection_change(self.selected, new)

    # --- Row-number actions (selection) -------------------------------
    def _do_rownum_select(self, row: int) -> None:
        new = {(row, c) for c in range(len(self.headers))}
        self._apply_selection_change(self.selected, new)

    def _do_rownum_toggle(self, row: int) -> None:
        row_set = {(row, c) for c in range(len(self.headers))}
        new = set(self.selected)
        if row_set.issubset(new):
            new -= row_set
        else:
            new |= row_set
        self._apply_selection_change(self.selected, new)

    def _do_rownum_remove(self, row: int) -> None:
        row_set = {(row, c) for c in range(len(self.headers))}
        new = set(self.selected) - row_set
        self._apply_selection_change(self.selected, new)

    # --- Press / Motion / Release: headers ----------------------------
    def _header_press(self, event: tk.Event) -> None:
        col = self._find_col(self.header_canvas.canvasx(event.x))
        if col is None:
            self._drag = None
            return
        ctrl = bool(event.state & 0x0004)
        shift = bool(event.state & 0x0001)
        if ctrl:
            self._do_header_toggle(col)
            self._drag = None
            return
        if shift:
            self._do_header_drop_header(col)
            self._drag = None
            return
        # defer until release — either click-to-select or drag-to-reorder
        self._drag = {
            "axis": "col",
            "from": col,
            "start_x": event.x,
            "active": False,
        }

    def _header_motion(self, event: tk.Event) -> None:
        d = self._drag
        if not d or d["axis"] != "col":
            return
        dx = abs(event.x - d["start_x"])
        if not d["active"]:
            if dx < 5:
                return
            d["active"] = True
        x = self.header_canvas.canvasx(event.x)
        pos = self._col_insertion_point(x)
        self._draw_col_drop_indicator(pos)

    def _header_release(self, event: tk.Event) -> None:
        d = self._drag
        if not d or d["axis"] != "col":
            return
        self._drag = None
        if d["active"]:
            x = self.header_canvas.canvasx(event.x)
            insert_pos = self._col_insertion_point(x)
            self._clear_drop_indicators()
            frm = d["from"]
            # Insertion index → destination column: removing frm first shifts
            # positions after it left by one.
            to = insert_pos - 1 if insert_pos > frm else insert_pos
            if to != frm:
                self.move_column(frm, to)
            return
        self._do_header_select(d["from"])

    # --- Press / Motion / Release: row numbers ------------------------
    def _rownum_press(self, event: tk.Event) -> None:
        y = self.rownum_canvas.canvasy(event.y)
        row = int(y // CELL_HEIGHT)
        if row < 0 or row >= len(self.data):
            self._drag = None
            return
        ctrl = bool(event.state & 0x0004)
        shift = bool(event.state & 0x0001)
        if ctrl:
            self._do_rownum_toggle(row)
            self._drag = None
            return
        if shift:
            self._do_rownum_remove(row)
            self._drag = None
            return
        self._drag = {
            "axis": "row",
            "from": row,
            "start_y": event.y,
            "active": False,
        }

    def _rownum_motion(self, event: tk.Event) -> None:
        d = self._drag
        if not d or d["axis"] != "row":
            return
        dy = abs(event.y - d["start_y"])
        if not d["active"]:
            if dy < 5:
                return
            d["active"] = True
        y = self.rownum_canvas.canvasy(event.y)
        pos = self._row_insertion_point(y)
        self._draw_row_drop_indicator(pos)

    def _rownum_release(self, event: tk.Event) -> None:
        d = self._drag
        if not d or d["axis"] != "row":
            return
        self._drag = None
        if d["active"]:
            y = self.rownum_canvas.canvasy(event.y)
            insert_pos = self._row_insertion_point(y)
            self._clear_drop_indicators()
            frm = d["from"]
            to = insert_pos - 1 if insert_pos > frm else insert_pos
            if to != frm:
                self.move_row(frm, to)
            return
        self._do_rownum_select(d["from"])

    # --- Drop indicator -----------------------------------------------
    def _col_insertion_point(self, x: float) -> int:
        if len(self.col_x) < 2:
            return 0
        for i in range(len(self.col_x) - 1):
            mid = (self.col_x[i] + self.col_x[i + 1]) / 2
            if x < mid:
                return i
        return len(self.col_x) - 1

    def _row_insertion_point(self, y: float) -> int:
        if not self.data:
            return 0
        idx = int((y + CELL_HEIGHT / 2) // CELL_HEIGHT)
        return max(0, min(len(self.data), idx))

    def _draw_col_drop_indicator(self, insertion_pos: int) -> None:
        self._clear_drop_indicators()
        x = (
            self.col_x[insertion_pos]
            if insertion_pos < len(self.col_x)
            else self.col_x[-1]
        )
        height = CELL_HEIGHT * max(1, len(self.data))
        lid = self.canvas.create_line(
            x, 0, x, height, fill=ACCENT, width=3
        )
        self._drop_line_ids.append((self.canvas, lid))
        hid = self.header_canvas.create_line(
            x, 0, x, CELL_HEIGHT, fill=ACCENT, width=3
        )
        self._drop_line_ids.append((self.header_canvas, hid))

    def _draw_row_drop_indicator(self, insertion_pos: int) -> None:
        self._clear_drop_indicators()
        y = insertion_pos * CELL_HEIGHT
        width = self.col_x[-1] if self.col_x else 0
        lid = self.canvas.create_line(
            0, y, width, y, fill=ACCENT, width=3
        )
        self._drop_line_ids.append((self.canvas, lid))
        rid = self.rownum_canvas.create_line(
            0, y, self.row_num_width, y, fill=ACCENT, width=3
        )
        self._drop_line_ids.append((self.rownum_canvas, rid))

    def _clear_drop_indicators(self) -> None:
        for canvas, item_id in self._drop_line_ids:
            try:
                canvas.delete(item_id)
            except Exception:
                pass
        self._drop_line_ids.clear()

    # --- Right-click context menus ------------------------------------
    def _make_menu(self) -> tk.Menu:
        return tk.Menu(
            self.root,
            tearoff=0,
            bg=BG_ELEV,
            fg=FG_DEFAULT,
            activebackground=ACCENT_BG,
            activeforeground="#ffffff",
            bd=0,
            relief="flat",
        )

    def _header_right_click(self, event: tk.Event) -> None:
        col = self._find_col(self.header_canvas.canvasx(event.x))
        if col is None:
            return
        name = self.headers[col] if self.headers else ""
        label_prefix = name if name else f"Col {col + 1}"
        m = self._make_menu()
        m.add_command(
            label=f"Select Column ({label_prefix})",
            command=lambda c=col: self._do_header_select(c),
        )
        m.add_separator()
        if self.has_header_var.get():
            m.add_command(
                label="Rename Column…",
                command=lambda c=col: self.rename_column(c),
            )
        m.add_command(
            label="Duplicate Column",
            command=lambda c=col: self.duplicate_column(c),
        )
        m.add_separator()
        m.add_command(
            label="Insert Empty Column Before",
            command=lambda c=col: self.insert_column(c),
        )
        m.add_command(
            label="Insert Empty Column After",
            command=lambda c=col: self.insert_column(c + 1),
        )
        m.add_separator()
        m.add_command(
            label="Move Column Left",
            command=lambda c=col: self.move_column(c, c - 1),
            state="normal" if col > 0 else "disabled",
        )
        m.add_command(
            label="Move Column Right",
            command=lambda c=col: self.move_column(c, c + 1),
            state="normal" if col < len(self.headers) - 1 else "disabled",
        )
        m.add_separator()
        m.add_command(
            label="Delete Column",
            command=lambda c=col: self.delete_column(c),
        )
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    def _rownum_right_click(self, event: tk.Event) -> None:
        y = self.rownum_canvas.canvasy(event.y)
        row = int(y // CELL_HEIGHT)
        if row < 0 or row >= len(self.data):
            return
        m = self._make_menu()
        m.add_command(
            label=f"Select Row {row + 1}",
            command=lambda r=row: self._do_rownum_select(r),
        )
        m.add_separator()
        m.add_command(
            label="Duplicate Row",
            command=lambda r=row: self.duplicate_row(r),
        )
        m.add_separator()
        m.add_command(
            label="Insert Empty Row Above",
            command=lambda r=row: self.insert_row(r),
        )
        m.add_command(
            label="Insert Empty Row Below",
            command=lambda r=row: self.insert_row(r + 1),
        )
        m.add_separator()
        m.add_command(
            label="Move Row Up",
            command=lambda r=row: self.move_row(r, r - 1),
            state="normal" if row > 0 else "disabled",
        )
        m.add_command(
            label="Move Row Down",
            command=lambda r=row: self.move_row(r, r + 1),
            state="normal" if row < len(self.data) - 1 else "disabled",
        )
        m.add_separator()
        m.add_command(
            label="Delete Row",
            command=lambda r=row: self.delete_row(r),
        )
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    # --- Structural operations: columns -------------------------------
    def insert_column(self, at: int, name: str = "New") -> None:
        if not self.headers and not self.data:
            # create a brand-new sheet with one column
            self._snapshot()
            self.headers = [name]
            self.data = [[""]]
        else:
            n = len(self.headers)
            at = max(0, min(at, n))
            self._snapshot()
            self.headers.insert(at, name)
            for row in self.data:
                row.insert(at, "")
        self.selected.clear()
        self.modified = True
        self._compute_column_widths()
        self._redraw_all()
        self._update_info()

    def delete_column(self, col: int) -> None:
        if col < 0 or col >= len(self.headers):
            return
        if len(self.headers) <= 1:
            messagebox.showwarning(
                "Delete Column", "Cannot delete the last remaining column."
            )
            return
        self._snapshot()
        self.headers.pop(col)
        for row in self.data:
            if col < len(row):
                row.pop(col)
        self.selected.clear()
        self.modified = True
        self._compute_column_widths()
        self._redraw_all()
        self._update_info()

    def duplicate_column(self, col: int) -> None:
        if col < 0 or col >= len(self.headers):
            return
        self._snapshot()
        label = self.headers[col]
        self.headers.insert(col + 1, f"{label} (copy)" if label else "")
        for row in self.data:
            row.insert(col + 1, row[col] if col < len(row) else "")
        self.selected.clear()
        self.modified = True
        self._compute_column_widths()
        self._redraw_all()
        self._update_info()

    def move_column(self, frm: int, to: int) -> None:
        n = len(self.headers)
        if n == 0 or frm < 0 or frm >= n:
            return
        to = max(0, min(to, n - 1))
        if to == frm:
            return
        self._snapshot()
        h = self.headers.pop(frm)
        self.headers.insert(to, h)
        for row in self.data:
            v = row.pop(frm) if frm < len(row) else ""
            row.insert(to, v)
        self.selected.clear()
        self.modified = True
        self._compute_column_widths()
        self._redraw_all()
        self._update_info()

    def rename_column(self, col: int) -> None:
        if col < 0 or col >= len(self.headers):
            return
        if not self.has_header_var.get():
            messagebox.showinfo(
                "Rename Column",
                "Turn on 'First row is header' first so that column names "
                "are part of the saved file.",
            )
            return
        new = simpledialog.askstring(
            "Rename Column",
            f"New name for column {col + 1}:",
            initialvalue=self.headers[col],
            parent=self.root,
        )
        if new is None:
            return
        self._snapshot()
        self.headers[col] = new
        self.modified = True
        self._compute_column_widths()
        self._redraw_all()
        self._update_info()

    # --- Structural operations: rows ---------------------------------
    def insert_row(self, at: int) -> None:
        ncols = len(self.headers) if self.headers else 1
        at = max(0, min(at, len(self.data)))
        self._snapshot()
        self.data.insert(at, [""] * ncols)
        self.selected.clear()
        self.modified = True
        self._redraw_all()
        self._update_info()

    def delete_row(self, row: int) -> None:
        if row < 0 or row >= len(self.data):
            return
        self._snapshot()
        self.data.pop(row)
        self.selected.clear()
        self.modified = True
        self._redraw_all()
        self._update_info()

    def duplicate_row(self, row: int) -> None:
        if row < 0 or row >= len(self.data):
            return
        self._snapshot()
        self.data.insert(row + 1, list(self.data[row]))
        self.selected.clear()
        self.modified = True
        self._redraw_all()
        self._update_info()

    def move_row(self, frm: int, to: int) -> None:
        n = len(self.data)
        if n == 0 or frm < 0 or frm >= n:
            return
        to = max(0, min(to, n - 1))
        if to == frm:
            return
        self._snapshot()
        r = self.data.pop(frm)
        self.data.insert(to, r)
        self.selected.clear()
        self.modified = True
        self._redraw_all()
        self._update_info()

    # --- Has-header toggle --------------------------------------------
    def _on_has_header_toggle(self) -> None:
        if not self.headers and not self.data:
            return
        self._snapshot()
        if self.has_header_var.get():
            # Turning ON: promote first data row to header
            if self.data:
                self.headers = list(self.data[0])
                self.data = self.data[1:]
        else:
            # Turning OFF: demote current headers to first data row
            self.data.insert(0, list(self.headers))
            self.headers = [f"Col {i + 1}" for i in range(len(self.headers))]
        # Selection references may no longer make sense; clear them.
        self.selected.clear()
        self.modified = True
        self._compute_column_widths()
        self._redraw_all()
        self._update_info()

    # --------------------------------------------------------- selection ops
    def select_all(self) -> None:
        if not self.headers:
            return
        new = {
            (r, c)
            for r in range(-1, len(self.data))
            for c in range(len(self.headers))
        }
        self._apply_selection_change(self.selected, new)

    def clear_selection(self) -> None:
        self._apply_selection_change(self.selected, set())

    def invert_selection(self) -> None:
        if not self.headers:
            return
        universe = {
            (r, c)
            for r in range(-1, len(self.data))
            for c in range(len(self.headers))
        }
        self._apply_selection_change(self.selected, universe - self.selected)

    # --------------------------------------------------------- data edit
    def _get_cell(self, r: int, c: int) -> str:
        return self.headers[c] if r == -1 else self.data[r][c]

    def _set_cell(self, r: int, c: int, value: str) -> None:
        if r == -1:
            self.headers[c] = value
        else:
            self.data[r][c] = value

    def _snapshot(self) -> None:
        has_header = bool(
            getattr(self, "has_header_var", None) and self.has_header_var.get()
        )
        self.undo_stack.append(
            (
                [h for h in self.headers],
                [row[:] for row in self.data],
                has_header,
            )
        )
        if len(self.undo_stack) > 40:
            self.undo_stack.pop(0)

    def undo(self) -> None:
        if not self.undo_stack:
            messagebox.showinfo("Undo", "Nothing to undo.")
            return
        entry = self.undo_stack.pop()
        headers, data = entry[0], entry[1]
        has_header = entry[2] if len(entry) > 2 else True
        self.headers = headers
        self.data = data
        if hasattr(self, "has_header_var"):
            self.has_header_var.set(has_header)
        self.modified = True
        self.selected.clear()
        self._compute_column_widths()
        self._redraw_all()
        self._update_info()

    def _require_selection(self) -> bool:
        if not self.selected:
            messagebox.showwarning(
                "No selection",
                "Select at least one cell, row, or column first.\n\n"
                "• Click a column header to select a column\n"
                "• Click a row number to select a row\n"
                "• Ctrl+click to toggle  •  Shift+click to remove from selection",
            )
            return False
        return True

    def _require_text(self, var: tk.StringVar, field: str) -> str | None:
        value = var.get()
        if value == "":
            messagebox.showwarning("Missing input", f"Please type something in '{field}'.")
            return None
        return value

    def _apply_to_selection(self, transform) -> None:
        if not self._require_selection():
            return
        self._snapshot()
        affected_rows: set[int] = set()
        affected_cols: set[int] = set()
        for (r, c) in self.selected:
            new_val = transform(self._get_cell(r, c))
            self._set_cell(r, c, new_val)
            if r == -1:
                affected_cols.add(c)
            else:
                affected_rows.add(r)
        self.modified = True
        self._refresh_cell_text_for(self.selected)
        self._update_info()

    def _refresh_cell_text_for(self, cells: set[tuple[int, int]]) -> None:
        for (r, c) in cells:
            if r == -1:
                if c in self.header_texts:
                    max_w = self.col_widths[c] - CELL_PAD_X * 2
                    self.header_canvas.itemconfig(
                        self.header_texts[c], text=self._fit_text(self.headers[c], max_w)
                    )
            else:
                if (r, c) in self.cell_texts:
                    max_w = self.col_widths[c] - CELL_PAD_X * 2
                    self.canvas.itemconfig(
                        self.cell_texts[(r, c)],
                        text=self._fit_text(self.data[r][c], max_w),
                    )

    def _overwrite_if_enabled(self) -> bool:
        """If Overwrite mode is on, replace every selected cell with the Text
        field value and return True. Otherwise return False so the caller can
        run its normal behaviour. Always requires a non-empty Text value so we
        never silently wipe the whole selection.
        """
        if not self.overwrite_var.get():
            return False
        text = self._require_text(self.text_var, "Text")
        if text is None:
            return True  # handled (warning was shown, abort caller)
        self._apply_to_selection(lambda _v: text)
        return True

    def op_add_before(self) -> None:
        if self._overwrite_if_enabled():
            return
        text = self._require_text(self.text_var, "Text")
        if text is None:
            return
        self._apply_to_selection(lambda v: text + v)

    def op_add_after(self) -> None:
        if self._overwrite_if_enabled():
            return
        text = self._require_text(self.text_var, "Text")
        if text is None:
            return
        self._apply_to_selection(lambda v: v + text)

    def op_replace(self) -> None:
        if self._overwrite_if_enabled():
            return
        find = self._require_text(self.text_var, "Text")
        if find is None:
            return
        replace = self.replace_var.get()  # empty => remove
        self._apply_to_selection(lambda v: v.replace(find, replace))

    def op_trim_start(self) -> None:
        if not self._require_selection():
            return
        n = simpledialog.askinteger(
            "Trim Start",
            "Remove how many characters from the START of each selected cell?",
            minvalue=1,
            parent=self.root,
        )
        if not n:
            return
        self._apply_to_selection(lambda v: v[n:])

    def op_trim_end(self) -> None:
        if not self._require_selection():
            return
        n = simpledialog.askinteger(
            "Trim End",
            "Remove how many characters from the END of each selected cell?",
            minvalue=1,
            parent=self.root,
        )
        if not n:
            return
        self._apply_to_selection(lambda v: v[:-n] if n < len(v) else "")


def main() -> None:
    root = tk.Tk()
    CSVTool(root)
    root.mainloop()


if __name__ == "__main__":
    main()
