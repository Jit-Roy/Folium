import sys
from PySide6.QtWidgets import QApplication, QTextEdit
from PySide6.QtGui import QTextCursor

app = QApplication(sys.argv)
edit = QTextEdit()
edit.setPlainText("Lemme Test")

doc = edit.document()
cursor = QTextCursor(doc)

cursor.beginEditBlock()
cursor = doc.find("lemme", cursor)
if not cursor.isNull():
    cursor.insertText("hmm")
cursor = doc.find("lemme", cursor)
# now cursor is null!
print("Is cursor null?", cursor.isNull())
try:
    cursor.endEditBlock()
    print("endEditBlock succeeded on null cursor.")
except Exception as e:
    print("EXCEPTION:", e)
