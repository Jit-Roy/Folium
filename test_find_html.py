import sys
from PySide6.QtWidgets import QApplication, QTextEdit
from PySide6.QtGui import QTextCursor

app = QApplication(sys.argv)
edit = QTextEdit()
edit.setHtml("<h1>Lemme Test H1</h1><p>Lemme test bold</p><h2>Lemme Test H2</h2>")

doc = edit.document()
cursor = QTextCursor(doc)

query = "lemme"
replacement = "hmm"

count = 0
cursor.beginEditBlock()
while not cursor.isNull() and not cursor.atEnd():
    cursor = doc.find(query, cursor)
    if not cursor.isNull():
        cursor.insertText(replacement)
        count += 1
cursor.endEditBlock()

print(f"Replaced {count} times.")
print(f"Final HTML:\n{edit.toHtml()}")
