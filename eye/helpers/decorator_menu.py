# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Decorators to create menu entries basing on decorated functions.

It's possible to create simple menus and sub-menus calling a Python function by using the
`registerMenuEntry` decorator::

	@registerMenuEntry('&My menu', 'Say hello &world')
	def helloWorld(editor):
		print('Hello world!')

	@registerMenuEntry('&My menu', '&Say', '&goodbye world', params=('Goodbye',))
	@registerMenuEntry('&My menu', '&Say', '&hello world', params=('Hello',))
	def genericHello(editor, greeting):
		print(greeting, 'world!')

"""

from collections import OrderedDict
from weakref import ref
from logging import getLogger

from PyQt5.QtWidgets import QAction, QMenu

from ..app import qApp
from ..qt import Slot
from ..connector import defaultWindowConfig


__all__ = (
	'registerMenuEntry', 'MenuEntry',
)


LOGGER = getLogger(__name__)


MENUS = OrderedDict()


def findAction(widget, text):
	for action in widget.actions():
		if action.text() == text:
			return action


class MenuEntry(QAction):
	def __init__(self, categories, cb, params=(), **kwargs):
		super(MenuEntry, self).__init__(**kwargs)
		self.cb = cb
		self.categories = frozenset(categories)
		self.triggered.connect(self._onTrigger)
		self.ref = None
		self.params = params
		qApp().focusChanged.connect(self._onFocusChanged)

	@Slot()
	def _onTrigger(self):
		if not self.ref:
			return
		obj = self.ref()
		if not obj:
			return

		self.cb(obj, *self.params)

	@Slot('QWidget*', 'QWidget*')
	def _onFocusChanged(self, _, new):
		if isinstance(new, QMenu):
			return

		if hasattr(new, 'categories'):
			has = bool(new.categories() & self.categories)
			self.setEnabled(has)
			self.ref = ref(new)
		else:
			self.ref = None
			self.setEnabled(False)


@defaultWindowConfig
def setupMenus(window):
	def setup(d, menu):
		for k in d:
			if isinstance(d[k], (dict, OrderedDict)):
				action = findAction(menu, k)
				if not action:
					action = menu.addMenu(k).menuAction()

				menu = action.menu()
				setup(d[k], menu)
			else:
				cb, params = d[k]
				action = MenuEntry(['editor'], cb=cb, params=params, text=k, parent=menu)
				menu.addAction(action)

	setup(MENUS, window.menuBar())


def registerMenuEntry(*path, **kwargs):
	"""Decorator to create a menu entry and link it to the decorated function

	:param path: each item will create a menu, and the last item will create a menu action
	:param params: extra arguments to pass to the decorated function
	"""

	params = kwargs.pop('params', ())
	if kwargs:
		raise ValueError('Unsupported keyword-args: %s' % list(kwargs))

	if not path:
		raise ValueError('There should be at least one positional argument')

	path, last = path[:-1], path[-1]

	def decorator(func):
		d = MENUS
		for k in path:
			d = d.setdefault(k, OrderedDict())
		d[last] = (func, params)
		return func
	return decorator

