"""mumbledtoken: M∞ v0.2 compaction, restoration, and key dictionary."""
from __future__ import annotations

import base64
import json
import sys
import tkinter as tk
import zlib
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

APP_TITLE = "mumbledtoken"
APP_VERSION = "1.7"
MAGIC = b"M1"
MODE_REF, MODE_ZLIB, MODE_RAW = b"R", b"Z", b"J"
PREFIX = "M∞0.2:"
MAX_DATA_BYTES = 64 * 1024 * 1024


def app_folder() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent


def load_default_key_text() -> str:
    path = app_folder() / "mumbledtoken_dictionary.json"
    try:
        return path.read_text(encoding="utf-8-sig")
    except OSError:
        return json.dumps({"shared_key": {}}, ensure_ascii=False, indent=2)


def load_lcl_spec_text() -> str:
    path = app_folder() / "lcl_specification.md"
    raw = path.read_bytes()
    if raw.startswith(b'\xff\xfe'):
        return '\ufeff' + raw[2:].decode('utf-16-le')
    if raw.startswith(b'\xfe\xff'):
        return '\ufeff' + raw[2:].decode('utf-16-be')
    if raw.startswith(b'\xef\xbb\xbf'):
        return '\ufeff' + raw[3:].decode('utf-8')
    return raw.decode('utf-8')

def load_ai_key_text() -> str:
    return (app_folder() / "lcl_ai_key.txt").read_text(encoding="utf-8-sig")

def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


class MInfinityCodec:
    """M∞ v0.2 codec for caller-supplied JSON-compatible values."""
    def __init__(self, shared_key: dict[str, Any] | None = None, level: int = 9):
        self.shared_key = shared_key or {}
        self.level = level
        self._reverse = {canonical_bytes(value): key for key, value in self.shared_key.items()}

    def encode(self, meaning: Any) -> bytes:
        raw = canonical_bytes(meaning)
        if len(raw) > MAX_DATA_BYTES:
            raise ValueError("Content exceeds the 64 MiB limit.")
        candidates = [(MAGIC + MODE_RAW + len(raw).to_bytes(4, "big") + raw, "direct")]
        compressed = zlib.compress(raw, self.level)
        candidates.append((MAGIC + MODE_ZLIB + len(raw).to_bytes(4, "big") + compressed, "compact JSON"))
        key_id = self._reverse.get(raw)
        if key_id is not None:
            ident = key_id.encode("utf-8")
            if len(ident) <= 65535:
                candidates.append((MAGIC + MODE_REF + len(ident).to_bytes(2, "big") + ident, "shared key"))
        return min(candidates, key=lambda item: len(item[0]))[0]

    def decode(self, payload: bytes) -> Any:
        if not payload.startswith(MAGIC) or len(payload) < 3:
            raise ValueError("This is not an M∞ v0.2 message.")
        mode = payload[2:3]
        if mode == MODE_REF:
            if len(payload) < 5:
                raise ValueError("The shared-key entry is incomplete.")
            size = int.from_bytes(payload[3:5], "big")
            if len(payload) != 5 + size:
                raise ValueError("The shared-key message is incomplete or has extra data.")
            ident = payload[5:].decode("utf-8")
            if ident not in self.shared_key:
                raise KeyError(f"This key does not contain the entry '{ident}'.")
            return self.shared_key[ident]
        if mode not in (MODE_RAW, MODE_ZLIB) or len(payload) < 7:
            raise ValueError("This M∞ message has an unknown format.")
        expected = int.from_bytes(payload[3:7], "big")
        if expected > MAX_DATA_BYTES:
            raise ValueError("The M∞ message exceeds the 64 MiB limit.")
        if mode == MODE_RAW:
            data = payload[7:]
        else:
            inflater = zlib.decompressobj()
            data = inflater.decompress(payload[7:], MAX_DATA_BYTES + 1)
            if len(data) > MAX_DATA_BYTES or inflater.unconsumed_tail or not inflater.eof or inflater.unused_data:
                raise ValueError("The compacted message is incomplete or too large.")
            data += inflater.flush()
        if len(data) != expected:
            raise ValueError("The restored content does not match its stored length.")
        return json.loads(data.decode("utf-8"))


