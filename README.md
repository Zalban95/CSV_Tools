# CSV Tools — Batch text editor for CSV columns and rows

A small, portable cross-platform GUI tool ([protolab.tech](https://protolab.tech))
that lets you:

- Pick a CSV from the `input/` folder.
- Select whole **columns** (click the header) or whole **rows** (click the row number).
- **Un-select** specific cells/rows/columns from the selection without losing the rest.
- Add text **before** (prefix) or **after** (suffix) each selected cell's current value.
- **Replace** or **remove** a piece of text.
- **Overwrite** every selected cell with a specific value (via the Overwrite toggle).
- **Trim** a fixed number of characters from the start or end of each selected cell.
- **Reorder** columns or rows by **dragging** their header / row number.
- **Right-click** any column header or row number for a menu with
  *Duplicate / Insert Before / Insert After / Move / Rename / Delete*.
- Toggle whether the **first row is a header** (sidebar checkbox). When off,
  the file is saved without a header line and generic `Col 1`, `Col 2`, …
  labels are used in the UI.
- **Confirm before destructive actions** (column/row delete, header flip,
  overwriting an existing output file) — a toolbar checkbox lets power-users
  turn these prompts off.
- Save the result to the `output/` folder (same filename, original delimiter and encoding preserved).

Dark theme, single-file, no third-party runtime dependencies.

---

## System requirements

| Target                      | What you need                                                            |
|-----------------------------|---------------------------------------------------------------------------|
| **Run from source** (any OS) | Python **3.10+** with the standard `tkinter` module                      |
| **Run as a `.exe`** (Windows) | Nothing — the bundled executable has no runtime dependency               |

The app itself imports only the Python standard library
(`tkinter`, `csv`, `os`, `sys`, `pathlib`, `webbrowser`). Nothing to
`pip install` for normal use.

Tested on Windows 10/11. The `.py` also runs fine on macOS and modern Linux
distributions with Python 3.10+ and Tk installed.

## Running it

### From source (Windows / macOS / Linux)

Double-click `CSV_Tools.bat` on Windows, or from any terminal:

```
python csv_tool.py
```

(Use `python3` on macOS/Linux if that's what your system calls it.)

### As a single-file executable (Windows)

If you don't want to install Python on a target machine, build a standalone
`.exe` once on a developer machine and copy it anywhere:

```
build_windows.bat
```

This produces `dist\CSV_Tools.exe` (≈ 15–25 MB). The `.exe` is fully
self-contained. On first launch it creates `input/` and `output/` folders
**next to the executable**, so just drop the `.exe` into any folder and go.

To build on macOS or Linux instead:

```
./build_unix.sh
```

`build_windows.bat` creates a private `.venv\` and installs PyInstaller
there (your system Python is left untouched); `build_unix.sh` installs it into
the current Python environment. PyInstaller is the **only** build-time
dependency — it is never required at runtime. `.venv/`, `build/` and `dist/`
are git-ignored.

**Portable use:** copy `dist\CSV_Tools.exe` to any folder (or USB stick) on a
Windows machine and double-click it. No Python, no install, no admin rights.

### Installer (optional, Windows)

If [Inno Setup 6](https://jrsoftware.org/isinfo.php) is installed
(`winget install JRSoftware.InnoSetup`, no admin needed), `build_windows.bat`
also produces `dist\CSV_Tools_Setup.exe` from `installer.iss`. You can also
run `iscc installer.iss` yourself after building the `.exe`. The setup
installs per-user (no admin prompt) into `%LOCALAPPDATA%\Programs\CSV_Tools`,
adds Start-menu entries (app, input/output folders, uninstall) and an optional
desktop shortcut, and registers an uninstaller in *Apps & features*.
Uninstalling leaves your `input\`/`output\` CSVs in place.

## Folder layout

```
CSV_Tools/
├── csv_tool.py        the application (single file, stdlib only)
├── CSV_Tools.bat      Windows launcher (uses pythonw so no console pops up)
├── CSV_Tools.spec     PyInstaller recipe
├── build_windows.bat  one-click Windows .exe build
├── build_unix.sh      macOS / Linux build
├── installer.iss      Inno Setup script (optional Windows installer)
├── README.md          this file (also shown by the in-app Info button)
├── input/             drop your CSVs here
└── output/            saved results land here
```

## Selection cheat sheet

| Action                                       | Mouse gesture                              |
|----------------------------------------------|--------------------------------------------|
| Select one cell                              | Click the cell                             |
| Select an entire column (incl. its header)   | Click the column header                    |
| Select an entire row                         | Click the row number on the left           |
| Select the whole sheet                       | Click the top-left "#" corner or `Ctrl+A`  |
| Toggle a whole column                        | `Ctrl`+click the column header             |
| Toggle a whole row                           | `Ctrl`+click the row number                |
| Toggle a single cell                         | `Ctrl`+click the cell                      |
| **Un-select just the header cell**           | `Shift`+click the column header            |
| Un-select a single data cell                 | `Shift`+click the cell                     |
| Un-select a whole row                        | `Shift`+click the row number               |
| Clear the selection                          | `Esc`                                      |
| Invert selection                             | "Invert Sel." button                       |

> **Tip:** To prefix every value in a column without changing its header name,
> click the column header (selects column + header), then `Shift`+click the
> same header to drop just the header cell, then hit **Add Before**.

## Moving, copying and reshaping the sheet

### Drag-and-drop
- **Drag a column header** sideways to reorder the column. A blue line shows
  the drop position. Drop between any two columns to slot it in.
- **Drag a row number** up or down to reorder a row. Same blue drop indicator.
- Dragging is only activated after you move more than ~5 px; short clicks
  still work as "select that column/row".

### Right-click menus
Right-click a **column header** for:
- Select Column
- Rename Column… (only when "First row is header" is on)
- Duplicate Column *(inserts a copy to the right, suffixed with `(copy)`)*
- Insert Empty Column Before / After
- Move Column Left / Right
- Delete Column

Right-click a **row number** for:
- Select Row
- Duplicate Row *(inserts a copy immediately below)*
- Insert Empty Row Above / Below
- Move Row Up / Down
- Delete Row

All structural operations are **undoable** (Ctrl+Z, up to 40 steps).

### First-row-is-header toggle
The sidebar's **First row is header** checkbox controls whether the top row is
treated as a header:

- **On** (default): the first row of the CSV is a header. It's shown in a
  distinct style at the top, you can `Rename Column…` it, and it's written
  back out as the first line when you save.
- **Off**: the top row shows generic `Col 1`, `Col 2`, … labels. Every line
  from the file is treated as data, and nothing extra is prepended when saving.

Flipping this checkbox asks for confirmation (it moves rows around) and is
fully undoable — turning the switch **off** prepends the current header as the
new first data row; turning it back **on** promotes whatever is currently the
first data row to header.

## Operation cheat sheet

1. Make a selection.
2. Type text into the **Text** (and optionally **Replace with**) fields.
3. Click one of the buttons:

| Button          | What it does (on every selected cell)               |
|-----------------|------------------------------------------------------|
| **Add Before**  | Prepends the *Text* to the current cell value       |
| **Add After**   | Appends the *Text* to the current cell value        |
| **Replace**     | Replaces every occurrence of *Text* with *Replace with* (leave *Replace with* empty to simply delete it) |
| **Trim Start N**| Removes N leading characters                         |
| **Trim End N**  | Removes N trailing characters                        |
| **Undo** / `Ctrl+Z` | Reverts the last operation (up to 40 steps)      |

### Overwrite mode

Tick the **Overwrite** checkbox in the toolbar to change the behaviour of
**Add Before**, **Add After** and **Replace**: instead of modifying the
existing text, each of those three buttons will replace the whole content of
every selected cell with whatever is in the **Text** box. The hint bar turns
blue while the mode is active so you can't miss it. Uncheck it to return to
the regular add / replace behaviour.

Typical usage: select the column(s) or rows you want to overwrite → type the
target value in **Text** → tick **Overwrite** → hit any of the three buttons.

### Confirm destructive actions

By default the app prompts before:

- deleting a column,
- deleting a row,
- flipping the **First row is header** switch (because it shifts rows),
- overwriting an existing file in `output/`.

Untick **Confirm destructive** in the toolbar to silence the prompts once
you're comfortable with the flow. The setting is in-session only, so a
freshly-opened window always starts safe.

## Saving

Press **Save to Output** (or `Ctrl+S`). The file is written to
`output/<original-name>.csv`. You can add a suffix (e.g. `_v2`) in the sidebar
before saving to avoid overwriting. If the target already exists and
confirmations are enabled, you will be asked before overwrite.

## Keyboard shortcuts

| Shortcut            | Action                          |
|---------------------|---------------------------------|
| `Ctrl+A`            | Select everything               |
| `Ctrl+S`            | Save to output                  |
| `Ctrl+Z`            | Undo last change                |
| `Esc`               | Clear the current selection     |
| `F1`                | Open the in-app Info / README   |

## Examples

- **Add `MAT-` to every article code:** Click the `ArticleCode` header → type
  `MAT-` in *Text* → click **Add Before**.
- **Remove trailing `L` from the first column, except for one row:** Click the
  column header, then `Shift`+click the specific cell you want to keep
  untouched → set *Text* to `L` and *Replace with* empty → click **Replace**.
  (Or use **Trim End N** with N=1 for a strict one-character chop.)
- **Append `mm` to every length value:** Click the `Length` header → type
  `mm` → **Add After**.

---

Made by [protolab.tech](https://protolab.tech).
