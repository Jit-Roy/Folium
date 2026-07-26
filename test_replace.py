import sys
import traceback
from PySide6.QtWidgets import QApplication
from ui.widgets.rich_text_editor import RichTextEditor

app = QApplication(sys.argv)
editor = RichTextEditor()
editor.setHtml("<h1>Lemme Test H1</h1><p>Lemme test bold</p><h2>Lemme Test H2</h2>")

try:
    count = editor.replace_all_matches("lemme", "hmm")
    print(f"Replaced {count} matches.")
    print("HTML:", editor.toHtml())
except Exception as e:
    print("EXCEPTION CAUGHT!")
    traceback.print_exc()
