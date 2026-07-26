import sys
from PySide6.QtWidgets import QApplication, QTextEdit
from PySide6.QtGui import QTextCursor

app = QApplication(sys.argv)
edit = QTextEdit()
edit.setPlainText("Lemme Test H1\nLemme test bold\nLemme Test H2")

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
        print(f"Replaced. Cursor at end? {cursor.atEnd()}")
    else:
        print("Not found, cursor is null.")
cursor.endEditBlock()

print(f"Replaced {count} times.")
print(f"Final text:\n{edit.toPlainText()}")
