# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.Qsci import *
Signal = pyqtSignal
Slot = pyqtSlot

from ..app import qApp
from ..connector import registerSignal, registerShortcut, disabled, categoryObjects
from .helpers import WidgetMixin


__all__ = ('Minibuffer', 'openMiniBuffer', 'getMiniBuffer')


class Minibuffer(QLineEdit, WidgetMixin):
	def __init__(self, parent=None):
		QLineEdit.__init__(self, parent)
		WidgetMixin.__init__(self)

		self.statusBar = None
		self.closeOnEscape = True
		self.closeOnFocusOut = True

		sh = QShortcut(QKeySequence(Qt.Key_Escape), self)
		sh.activated.connect(self.onEscape)

		self.returnPressed.connect(self.onReturnPressed)

		self.addCategory('minibuffer')

	def __del__(self):
		self.cancelled.emit()

	def addToWindow(self, window):
		if self.statusBar:
			self.remove()
		self.statusBar = window.statusBar()
		self.statusBar.insertWidget(0, self)

	def remove(self):
		# warning: this triggers the focus-out
		if self.statusBar:
			self.statusBar.removeWidget(self)
			self.statusBar = None

	def setCloseOnEscape(self, b):
		self.closeOnEscape = b

	def setCloseOnFocusOut(self, b):
		self.closeOnEscape = b

	textEntered = Signal(unicode)
	cancelled = Signal()

	@Slot()
	def cancel(self):
		self.cancelled.emit()
		self.remove()

	@Slot()
	def onReturnPressed(self):
		self.textEntered.emit(self.text())

	@Slot()
	def onEscape(self):
		if self.closeOnEscape:
			self.cancel()

	def focusOutEvent(self, ev):
		QLineEdit.focusOutEvent(self, ev)
		if self.closeOnFocusOut:
			self.cancel()


def _makeMiniBuffer(text='', window=None, category=None, closeOnEscape=True, closeOnFocusOut=True):
	if window is None:
		window = qApp().lastWindow

	m = Minibuffer()
	m.setCloseOnEscape(closeOnEscape)
	m.setCloseOnFocusOut(closeOnFocusOut)
	m.setText(text)
	m.addToWindow(window)
	m.giveFocus()
	if category:
		m.addCategory(category)
	return m


def openMiniBuffer(text='', window=None, category=None, closeOnEscape=True, closeOnFocusOut=True):
	old = getMiniBuffer(window)
	if old:
		old.cancel()
		old = None
	return _makeMiniBuffer(text, window, category, closeOnEscape, closeOnFocusOut)


def getMiniBuffer(window=None, category=None):
	if window is None:
		window = qApp().lastWindow

	for mb in categoryObjects('minibuffer'):
		if mb.window() == window:
			if category and category not in mb.categories():
				return None
			return mb

# TODO: only one minibuffer at a time
# create another minibuffer if different category (because different use)
# possible reuse if same category?