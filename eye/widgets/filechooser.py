# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import QSortFilterProxyModel, QModelIndex, QRegExp, pyqtSignal, pyqtSlot, Qt, QTimer
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QTreeView, QWidget, QFileSystemModel
Signal = pyqtSignal
Slot = pyqtSlot

import os
import re

from ..three import str
from ..structs import PropDict
from .helpers import WidgetMixin
from ..helpers import buffers


__all__ = ('FileChooser', 'SubSequenceFileChooser')


def commonPrefix(strings):
	res = ''
	for cs in zip(*strings):
		if len(set(cs)) == 1:
			res += cs[0]
		else:
			break
	return res


class RootChangerProxy(QSortFilterProxyModel):
	def __init__(self, **kwargs):
		super(RootChangerProxy, self).__init__(**kwargs)
		self.srcRoot = QModelIndex()

	def setRootSource(self, srcRoot):
		self.modelAboutToBeReset.emit() # TODO be a bit more clever
		self.srcRoot = srcRoot
		self.modelReset.emit()
		self.sourceModel().fetchMore(srcRoot)

	def mapToSource(self, proxyIdx):
		if not proxyIdx.isValid():
			return self.srcRoot
		srcParent = self.mapToSource(proxyIdx.parent())
		return self.sourceModel().index(proxyIdx.row(), proxyIdx.column(), srcParent)

	def mapFromSource(self, srcIdx):
		if srcIdx == self.srcRoot or not srcIdx.isValid():
			return QModelIndex()
		proxyParent = self.mapFromSource(srcIdx.parent())
		return self.index(srcIdx.row(), srcIdx.column(),proxyParent)


class BaseFileChooser(QWidget, WidgetMixin):
	def __init__(self, **kwargs):
		super(BaseFileChooser, self).__init__(**kwargs)

		self.options = PropDict()

		# sub-widgets
		layout = QVBoxLayout()
		self.setLayout(layout)

		self.edit = QLineEdit()
		layout.addWidget(self.edit)
		self.setFocusProxy(self.edit)

		self.view = QTreeView()
		layout.addWidget(self.view)

	def setModel(self, model):
		self.view.setModel(model)

	@Slot(str)
	def setRoot(self, path):
		raise NotImplementedError()


def walk_files(root, ignore_re=None):
	for dp, dirs, files in os.walk(root):
		if ignore_re:
			dirs[:] = filter(ignore_re.match, dirs)

		for f in files:
			if ignore_re and ignore_re.match(f):
				continue
			yield os.path.join(dp, f)


class SubSequenceProxy(QSortFilterProxyModel):
	def __init__(self, **kwargs):
		super(SubSequenceProxy, self).__init__(**kwargs)
		self.reobj = re.compile('')
		self.cache = {}

	def setFilter(self, text):
		parts = map(QRegExp.escape, text)
		pattern = '.*'.join('(%s)' % part for part in parts)
		self.reobj = re.compile(pattern, re.I)
		self.cache = {}
		self.invalidate()

	def filterAcceptsRow(self, row, parent):
		if not self.reobj.pattern:
			return False

		mdl = self.sourceModel()
		qidx = mdl.index(row, 0, parent)
		text = mdl.data(qidx)
		mtc = self.reobj.search(text)
		if mtc:
			self._scoreMatch(mtc, text)
		return bool(mtc)

	def _score(self, qidx):
		text = self.sourceModel().data(qidx)
		try:
			return self.cache[text]
		except KeyError:
			pass

		mtc = self.reobj.search(text)
		return self._scoreMatch(mtc, text)

	def _scoreMatch(self, mtc, text):
		n = self.reobj.groups

		seq = 0
		sub = 0
		for i in xrange(1, n + 1):
			if i > 1:
				seq += int(bool(mtc.start(i) - mtc.start(i - 1) - 1))

			if mtc.start(i) == 0:
				sub += 1
			else:
				sub += int(text[mtc.start(i) - 1] == '/')

		score = seq - sub
		self.cache[text] = score
		return score

	def lessThan(self, qidx1, qidx2):
		if not self.reobj.groups:
			return qidx1.data() < qidx2.data()
		return self._score(qidx1) < self._score(qidx2)