def read_shared_key(text: str) -> dict[str, Any]:
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("The key must be a JSON object.")
    shared = value.get("shared_key", value)
    if not isinstance(shared, dict) or any(not isinstance(key, str) for key in shared):
        raise ValueError("The key must map text IDs to JSON values.")
    canonical_bytes(shared)
    return shared


def compact_text(text: str, shared_key: dict[str, Any]) -> tuple[str, str]:
    # Preserve entered text exactly. A key reference is allowed only for a full JSON value match.
    meaning: Any = text
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    else:
        try:
            canonical = canonical_bytes(parsed)
            if text.encode("utf-8") == canonical and any(canonical_bytes(value) == canonical for value in shared_key.values()):
                meaning = parsed
        except (TypeError, ValueError):
            pass
    payload = MInfinityCodec(shared_key).encode(meaning)
    mode = {MODE_RAW: "direct JSON", MODE_ZLIB: "compact text", MODE_REF: "shared key"}[payload[2:3]]
    return PREFIX + base64.b64encode(payload).decode("ascii"), mode
def restore_text(text: str, shared_key: dict[str, Any]) -> str:
    value = "".join(text.split())
    if value.startswith(PREFIX):
        value = value[len(PREFIX):]
    try:
        payload = base64.b64decode(value, validate=True)
    except Exception as exc:
        raise ValueError("This does not look like an M∞ v0.2 message.") from exc
    result = MInfinityCodec(shared_key).decode(payload)
    return result if isinstance(result, str) else canonical_bytes(result).decode("utf-8")


class MumbledTokenApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_TITLE} {APP_VERSION}")
        self.geometry("920x780")
        self.minsize(700, 580)
        self.configure(bg="#10110f")
        self._style()
        self._build()

    def _style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#10110f")
        style.configure("TLabel", background="#10110f", foreground="#eceee6", font=("Segoe UI", 10))
        style.configure("Muted.TLabel", foreground="#9aa08f", font=("Segoe UI", 9))
        style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"), foreground="#c7f36b")
        style.configure("TNotebook", background="#10110f", borderwidth=0)
        style.configure("TNotebook.Tab", background="#1c1e1a", foreground="#a6ad9a", padding=(18, 9))
        style.map("TNotebook.Tab", background=[("selected", "#29321e")], foreground=[("selected", "#c7f36b")])
        style.configure("Primary.TButton", background="#c7f36b", foreground="#171b10", padding=(12, 8), font=("Segoe UI", 10, "bold"))
        style.map("Primary.TButton", background=[("active", "#d6fb8b")])
        style.configure("TButton", background="#252821", foreground="#e2e5da", padding=(10, 7))

    def _text(self, parent: tk.Widget, height: int = 10, state: str = "normal") -> tk.Text:
        return tk.Text(parent, height=height, wrap="word", undo=True, bg="#141512", fg="#e2e5da",
                       insertbackground="#c7f36b", selectbackground="#526b34", relief="flat",
                       padx=12, pady=10, font=("Consolas", 10), state=state)

    def _build(self) -> None:
        outer = ttk.Frame(self, padding=20); outer.pack(fill="both", expand=True)
        ttk.Label(outer, text=APP_TITLE, style="Title.TLabel").pack(anchor="w")
        ttk.Label(outer, text="Compact JSON or text, restore it later, and keep the same shared key on both sides.", style="Muted.TLabel").pack(anchor="w", pady=(2, 15))
        tabs = ttk.Notebook(outer); tabs.pack(fill="both", expand=True)
        compact_tab, restore_tab, key_tab = (ttk.Frame(tabs, padding=15) for _ in range(3))
        tabs.add(compact_tab, text="Compact"); tabs.add(restore_tab, text="Reconstruct"); tabs.add(key_tab, text="AI Key (.txt)")
        self._build_compact(compact_tab); self._build_restore(restore_tab); self._build_key(key_tab)
        ttk.Label(outer, text="For key-based messages, keep the same dictionary on both sides.", style="Muted.TLabel").pack(anchor="w", pady=(12, 0))

    def _build_compact(self, parent: ttk.Frame) -> None:
        source_header = ttk.Frame(parent); source_header.pack(fill="x")
        ttk.Label(source_header, text="JSON content or plain text").pack(side="left", anchor="w")
        ttk.Button(source_header, text="Upload .txt file…", command=self._load_text_file).pack(side="right")
        self.source = self._text(parent, 12); self.source.pack(fill="both", expand=True, pady=(6, 12))
        self.source.insert("1.0", canonical_bytes(read_shared_key(load_default_key_text()).get("E17", {})).decode("utf-8"))
        ttk.Button(parent, text="Compact", style="Primary.TButton", command=self._compact).pack(anchor="w", pady=(0, 8))
        ttk.Label(parent, text="Compact M∞ message").pack(anchor="w")
        self.compacted = self._text(parent, 8, "disabled"); self.compacted.pack(fill="both", expand=True, pady=(6, 8))
        self.compact_stats = ttk.Label(parent, text="", style="Muted.TLabel"); self.compact_stats.pack(anchor="w", pady=(0, 8))
        row = ttk.Frame(parent); row.pack(fill="x")
        ttk.Button(row, text="Copy message", command=lambda: self._copy(self.compacted)).pack(side="left", padx=(0, 8))
        ttk.Button(row, text="Save message…", command=self._save_package).pack(side="left")

    def _build_restore(self, parent: ttk.Frame) -> None:
        top = ttk.Frame(parent); top.pack(fill="x")
        ttk.Label(top, text="Paste an M∞ message or open a saved .m1 file").pack(side="left", anchor="w")
        ttk.Button(top, text="Open file…", command=self._load_package).pack(side="right")
        ttk.Button(top, text="Paste", command=lambda: self._paste_into(self.package)).pack(side="right", padx=(0, 8))
        self.package = self._text(parent, 12); self.package.pack(fill="both", expand=True, pady=(6, 12))
        self.package.bind("<Control-v>", self._paste_restore_shortcut)
        self.package.bind("<Control-V>", self._paste_restore_shortcut)
        self.package.bind("<Shift-Insert>", self._paste_restore_shortcut)
        ttk.Button(parent, text="Restore content", style="Primary.TButton", command=self._restore).pack(anchor="w", pady=(0, 10))
        ttk.Label(parent, text="Restored content").pack(anchor="w")
        self.restored = self._text(parent, 12, "disabled"); self.restored.pack(fill="both", expand=True, pady=(6, 8))
        ttk.Button(parent, text="Copy restored content", command=lambda: self._copy(self.restored)).pack(anchor="w")

    def _build_key(self, parent: ttk.Frame) -> None:
        self.ai_key_text = load_ai_key_text()
        self.key_text = self._text(parent, 25); self.key_text.pack(fill="both", expand=True)
        self.key_text.insert("1.0", self.ai_key_text)
        self.key_text.configure(state="disabled")
        ttk.Button(parent, text="Download .txt", style="Primary.TButton", command=self._download_ai_key).pack(anchor="w", pady=(8, 0))

    def _download_ai_key(self) -> None:
        path = filedialog.asksaveasfilename(parent=self, title="Download AI key", initialfile="lcl_ai_key.txt", defaultextension=".txt", filetypes=[("Text file", "*.txt")])
        if path:
            with open(path, "w", encoding="utf-8", newline="") as file:
                file.write(self.ai_key_text)
    def _current_key(self) -> dict[str, Any]:
        return read_shared_key(load_default_key_text())

    def _load_text_file(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Choose a text file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            raw = Path(path).read_bytes()
            if raw.startswith(b'\xff\xfe'):
                content = '\ufeff' + raw[2:].decode('utf-16-le')
            elif raw.startswith(b'\xfe\xff'):
                content = '\ufeff' + raw[2:].decode('utf-16-be')
            elif raw.startswith(b'\xef\xbb\xbf'):
                content = '\ufeff' + raw[3:].decode('utf-8')
            else:
                content = raw.decode('utf-8')
            self.source.delete("1.0", "end")
            self.source.insert("1.0", content)
            # Tk normalizes line endings in its text widget; retain the original text for compaction.
            self.loaded_file_text = content
            self.loaded_file_display = self.source.get("1.0", "end-1c")
        except (OSError, UnicodeError) as exc:
            messagebox.showerror("Could not open text file", str(exc), parent=self)
    def _compact(self) -> None:
        try:
            entered = self.source.get("1.0", "end-1c")
            loaded_text = getattr(self, "loaded_file_text", None)
            loaded_display = getattr(self, "loaded_file_display", None)
            source_text = loaded_text if loaded_text is not None and entered == loaded_display else entered
            message, mode = compact_text(source_text, self._current_key())
            self.compacted.configure(state="normal"); self.compacted.delete("1.0", "end"); self.compacted.insert("1.0", message); self.compacted.configure(state="disabled")
            self.compact_stats.configure(text=f"M∞ format: {mode}")
        except Exception as exc:
            messagebox.showerror("Could not compact content", str(exc), parent=self)
    def _paste_into(self, widget: tk.Text) -> None:
        try:
            content = self.clipboard_get()
            try:
                start = widget.index("sel.first")
                end = widget.index("sel.last")
                widget.delete(start, end)
            except tk.TclError:
                pass
            widget.insert("insert", content)
            widget.focus_set()
        except tk.TclError:
            messagebox.showinfo("Clipboard is empty", "Copy an M∞ message first, then paste it here.", parent=self)

    def _paste_restore_shortcut(self, _event: tk.Event) -> str:
        self._paste_into(self.package)
        return "break"

    def _restore(self) -> None:
        try:
            value = restore_text(self.package.get("1.0", "end-1c"), self._current_key())
            self.restored_exact_text = value
            self.restored.configure(state="normal"); self.restored.delete("1.0", "end"); self.restored.insert("1.0", value); self.restored.configure(state="disabled")
        except Exception as exc:
            messagebox.showerror("Could not restore content", str(exc), parent=self)

    def _copy(self, widget: tk.Text) -> None:
        value = getattr(self, "restored_exact_text", widget.get("1.0", "end-1c")) if widget is getattr(self, "restored", None) else widget.get("1.0", "end-1c")
        if not value:
            messagebox.showinfo("Nothing to copy", "There is no text here yet.", parent=self); return
        self.clipboard_clear(); self.clipboard_append(value); self.update()
        messagebox.showinfo("Copied", "Text copied to the clipboard.", parent=self)

    def _save_package(self) -> None:
        value = self.compacted.get("1.0", "end-1c")
        if not value:
            messagebox.showinfo("Nothing to save", "Compact some content first.", parent=self); return
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".m1", filetypes=[("M∞ v0.2 message", "*.m1"), ("Text file", "*.txt")])
        if path:
            with open(path, "w", encoding="utf-8", newline="") as f: f.write(value)

    def _load_package(self) -> None:
        path = filedialog.askopenfilename(parent=self, filetypes=[("M∞ v0.2 message", "*.m1 *.txt"), ("All files", "*.*")])
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f: value = f.read()
                self.package.delete("1.0", "end"); self.package.insert("1.0", value)
            except Exception as exc:
                messagebox.showerror("Could not open message", str(exc), parent=self)


if __name__ == "__main__":
    MumbledTokenApp().mainloop()












