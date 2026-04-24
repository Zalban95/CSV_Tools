# CSV Tools — Batch text editor for CSV columns and rows

A tiny Windows GUI tool that lets you:

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
- Save the result to the `output/` folder (same filename, original delimiter and encoding preserved).

Ships in a dark theme.

Runs on Python 3.10+ using only the standard library (`tkinter`), so no installation is needed beyond Python itself.

---

## Running it

Double-click `CSV_Tools.bat`, or from a terminal:

```
python csv_tool.py
```

## Folder layout

```
CSV_Tools/
├── csv_tool.py        the application
├── CSV_Tools.bat      Windows launcher
├── input/             drop your CSVs here
└── output/            saved results land here
```

## Selection cheat sheet

| Action                                       | Mouse gesture                              |
|----------------------------------------------|--------------------------------------------|
| Select one cell                              | Click the cell                             |
| Select an entire column (incl. its header)   | Click the column header                    |
| Select an entire row                         | Click the row number on the left           |
| Select the whole sheet                       | Click the top-left "#" corner or `Ctrl+A` |
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

All structural operations are **undoable** (Ctrl+Z).

### First-row-is-header toggle
The sidebar's **First row is header** checkbox controls whether the top row is
treated as a header:

- **On** (default): the first row of the CSV is a header. It's shown in a
  distinct style at the top, you can `Rename Column…` it, and it's written
  back out as the first line when you save.
- **Off**: the top row shows generic `Col 1`, `Col 2`, … labels. Every line
  from the file is treated as data, and nothing extra is prepended when saving.

Toggling promotes/demotes rows as needed so nothing gets lost: turning the
switch **off** prepends the current header as the new first data row; turning
it back **on** promotes whatever is currently the first data row to header.

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

## Saving

Press **Save to Output** (or `Ctrl+S`). The file is written to `output/<original-name>.csv`.
You can add a suffix (e.g. `_v2`) in the sidebar before saving to avoid overwriting.

## Examples

- **Add `MAT-` to every article code:** Click the `ArticleCode` header → type `MAT-` in *Text* → click **Add Before**.
- **Remove trailing `L` from the first column, except for one row:** Click the column header, then `Shift`+click the specific cell you want to keep untouched → set *Text* to `L` and *Replace with* empty → click **Replace**. (Or use **Trim End N** with N=1 for a strict one-character chop.)
- **Append `mm` to every length value:** Click the `Length` header → type `mm` → **Add After**.