class SubSequenceFileChooser(BaseFileChooser):
	elements_per_crawl = 20

	def __init__(self, **kwargs):
		super(SubSequenceFileChooser, self).__init__(**kwargs)

		self.mdl = QStandardItemModel()
		self.filter = SubSequenceProxy()
		self.filter.setSourceModel(self.mdl)
		self.view.setModel(self.filter)

		self.view.setRootIsDecorated(False)
		self.view.setAlternatingRowColors(True)
		self.view.sortByColumn(0, Qt.AscendingOrder)

		self.edit.textEdited.connect(self._onTextEdited)

		self.crawlTimer = QTimer()
		self.crawlTimer.timeout.connect(self.doCrawl)
		self.crawler = None

	@Slot(str)
	def _onTextEdited(self, text):
		return self.filter.setFilter(text)
		parts = map(QRegExp.escape, text)
		pattern = '.*'.join(parts)
		self.filter.setFilterRegExp(pattern)

	@Slot()
	def doCrawl(self):
		i = 0
		for path, i in zip(self.crawler, range(self.elements_per_crawl)):
			self.content.append(path)
			self.mdl.appendRow(QStandardItem(path))

		if not i:
			self.crawlTimer.stop()

	def setRoot(self, root):
		self.root = root
		self.content = []
		self.mdl.clear()
		self.mdl.setHorizontalHeaderLabels([self.tr('File')])

		self.crawler = walk_files(root)
		self.crawlTimer.start(0)

	# TODO be able to configure crawling: ignored patterns, depth, etc.


class FileChooser(BaseFileChooser):
	def __init__(self, **kwargs):
		super(FileChooser, self).__init__(**kwargs)

		self.options = PropDict()

		self.edit.textEdited.connect(self._onTextEdited)

		self.view.activated.connect(self._onActivated)

		# models
		self.rootChanger = RootChangerProxy()

		fsModel = QFileSystemModel(self)
		self.setModel(fsModel)

		self.filter = QSortFilterProxyModel()
		self.filter.setSourceModel(self.rootChanger)
		self.view.setModel(self.filter)

		self.addCategory('filechooser')

	def setModel(self, model):
		self.baseModel = model
		self.rootChanger.setSourceModel(self.baseModel)

	@Slot(str)
	def setRoot(self, path):
		self.root = path
		srcIdx = self.baseModel.setRootPath(path)
		self.rootChanger.setRootSource(srcIdx)
		self.view.setRootIndex(QModelIndex())

	@Slot(str)
	def _onTextEdited(self, txt):
		elems = txt.rsplit('/', 1)
		if len(elems) == 2:
			dir, base = elems
		else:
			dir, base = '', elems[0]

		path = os.path.join(self.root, dir)
		self.rootChanger.setRootSource(self.baseModel.index(path))
		self.filter.setFilterRegExp(QRegExp(base, Qt.CaseInsensitive, QRegExp.Wildcard))

		if self.options.get('autosuggest'):
			names = [self.filter.data(self.filter.index(i, 0)).toString()
				 for i in xrange(self.filter.rowCount(QModelIndex()))]
			names = [n[len(base):] for n in names]
			add = commonPrefix(names)

			cursor = self.edit.cursorPosition()
			self.edit.setText(self.edit.text()[:cursor] + add)
			self.edit.setSelection(cursor, len(self.edit.text()))

	@Slot(QModelIndex)
	def _onActivated(self, idx):
		idx = self.filter.mapToSource(idx)
		idx = self.rootChanger.mapToSource(idx)
		info = self.baseModel.fileInfo(idx)
		if info.isDir():
			return
		path = info.absoluteFilePath()
		buffers.openEditor(path)