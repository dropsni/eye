# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import QModelIndex, QRegExp
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QPushButton, QMenu
from PyQt5.QtWidgets import QWidget, QActionGroup, QGridLayout, QLineEdit, QComboBox, QToolButton

import logging
import os

from ..three import str
from ..qt import Signal, Slot
from .. import consts
from .helpers import WidgetMixin
from ..helpers import file_search, buffers
from ..helpers.editor_search import SearchProps
from ..reutils import csToQtEnum
from ..qt import Signal, Slot
from .locationlist import LocationList


__all__ = ('SearchWidget',)


LOGGER = logging.getLogger(__name__)


class SearchOptionsMenu(QMenu):
	def __init__(self, **kwargs):
		super(SearchOptionsMenu, self).__init__(**kwargs)

		self.ci = self.addAction(self.tr('Case insensitive'))
		# TODO "smart case sensitive", i.e. CI if only lowercase chars
		self.addSeparator()

		self.formatGroup = QActionGroup(self)
		self.plain = self.addAction(self.tr('Plain text'))
		self.re = self.addAction(self.tr('Regular expression'))
		self.glob = self.addAction(self.tr('Glob pattern')) # TODO
		self.glob.setEnabled(False)
		self.formatGroup.addAction(self.plain)
		self.formatGroup.addAction(self.re)
		self.formatGroup.addAction(self.glob)

		for action in [self.ci, self.re, self.plain, self.glob]:
			action.setCheckable(True)
		self.plain.setChecked(True)

	def toSearchProps(self):
		ret = SearchProps(
			caseSensitive=not self.ci.isChecked(),
			isRe=self.re.isChecked()
		)
		return ret


class SearchOptionsButton(QPushButton):
	def __init__(self, **kwargs):
		super(SearchOptionsButton, self).__init__(**kwargs)

		self.setText(self.tr('Options'))

		# TODO factor with SearchOptionsMenu
		menu = QMenu()
		self.actionCi = menu.addAction(self.tr('Case insensitive'))

		menu.addSeparator()
		self.actionFormat = QActionGroup(self)
		self.actionPlain = menu.addAction(self.tr('Plain text'))
		self.actionPlain.setEnabled(False)
		self.actionRe = menu.addAction(self.tr('Regular expression'))
		self.actionGlob = menu.addAction(self.tr('Glob pattern'))
		self.actionGlob.setEnabled(False)
		self.actionFormat.addAction(self.actionPlain)
		self.actionFormat.addAction(self.actionRe)
		self.actionFormat.addAction(self.actionGlob)

		self.actionRoot = menu.addAction(self.tr('Search in best root dir'))

		for act in [self.actionCi, self.actionRe, self.actionPlain, self.actionGlob, self.actionRoot]:
			act.setCheckable(True)
		self.actionRe.setChecked(True)

		self.setMenu(menu)

	def shouldFindRoot(self):
		return self.actionRoot.isChecked()

	def caseSensitive(self):
		return not self.actionCi.isChecked()

	def reFormat(self):
		if self.actionPlain.isChecked():
			return QRegExp.FixedString
		elif self.actionRe.isChecked():
			return QRegExp.RegExp
		elif self.actionGlob.isChecked():
			return QRegExp.WildcardUnix


