# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt4.QtGui import QColor

__all__ = ('QColorAlpha', 'QColor')

def QColorAlpha(*args):
	if len(args) == 1:
		if isinstance(args[0], (str, unicode)):
			s = args[0]
			if s.startswith('#') and len(s) == 9: #RRGGBBAA
				qc = QColor(s[:7])
				qc.setAlpha(int(s[7:], 16))
				return
			else: # #RRGGBB, "red"
				return QColor(s)
		return QColor(args[0]) # Qt.red
	elif len(args) == 2: # (Qt.red, alpha)
		qc = QColor(args[0])
		qc.setAlpha(args[1])
		return qc
	elif len(args) >= 3: # (r, g, b)
		return QColor(*args)
