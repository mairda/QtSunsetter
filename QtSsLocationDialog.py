# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'QtSsLocationDialog.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_QtSsLocationDialog(object):
    def setupUi(self, QtSsLocationDialog):
        if not QtSsLocationDialog.objectName():
            QtSsLocationDialog.setObjectName(u"QtSsLocationDialog")
        QtSsLocationDialog.setWindowModality(Qt.ApplicationModal)
        QtSsLocationDialog.resize(300, 265)
        self.buttonBox = QDialogButtonBox(QtSsLocationDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setGeometry(QRect(10, 213, 280, 41))
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        self.label = QLabel(QtSsLocationDialog)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(10, 10, 61, 19))
        self.label_2 = QLabel(QtSsLocationDialog)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(20, 39, 61, 16))
        self.longitude = QLineEdit(QtSsLocationDialog)
        self.longitude.setObjectName(u"longitude")
        self.longitude.setGeometry(QRect(82, 68, 134, 30))
        self.longitude.setInputMethodHints(Qt.ImhDigitsOnly)
        self.longitude.setMaxLength(16)
        self.label_3 = QLabel(QtSsLocationDialog)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setGeometry(QRect(10, 75, 71, 16))
        self.latitude = QLineEdit(QtSsLocationDialog)
        self.latitude.setObjectName(u"latitude")
        self.latitude.setGeometry(QRect(82, 32, 134, 30))
        self.latitude.setInputMethodHints(Qt.ImhDigitsOnly)
        self.latitude.setMaxLength(16)
        self.latDirection = QComboBox(QtSsLocationDialog)
        self.latDirection.addItem("")
        self.latDirection.addItem("")
        self.latDirection.setObjectName(u"latDirection")
        self.latDirection.setGeometry(QRect(222, 32, 68, 30))
        self.longDirection = QComboBox(QtSsLocationDialog)
        self.longDirection.addItem("")
        self.longDirection.addItem("")
        self.longDirection.setObjectName(u"longDirection")
        self.longDirection.setGeometry(QRect(222, 68, 68, 30))
        self.label_4 = QLabel(QtSsLocationDialog)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setGeometry(QRect(10, 111, 171, 16))
        self.tzOffset = QSpinBox(QtSsLocationDialog)
        self.tzOffset.setObjectName(u"tzOffset")
        self.tzOffset.setGeometry(QRect(182, 104, 49, 30))
        self.tzOffset.setMinimum(-12)
        self.tzOffset.setMaximum(12)
        self.tzOffset.setValue(0)
        self.chkCorrectForSysTZ = QCheckBox(QtSsLocationDialog)
        self.chkCorrectForSysTZ.setObjectName(u"chkCorrectForSysTZ")
        self.chkCorrectForSysTZ.setGeometry(QRect(10, 145, 251, 20))
        self.showLocationInDMS = QCheckBox(QtSsLocationDialog)
        self.showLocationInDMS.setObjectName(u"showLocationInDMS")
        self.showLocationInDMS.setGeometry(QRect(10, 176, 277, 24))
        QWidget.setTabOrder(self.latitude, self.latDirection)
        QWidget.setTabOrder(self.latDirection, self.longitude)
        QWidget.setTabOrder(self.longitude, self.longDirection)

        self.retranslateUi(QtSsLocationDialog)
        self.buttonBox.accepted.connect(QtSsLocationDialog.accept)
        self.buttonBox.rejected.connect(QtSsLocationDialog.reject)

        QMetaObject.connectSlotsByName(QtSsLocationDialog)
    # setupUi

    def retranslateUi(self, QtSsLocationDialog):
        QtSsLocationDialog.setWindowTitle(QCoreApplication.translate("QtSsLocationDialog", u"Location", None))
        self.label.setText(QCoreApplication.translate("QtSsLocationDialog", u"Location:", None))
        self.label_2.setText(QCoreApplication.translate("QtSsLocationDialog", u"Latitude:", None))
        self.label_3.setText(QCoreApplication.translate("QtSsLocationDialog", u"Longitude:", None))
        self.latDirection.setItemText(0, QCoreApplication.translate("QtSsLocationDialog", u"North", None))
        self.latDirection.setItemText(1, QCoreApplication.translate("QtSsLocationDialog", u"South", None))

        self.longDirection.setItemText(0, QCoreApplication.translate("QtSsLocationDialog", u"East", None))
        self.longDirection.setItemText(1, QCoreApplication.translate("QtSsLocationDialog", u"West", None))

        self.label_4.setText(QCoreApplication.translate("QtSsLocationDialog", u"Timezone Offset (Hours):", None))
        self.chkCorrectForSysTZ.setText(QCoreApplication.translate("QtSsLocationDialog", u"Correct for system clock timezone", None))
        self.showLocationInDMS.setText(QCoreApplication.translate("QtSsLocationDialog", u"Location in Degrees Minutes Seconds", None))
    # retranslateUi

