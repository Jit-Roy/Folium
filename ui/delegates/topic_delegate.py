from PySide6.QtWidgets import QStyledItemDelegate, QStyle
import sys
from PySide6.QtGui import QIcon, QPainter
from PySide6.QtCore import Qt, QRect, Signal, QObject, QEvent

class TopicDelegateSignals(QObject):
    add_clicked = Signal(int)
    delete_clicked = Signal(int)
    move_up_clicked = Signal(int)
    move_down_clicked = Signal(int)

class TopicDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.signals = TopicDelegateSignals()
        self.icon_plus = QIcon("assets/icons/plus.svg")
        self.icon_trash = QIcon("assets/icons/trash.svg")
        self.icon_check = QIcon("assets/icons/check.svg")
        self.icon_cross = QIcon("assets/icons/x.svg")
        self.icon_up = QIcon("assets/icons/arrow-up.svg")
        self.icon_down = QIcon("assets/icons/arrow-down.svg")
        
        self.confirming_delete = {}
        
        self.btn_size = 16
        self.padding = 6
        
        self._current_elide_width = None
        self._current_font_metrics = None

    def displayText(self, value, locale):
        text = super().displayText(value, locale)
        if self._current_elide_width is not None and self._current_font_metrics is not None:
            if self._current_elide_width > 0:
                text = self._current_font_metrics.elidedText(text, Qt.ElideRight, self._current_elide_width)
            else:
                text = ""
        return text

    def paint(self, painter, option, index):
        topic_id = index.data(Qt.UserRole)
        is_hovered = bool(option.state & QStyle.State_MouseOver)
        is_confirming = self.confirming_delete.get(topic_id, False) if topic_id else False

        rect = option.rect
        r4 = QRect(rect.right() - self.btn_size - self.padding, 
                   rect.top() + (rect.height() - self.btn_size) // 2, 
                   self.btn_size, self.btn_size) # Trash / Cross
        r3 = QRect(r4.left() - self.btn_size - (self.padding // 2), 
                   r4.top(), 
                   self.btn_size, self.btn_size) # Plus / Check
        r2 = QRect(r3.left() - self.btn_size - (self.padding // 2),
                   r3.top(),
                   self.btn_size, self.btn_size) # Down
        r1 = QRect(r2.left() - self.btn_size - (self.padding // 2),
                   r2.top(),
                   self.btn_size, self.btn_size) # Up

        if topic_id and (is_hovered or is_confirming):
            btn_area_width = (self.btn_size * 4) + (self.padding * 2.5) + 5
            available_width = rect.width() - btn_area_width
            self._current_elide_width = available_width
            self._current_font_metrics = option.fontMetrics
        else:
            self._current_elide_width = None
            self._current_font_metrics = None

        super().paint(painter, option, index)

        self._current_elide_width = None
        self._current_font_metrics = None

        if not topic_id or not (is_hovered or is_confirming):
            return

        if is_confirming:
            self.icon_check.paint(painter, r3)
            self.icon_cross.paint(painter, r4)
        else:
            self.icon_up.paint(painter, r1)
            self.icon_down.paint(painter, r2)
            self.icon_plus.paint(painter, r3)
            self.icon_trash.paint(painter, r4)

    def helpEvent(self, event, view, option, index):
        if event.type() == QEvent.ToolTip:
            from PySide6.QtWidgets import QToolTip
            
            topic_id = index.data(Qt.UserRole)
            text = index.data(Qt.DisplayRole)
            if topic_id and text:
                rect = option.rect
                btn_area_width = (self.btn_size * 4) + (self.padding * 2.5) + 5
                
                # We can't safely use style.subElementRect here due to PySide6 memory issues.
                # Just assume standard text indent or use the same safe available_width formula:
                available_width = rect.width() - btn_area_width
                
                if option.fontMetrics.horizontalAdvance(text) > available_width:
                    QToolTip.showText(event.globalPos(), text, view)
                    return True

        return super().helpEvent(event, view, option, index)

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            topic_id = index.data(Qt.UserRole)
            if not topic_id:
                return super().editorEvent(event, model, option, index)

            rect = option.rect
            r4 = QRect(rect.right() - self.btn_size - self.padding, 
                       rect.top() + (rect.height() - self.btn_size) // 2, 
                       self.btn_size, self.btn_size)
            r3 = QRect(r4.left() - self.btn_size - (self.padding // 2), 
                       r4.top(), 
                       self.btn_size, self.btn_size)
            r2 = QRect(r3.left() - self.btn_size - (self.padding // 2),
                       r3.top(),
                       self.btn_size, self.btn_size)
            r1 = QRect(r2.left() - self.btn_size - (self.padding // 2),
                       r2.top(),
                       self.btn_size, self.btn_size)

            pos = event.pos()
            is_confirming = self.confirming_delete.get(topic_id, False)

            if r3.contains(pos):
                if is_confirming:
                    # Check clicked -> Confirm delete
                    self.confirming_delete[topic_id] = False
                    self.signals.delete_clicked.emit(topic_id)
                else:
                    # Plus clicked -> Add subtopic
                    self.signals.add_clicked.emit(topic_id)
                return True
                
            elif r4.contains(pos):
                if is_confirming:
                    # Cross clicked -> Cancel
                    self.confirming_delete[topic_id] = False
                    if self.parent():
                        self.parent().viewport().update()
                else:
                    # Trash clicked -> Enter confirm state
                    self.confirming_delete[topic_id] = True
                    if self.parent():
                        self.parent().viewport().update()
                return True
                
            elif not is_confirming:
                if r1.contains(pos):
                    self.signals.move_up_clicked.emit(topic_id)
                    return True
                elif r2.contains(pos):
                    self.signals.move_down_clicked.emit(topic_id)
                    return True

        return super().editorEvent(event, model, option, index)

    def createEditor(self, parent, option, index):
        from PySide6.QtWidgets import QLineEdit
        editor = QLineEdit(parent)
        editor.setStyleSheet("""
            QLineEdit {
                background: #1e1e1e;
                border: 1px solid #B48EAD;
                border-radius: 3px;
                padding: 0px 4px;
                color: #ffffff;
                font-size: 13px;
                margin: 0px;
            }
        """)
        return editor