class SearchWidget(QWidget, WidgetMixin):
	def __init__(self, **kwargs):
		super(SearchWidget, self).__init__(**kwargs)

		layout = QGridLayout()
		self.setLayout(layout)

		self.exprEdit = QLineEdit()
		self.exprEdit.returnPressed.connect(self.returnPressed)
		self.setFocusProxy(self.exprEdit)

		self.optionsButton = SearchOptionsButton()

		self.pluginChoice = QComboBox()
		plugins = sorted(file_search.enabledPlugins(), key=lambda p: p.name())
		for plugin in plugins:
			self.pluginChoice.addItem(plugin.name(), plugin.id)

		self.results = LocationList()
		self.results.setColumns(['path', 'line', 'snippet'])

		self.searcher = None

		layout.addWidget(self.exprEdit, 0, 0)
		layout.addWidget(self.optionsButton, 0, 1)
		layout.addWidget(self.pluginChoice, 0, 2)
		layout.addWidget(self.results, 1, 0, 1, -1)

		self.addCategory('file_search_widget')

	def setPlugin(self, id):
		index = self.pluginChoice.findData(id)
		if index >= 0:
			self.pluginChoice.setCurrentIndex(index)

	def setText(self, text):
		self.exprEdit.setText(text)

	def selectedPlugin(self):
		return self.pluginChoice.itemData(self.pluginChoice.currentIndex())

	def regexp(self):
		re = QRegExp(self.exprEdit.text())
		re.setCaseSensitivity(csToQtEnum(self.optionsButton.caseSensitive()))
		re.setPatternSyntax(self.optionsButton.reFormat())
		return re

	def shouldFindRoot(self):
		return self.optionsButton.shouldFindRoot()

	def makeArgs(self, plugin):
		ed = buffers.currentBuffer()

		if self.shouldFindRoot():
			path = plugin.searchRootPath(ed.path)
		else:
			path = os.path.dirname(ed.path)
		pattern = self.exprEdit.text()
		ci = self.optionsButton.caseSensitive()
		return (path, pattern, ci)

	@Slot()
	def doSearch(self):
		self.results.clear()
		plugin_type = file_search.getPlugin(self.selectedPlugin())
		self.searcher = plugin_type()
		file_search.setupLocationList(self.searcher, self.results)
		args = self.makeArgs(self.searcher)
		self.searcher.search(*args)

	returnPressed = Signal()


# FIXME no wrap around
class SearchReplaceWidget(QWidget, WidgetMixin):
	def __init__(self, **kwargs):
		super(SearchReplaceWidget, self).__init__(**kwargs)

		layout = QGridLayout()
		self.setLayout(layout)

		self.patternEdit = QLineEdit()
		self.patternEdit.returnPressed.connect(self._search)
		self.patternEdit.textChanged.connect(self._updateEnabling)
		self.patternOptions = SearchOptionsMenu()
		self.patternButton = QToolButton(self)
		self.patternButton.setText('Options')
		self.patternButton.setPopupMode(QToolButton.InstantPopup)
		self.patternButton.setMenu(self.patternOptions)

		self.replaceEdit = QLineEdit()
		self.replaceEdit.returnPressed.connect(self._replace)

		self.searchButton = QPushButton(self.tr('&Search'))
		self.searchButton.clicked.connect(self._search)
		self.replaceButton = QPushButton(self.tr('&Replace'))
		self.replaceButton.clicked.connect(self._replace)
		self.replaceAllButton = QPushButton(self.tr('Replace &all'))
		self.replaceAllButton.clicked.connect(self._replaceAll)

		layout.addWidget(self.patternEdit, 0, 0)
		layout.addWidget(self.patternButton, 0, 1)
		layout.addWidget(self.searchButton, 0, 2)
		layout.addWidget(self.replaceEdit, 1, 0)
		layout.addWidget(self.replaceButton, 1, 1)
		layout.addWidget(self.replaceAllButton, 1, 2)

		self._updateEnabling()

		self.setWindowTitle(self.tr('Search/Replace'))
		self.addCategory('search_replace_widget')

	@Slot()
	def _updateEnabling(self):
		has_pattern = bool(self.patternEdit.text())
		self.searchButton.setEnabled(has_pattern)
		self.replaceButton.setEnabled(has_pattern)

	@Slot(str)
	def setPattern(self, text):
		self.patternEdit.setText(text)
		self.patternEdit.selectAll()

	@Slot()
	def _search(self):
		pattern = self.patternEdit.text()
		if not pattern:
			return

		editor = self.window().currentBuffer()
		props = self.patternOptions.toSearchProps()
		props.expr = pattern

		from ..helpers import editor_search
		editor_search.performSearchSeek(editor, props)

	@Slot()
	def _replace(self):
		editor = self.window().currentBuffer()
		if not hasattr(editor, 'searchObj'):
			LOGGER.info('no editor_search has been performed on %r', editor)
			return

		props = self.patternOptions.toSearchProps()

		editor.searchObj.replaceSelection(self.replaceEdit.text(), isRe=props.isRe)
		self._search()

	@Slot()
	def _replaceAll(self):
		editor = self.window().currentBuffer()
		if not hasattr(editor, 'searchObj'):
			LOGGER.info('no editor_search has been performed on %r', editor)
			return

		props = self.patternOptions.toSearchProps()

		editor.searchObj.replaceAll(self.replaceEdit.text(), isRe=props.isRe)
