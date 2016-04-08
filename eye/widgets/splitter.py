# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QPoint, QRect
from PyQt5.QtWidgets import QSplitter, QWidget, QStackedLayout
Signal = pyqtSignal
Slot = pyqtSlot

from .helpers import WidgetMixin

__all__ = ('SplitManager', 'Splitter')


class Splitter(QSplitter, WidgetMixin):
	HandleBar = 42

	def __init__(self, *a):
		QSplitter.__init__(self, *a)
		WidgetMixin.__init__(self)

		self.addCategory('splitter')

	def childAt(self, pos):
		if pos.x() < 0 or pos.y() < 0 or pos.x() >= self.width() or pos.y() >= self.height():
			return None
		for i in xrange(self.count()):
			w = self.widget(i)
			if w.geometry().contains(pos):
				return w
		return self.HandleBar

	def parentManager(self):
		w = self.parent()
		while not isinstance(w, SplitManager):
			w = w.parent()
		return w


class SplitManager(QWidget, WidgetMixin):
	North = 0
	South = 1
	West = 2
	East = 3

	SplitterClass = Splitter

	def __init__(self, *args):
		QWidget.__init__(self, *args)
		WidgetMixin.__init__(self)

		self.root = self.SplitterClass(Qt.Horizontal)

		layout = QStackedLayout()
		self.setLayout(layout)
		layout.addWidget(self.root)

		self.addCategory('splitmanager')

	def splitAt(self, widgetLocation, orientation, newWidget):
		if widgetLocation:
			parent = widgetLocation.parent()
			pos = parent.indexOf(widgetLocation)
		else:
			parent = self.root
			pos = 0

		if parent.orientation() == orientation:
			parent.insertWidget(pos + 1, newWidget)
		else:
			newSplit = self.SplitterClass(orientation)
			parent.insertWidget(pos, newSplit)
			if widgetLocation:
				newSplit.addWidget(widgetLocation)
			newSplit.addWidget(newWidget)

	def removeWidget(self, widget):
		parent = widget.parent()
		widget.setParent(None)
		if not parent.count() and parent != self.root:
			self.removeWidget(parent)

	def allChildren(self):
		widgets = []
		splitters = [self.root]
		while splitters:
			spl = splitters.pop()
			for i in xrange(spl.count()):
				w = spl.widget(i)
				if isinstance(w, self.SplitterClass):
					splitters.append(w)
				else:
					widgets.append(w)

		return widgets

	def getRect(self, widget):
		return QRect(widget.mapTo(self, QPoint()), widget.size())

	def childId(self, widget):
		spl = widget
		while not isinstance(spl, self.SplitterClass):
			spl = spl.parent()
		return (spl, spl.indexOf(widget))

	def deepChildAt(self, pos):
		widget = self.root
		while isinstance(widget, QSplitter):
			widget = widget.childAt(widget.mapFrom(self, pos))
		return widget

	def requestClose(self):
		for c in self.allChildren():
			if not c.requestClose():
				return False
		return True
