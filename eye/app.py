#!/usr/bin/env python
# this project is licensed under the WTFPLv2, see COPYING.txt for details

import argparse
import logging
import os
import sys

import sip
sip.setapi('QString', 2)

from PyQt5.QtCore import pyqtSignal as Signal
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow

qApp = lambda: QApplication.instance()

from .three import execfile
from .qt import Slot
from . import pathutils
from . import connector


__all__ = ('App', 'qApp', 'main')


class App(QApplication):
	def __init__(self, argv):
		super(App, self).__init__(argv)
		self.setApplicationName('eye')

		self.logger = logging.getLogger()

		self.args = None

		self.lastWindow = None
		self.focusChanged.connect(self._appFocusChanged)

	def initUi(self):
		from .widgets import window

		win = window.Window()
		win.createDefaultMenuBar()
		win.quitRequested.connect(self.quit)
		return win

	def _startupScripts(self):
		import glob
		files = glob.glob(os.path.join(pathutils.getConfigPath('startup'), '*.py'))
		files.sort()
		return files

	def _scriptDict(self):
		return {'qApp': QApplication.instance()}

	def runStartScripts(self):
		for f in self._startupScripts():
			self.logger.debug('execing startup script %s', f)
			try:
				execfile(f, self._scriptDict())
			except Exception:
				self.logger.error('cannot execute startup script %r', f, exc_info=True)

	def rerun(self, path):
		connector.deleteCreatedBy(path)
		try:
			execfile(path, self._scriptDict())
		except Exception:
			self.logger.error('cannot execute startup script %r', path, exc_info=True)

	def run(self):
		"""Run app until exit

		Create and show interface, run config script, handle command-line args and run.
		Does not return until app is quit.
		"""

		self._handleArguments()
		win = self.initUi()
		win.show()
		if not self.args.no_config:
			self.runStartScripts()
		self.openCommandLineFiles()
		self.exec_()

	def _handleArguments(self):
		parser = argparse.ArgumentParser()
		parser.add_argument('files', metavar='FILE', nargs='*')
		parser.add_argument('--debug', action='store_true', default=False)
		parser.add_argument('--debug-only', action='append', default=[])
		parser.add_argument('--no-config', action='store_true', default=False)

		argv = self.arguments()[1:]
		self.args = parser.parse_args(argv)

		if self.args.debug:
			self.logger.handlers[0].setLevel(logging.DEBUG)
		for logger_name in self.args.debug_only:
			handler = logging.StreamHandler()
			handler.setFormatter(logging.Formatter('%(levelname)s:%(name)s:%(message)s'))
			handler.setLevel(logging.DEBUG)

			logger = logging.getLogger(logger_name)
			logger.addHandler(handler)

	def openCommandLineFiles(self):
		if not self.args.files:
			return

		win = connector.categoryObjects('window')[0]

		from .helpers.intent import sendIntent

		for name in self.args.files:
			path, row, col = pathutils.parseFilename(name)
			path = os.path.abspath(path)

			loc = None
			if row and col:
				loc = (row - 1, col - 1)
			elif row:
				loc = (row - 1,)
			sendIntent(win, 'openEditor', path=path, loc=loc)

	@Slot(QWidget, QWidget)
	def _appFocusChanged(self, old, new):
		while new and not new.isWindow():
			new = new.parentWidget()
		if not new or not isinstance(new, QMainWindow):
			# exclude dialogs
			return
		self.lastWindow = new


def setupLogging():
	logging.basicConfig()
	root = logging.getLogger()
	root.setLevel(logging.DEBUG)
	root.handlers[0].setLevel(logging.WARNING)


def main():
	"""Run eye app"""

	# if the default excepthook is used, PyQt 5.5 *aborts* the app when an unhandled exception occurs
	# see http://pyqt.sourceforge.net/Docs/PyQt5/incompatibilities.html
	# as this behaviour is questionable, we restore the old one

	if sys.excepthook is sys.__excepthook__:
		sys.excepthook = lambda *args: sys.__excepthook__(*args)

	setupLogging()

	app = App(sys.argv)
	app.run()
	return 0

if __name__ == '__main__':
	main()
