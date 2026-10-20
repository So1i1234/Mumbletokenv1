# Mumbletokenv1
dependincies=pyinstaller>=6.0
Compressed token efficient language translator along with copyable prompt dictionary so your ai can understand the launguage
What is included
mumbledtoken.exe — ready-to-run Windows app.
mumbledtoken_app.py — readable application source.
mumbledtoken_dictionary.json — copyable LCL vocabulary, preservation rules, standards references, and M∞ shared-key examples.
lcl_specification.md — supplied source specification, preserved for reference.
build_windows.ps1, requirements.txt, and LICENSE.
App use
Compact accepts JSON or plain text, either pasted into the box or loaded with Upload .txt file…. Restore restores an M∞ message. The M∞ Key / Dictionary tab is a reference screen where you can copy, open, edit, and save the dictionary. Keep the exact same shared_key entries on both sides for key references.

M∞ v0.2 preserves entered text as a string by default. It uses a shared-key reference only when the input is canonical JSON text and the complete value exactly matches a shared-key entry. Uploaded UTF-8 and BOM-marked UTF-16 text keeps its line endings and BOM character during compaction. The broader LCL vocabulary is documentation; it does not automatically encode each word or translate arbitrary prose.

Vocabulary guidance
The vocabulary includes the supplied structural anchors, practical task/logic/data concepts, explicit time concepts, and provenance concepts mapped to W3C standards. Preserve negation, modality, numbers, units, attribution, uncertainty, ordering, and scope. Avoid deleting grammar when it changes the meaning. A shorthand form is not guaranteed to reconstruct ambiguous natural language unless the needed meaning is explicitly represented.

Symbols and abbreviations are not guaranteed to be single tokens in any particular model tokenizer, and token savings depend on the actual tokenizer and content.

Build
Requires Python 3.10+ with Tk support and PyInstaller. Run build_windows.ps1; it places the executable and dictionary in mumbledtoken_dist.

References
W3C PROV-O: https://www.w3.org/TR/prov-o/
W3C OWL-Time: https://www.w3.org/TR/owl-time/
JSON Schema Draft 2020-12: https://json-schema.org/draft/2020-12
Tokenizer reference: https://github.com/openai/tiktoken/blob/main/tiktoken/core.py
