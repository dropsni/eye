# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import QObject, QTimer, pyqtSignal as Signal, pyqtSlot as Slot, QElapsedTimer, QUrl
from PyQt5.QtWidgets import QWidget, QLineEdit, QVBoxLayout

from PyQt5.QtWebKitWidgets import QWebView

from ..three import str
from ..qt import Slot
from ..connector import CategoryMixin


class BasicView(QWidget, CategoryMixin):
	def __init__(self, *args, **kwargs):
		super(BasicView, self).__init__(*args, **kwargs)
		self.setLayout(QVBoxLayout())

		self.urlbar = QLineEdit()
		self.urlbar.returnPressed.connect(self._returnPressed)

		self.web = QWebView()
		self.web.urlChanged.connect(self._urlChanged)

		self.layout().addWidget(self.urlbar)
		self.layout().addWidget(self.web)

		self.setWindowTitle(self.tr('Web view'))

		self.addCategory('webview')

	@Slot()
	def _returnPressed(self):
		self.web.load(QUrl(self.urlbar.text()))

	@Slot(QUrl)
	def _urlChanged(self, url):
		self.urlbar.setText(url.toString())

