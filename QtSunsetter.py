# This Python file uses the following encoding: utf-8
#
# Entry point and main window implementation
#
# Version: 1.0
# Copyright (C) 2020/09/21 David A. Mair
# This file is part of QtSunsetter<https://github.com/mairda/QtSunsetter.git>.
#
# QtSunsetter is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# QtSunsetter is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with QtSunsetter.  If not, see <http://www.gnu.org/licenses/>.
#
# PySide2 based Qt program providing daily sunset/sunrise time calculation and
# the ability to run a program of choice at rise and/or set
#
# Version: 1.0
# Copyright (C) 2020/10/19 David A. Mair
# This file is part of QtSunsetter<https://github.com/mairda/QtSunsetter.git>.
#
# QtSunsetter is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# QtSunsetter is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with QtSunsetter.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import subprocess

from math import sin, cos, atan2, pi, pow, sqrt
# from math import tan, asin, acos, radians, pi, degrees,

from threading import enumerate, main_thread, Thread
from time import sleep

from PySide2.QtWidgets import QApplication, QWidget, QPushButton, QDialog
from PySide2.QtWidgets import QLineEdit, QLabel, QComboBox, QCheckBox
from PySide2.QtWidgets import QSpinBox, QMessageBox, QFileDialog
from PySide2.QtWidgets import QGraphicsView, QGraphicsScene
from PySide2.QtCore import Qt
from PySide2.QtCore import QFile, QPoint, QObject, QSize, QTimer, SIGNAL, SLOT
from PySide2.QtCore import QDir, QFileInfo, QCoreApplication
from PySide2.QtGui import QColor, QPen
from PySide2.QtGui import QPalette, QBrush
# from PySide2.QtGui import QPainter, QIcon
from PySide2.QtGui import QImage, QPainter, QPixmap, QIcon
from PySide2.QtUiTools import QUiLoader
from random import seed, randint
from QtSsLocationDialog import Ui_QtSsLocationDialog
# from QtSsLocationDialog import Ui_QtSsDialog
#  from QtSsLocation import Ui_QtSsDialog
from QtSsTODMath import getTimeNowWithCorrection, getSunriseTime, getSunsetTime
from QtSsTODMath import itsDaytime, itsNighttime
from QtSsTODMath import getCorrectForSysTZ, setCorrectForSysTZ
from QtSsTODMath import getTimeNowFractionOfLightPeriod
from QtSsTODMath import getTimeToNextHorizonCrossing
# from QtSsTODMath import getTimeNowDeltaWithCorrection
# from QtSsTODMath import getSunriseDelta
# from QtSsTODMath import daytimeFractionOfDay
# from QtSsTODMath import nighttimeFractionOfDay
# from QtSsTODMath import getTimeNowDurationOfLightPeriod
from QtSsMath import setLatitude, setLongitude, getLatitude, getLongitude
from QtSsMath import getLatitudeDegrees, getLatitudeMinutes, getLatitudeSeconds
from QtSsMath import getLongitudeDegrees, getLongitudeMinutes
from QtSsMath import getLongitudeSeconds, getAbsLatitude, getAbsLongitude
from QtSsMath import setSystemTime, getHomeTZ, setHomeTZ, setLocalTZ
from QtSsConfig import SunsetterConfig, QTS_SUNRISE, QTS_SUNSET
from QtSsDebug import disableWarnings, enableWarnings, warningsEnabled
from QtSsDebug import warningMessage
from QtSsDebug import disableDebug, enableDebug, debugIsEnabled, debugMessage


class QtSunsetter(QWidget):
    # Class variables for child threads on rise/set events
    sunriseChildName = "QtS Rise"
    sunsetChildName = "QtS Set"
    childThreadAny = 0
    childThreadSunrise = 1
    childThreadSunset = 2

    def __init__(self):
        super(QtSunsetter, self).__init__()

        # A name for this object in warning messages
        self.appSrcFrom = "App"

        # Last sky object position is not on-screen
        self.lastPan = -1.0
        self.lastHeight = -1.0
        self.lastXObject = -1.0
        self.lastYObject = 256.0
        self.lastY = 128.0
        # self.yMaxObject = 0.0
        self.yMaxObject = 5.65

        # Use these to force stepping time by forceAmount on the timer tick
        # Set forceTime to True and adjust forceAmount to suit
        self.forceTime = False
        self.forceAmount = 0.005

        self.savedT = 0.0
        self.lockAngle = 0.0

        self.nextCrossing = None
        setLocalTZ()
        self.presetConfig()
        self.loadConfig()
        self.timer = QTimer(self)
        self.load_ui()
        if self.getRunLastEventAtLaunch():
            if itsDaytime():
                self.reachedSunrise()
            else:
                self.reachedSunset()

    def load_ui(self):
        loader = QUiLoader()
        path = os.path.join(os.path.dirname(__file__), "QtSsMainWindow.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        loader.load(ui_file, self)
        ui_file.close()

        self.getTargetLineEditColor()

        # Not yet shown any sunrise or sunset times
        self.shownSRise = None
        self.shownSSet = None

        # Cause the time to set
        self.tick()

        # Show any saved location
        self.showLocation()

        # Show any saved sunset/sunrise programs and whether we pre-run the
        # last passed one
        self.showSolarCrossingProgramText(self.initRiseRun, QTS_SUNRISE)
        self.showSolarCrossingProgramText(self.initSetRun, QTS_SUNSET)
        self.showRunLastEventAtLaunch(self.initRunLastEventAtLaunch)

        # Connect the settings button to our slot
        btnSetLocation = self.findChild(QPushButton, "btnSetLocation")
        if btnSetLocation is not None:
            QObject.connect(btnSetLocation, SIGNAL('clicked()'),
                            self, SLOT('locationClicked()'))

        # Connect the save config button to our slot
        btnSaveConfig = self.findChild(QPushButton, "btnSaveConfig")
        if btnSaveConfig is not None:
            QObject.connect(btnSaveConfig, SIGNAL('clicked()'),
                            self, SLOT('saveConfig()'))

        # Connect the sunrise run ... button to our slot
        btnChooseRun = self.findChild(QPushButton, "btnChooseRiseRun")
        if btnChooseRun is not None:
            QObject.connect(btnChooseRun, SIGNAL('clicked()'),
                            self, SLOT('chooseRiseRun()'))

        # Connect the sunset run ... button to our slot
        btnChooseRun = None
        btnChooseRun = self.findChild(QPushButton, "btnChooseSetRun")
        if btnChooseRun is not None:
            QObject.connect(btnChooseRun, SIGNAL('clicked()'),
                            self, SLOT('chooseSetRun()'))

        # Create an application icon and not the file as a name
        self.createAppIcon()
        self.setWindowIconText("QtSunsetter")
        self.setWindowTitle("QtSunsetter")

        # Start a timer to update the time, it doesn't need to be per-second
        # in normal use
        self.timer.timeout.connect(self.tick)
        if not debugIsEnabled():
            # Not debugging, and not forcing time progression, just update
            # every minute
            if self.forceTime is False:
                self.timer.start(60000)
            # Forcing time progress, use a one second timer
            else:
                self.timer.start(1000)
        # Debugging, use a one second timer but don't force sky object progress
        else:
            self.timer.start(1000)

    def dumpAppIconSizes(self, atContext):
        if debugIsEnabled():
            # Get the current window icon
            appIcon = self.windowIcon()
            lSizes = appIcon.availableSizes()
            count = 0
            for size in lSizes:
                # Assuming a QSize
                msg = "At {}, an app icon exists with size ".format(atContext)
                msg += "{}, {}".format(size.width(), size.height())
                debugMessage(msg)
                count += 1
            msg = "At {}, icon size list has length {}".format(atContext,
                                                               count)
            debugMessage(msg)

    # Draw an icon for the application, for now make it unchanging
    def createAppIcon(self):
        # This will only output if debug is enabled
        self.dumpAppIconSizes("launch")

        # Use a relatively big image it will scale
        image = QImage(128, 128, QImage.Format_RGB32)

        # Required colors for sky, ground and sky object
        # ...for now don't make these variable and only draw the sun rising
        # (viewing South) or setting (viewing North)
        groundColor = self.getGroundColor(timeFrac=-1.0)
        skyColor = self.getSkyColor(timeFrac=-1.0, assumeDaytime=True)
        objectColor = Qt.yellow

        # More sky than ground, set the sizes
        skyHeight = (image.height() * 85) / 128
        groundHeight = image.height() - skyHeight

        # Start painting onto the image
        p = QPainter()
        p.begin(image)

        # Draw the sky
        p.fillRect(0, 0, image.width(), skyHeight, skyColor)

        # Pen/Brush for the object in the sky
        objectPen = QPen(objectColor,
                         1,
                         Qt.SolidLine,
                         Qt.SquareCap,
                         Qt.BevelJoin)
        objectBrush = QBrush(objectColor)
        p.setPen(objectPen)
        p.setBrush(objectBrush)

        # Size and center of the object in the sky
        objectRad = 8.0
        objectDiam = 2.0 * objectRad
        cntrPnt = QPoint(5 + objectDiam, skyHeight)

        # Draw the object in the sky
        p.drawEllipse(cntrPnt,
                      objectDiam,
                      objectDiam)

        # Draw the ground
        p.fillRect(0, skyHeight, image.width(), groundHeight, groundColor)
        p.end()

        # Get a pixmap from the image and use it to create an icon
        myPixmap = QPixmap(image)
        myIcon = QIcon(myPixmap)

        # Use the icon as the window icon
        self.setWindowIcon(myIcon)

        # This will only output if debug is enabled
        self.dumpAppIconSizes("set icon")

        return None

    # Given either the app object or a parent window position this window
    # with a little randomness when based on the screen
    def position_ui(self, parentWidget=None):
        # Get my app
        theApp = QApplication.instance()
        if theApp is None:
            theApp = QApplication()

        if theApp is not None:
            # Get my geometry
            frSize = self.frameGeometry()
            debugMessage("Frame size: {}, {}".format(frSize.width(),
                                                     frSize.height()))
            wdSize = self.geometry()
            debugMessage("Widget size: {}, {}".format(wdSize.width(),
                                                      wdSize.height()))

            dtop = theApp.desktop()
            dtSize = dtop.availableGeometry(widget)
            debugMessage("Desktop size: {}, {}".format(dtSize.width(),
                                                       dtSize.height()))

            if parentWidget is None:
                seed()
                leftRoom = dtSize.width() - frSize.width()
                if leftRoom < 0:
                    leftRoom = 0
                    debugMessage("Left Room: {}".format(leftRoom))
                leftPos = randint(int(leftRoom / 4), int((leftRoom * 3) / 4))
                debugMessage("Left Position: {}".format(leftPos))

                topRoom = dtSize.height() - frSize.height()
                if topRoom < 0:
                    topRoom = 0
                debugMessage("Top Room: {}".format(topRoom))
                topPos = randint(int(topRoom / 4), int((topRoom * 3) / 4))
                debugMessage(" Top position: {}".format(topPos))
                newPos = QPoint(leftPos, topPos)
            else:
                # Get the parent position and geometry
                pPos = parentWidget.pos()
                debugMessage("parent position: {}, {}".format(pPos.x(),
                                                              pPos.y()))
                pfrSize = parentWidget.frameGeometry()
                debugMessage("Frame size: {}, {}".format(pfrSize.width(),
                                                         pfrSize.height()))
                pwdSize = parentWidget.geometry()
                debugMessage("Widget size: {}, {}".format(pwdSize.width(),
                                                          pwdSize.height()))

                # Parent center
                pCenter = QPoint(pPos.x() + (pfrSize.width() / 2),
                                 pPos.y() + (pfrSize.height / 2))
                debugMessage("Parent center: {}, {}".format(pCenter.x(),
                                                            pCenter.y()))

                # Use the parent center and our size to create our position
                newPos = QPoint(pCenter.x() - (frSize.width() / 2),
                                pCenter.y() - (frSize.height() / 2))

            debugMessage("New position: {}, {}".format(newPos.x(), newPos.y()))
            self.move(newPos.x(), newPos.y())

    # Manage close to delay it while child threads are running
    def closeEvent(self, event):
        self.listChildren()
        while self.haveRunningThreadOfType(self.childThreadSunrise):
            print("Waiting for a sunrise program to finish")
            sleep(15)
        while self.haveRunningThreadOfType(self.childThreadSunset):
            print("Waiting for a sunset program to finish")
            sleep(15)
        event.accept()

    def showLocation(self):
        # Get our location control
        ctrlLocation = self.findChild(QLabel, "location")
        if ctrlLocation is not None:
            debugMessage("Found location control in main widget")

            latDir = self.getLatitudeDirection(getLatitude())
            lonDir = self.getLongitudeDirection(getLongitude())

            if self.showLocationDMS is False:
                locText = "{}\u00B0 {} {}\u00B0 {}".format(getAbsLatitude(),
                                                           latDir[0],
                                                           getAbsLongitude(),
                                                           lonDir[0])
            else:
                locText = "{}\u00B0 ".format(getLatitudeDegrees())
                locText += "{}\' ".format(getLatitudeMinutes())
                locText += "{}\" ".format(getLatitudeSeconds())
                locText += "{}  ".format(latDir[0])

                locText += "{}\u00B0 ".format(getLongitudeDegrees())
                locText += "{}\' ".format(getLongitudeMinutes())
                locText += "{}\" ".format(getLongitudeSeconds())
                locText += "{} ".format(lonDir[0])

            ctrlLocation.setText(locText)

    # Get the rise or set run program control
    def getSolarCrossingProgramControl(self, atRise=QTS_SUNRISE):
        if atRise == QTS_SUNRISE:
            return self.findChild(QLineEdit, "lnRiseRun")
        return self.findChild(QLineEdit, "lnSetRun")

    # Show the program to run at sunrise or sunset
    def showSolarCrossingProgramText(self, progText, atRise=QTS_SUNRISE):
        if (progText is not None) and (progText != ""):
            if self.isRunnableFile(progText):
                crossingCtrl = self.getSolarCrossingProgramControl(atRise)
                if crossingCtrl is not None:
                    crossingCtrl.setText(progText)

    # Get the text from the control with the program to run at sunrise or
    # sunset
    def getSolarCrossingProgramText(self, atRise=QTS_SUNRISE):
        crossingCtrl = self.getSolarCrossingProgramControl(atRise)
        if crossingCtrl is not None:
            return crossingCtrl.text()

        return None

    # Get whether we run the last past crossing program at launch
    def getRunLastEventAtLaunchControl(self):
        return self.findChild(QCheckBox, "runLastEventAtLaunch")

    # Set/Clear the run last past event at launch checkbox
    def showRunLastEventAtLaunch(self, newVal):
        runLastEventAtLaunchCtrl = self.getRunLastEventAtLaunchControl()
        if runLastEventAtLaunchCtrl is not None:
            runLastEventAtLaunchCtrl.setChecked(newVal)

    def getRunLastEventAtLaunch(self):
        runLastEventAtLaunchCtrl = self.getRunLastEventAtLaunchControl()
        if runLastEventAtLaunchCtrl is not None:
            return runLastEventAtLaunchCtrl.isChecked()

        return False

    # Return True if fileName argument is an existing, executable file
    # else return False
    def isRunnableFile(self, fileName):
        result = False
        if (fileName is not None) and (fileName != ""):
            fInfo = QFileInfo(fileName)
            if (fInfo.exists()) and (fInfo.isExecutable()):
                result = True
        return result

    def runEventProgram(self, fileName):
        if self.isRunnableFile(fileName) is True:
            sproc = subprocess.Popen([fileName],
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT)
            stdout, stderr = sproc.communicate()
            if stderr is None:
                mornInfo = stdout.splitlines()
                for aLine in mornInfo:
                    uText = str(aLine, "utf-8")
                    print("<: {}".format(uText))
            else:
                mornErr = stdout.splitlines()
                for aLine in mornErr:
                    uText = str(aLine, "utf-8")
                    print("<: {}".format(uText))

    # Threaded versions of the exec'ing of sunrise/sunset programs

    def reachedSunriseThreadEntry(self):
        debugMessage("Entered threaded sunrise reached")
        self.runEventProgram(self.getSolarCrossingProgramText(QTS_SUNRISE))
        self.lastY = 128.0
        debugMessage("Exiting threaded sunrise reached")

    def reachedSunsetThreadEntry(self):
        debugMessage("Entered threaded sunset reached")
        self.runEventProgram(self.getSolarCrossingProgramText(QTS_SUNSET))
        self.lastY = 128.0
        debugMessage("Exiting threaded sunset reached")

    def listChildren(self):
        for th in enumerate():
            if th is main_thread():
                continue
            print("We have a thread named: {}".format(th.getName()))

    def threadTypeIs(self, thrdObj, thrdType=childThreadAny):
        if thrdObj is not None:
            thrdName = thrdObj.getName()
            isRise = (thrdName == self.sunriseChildName)
            isSet = (thrdName == self.sunsetChildName)
            if (thrdType == self.childThreadSunrise) and isRise:
                return True
            if (thrdType == self.childThreadSunset) and isSet:
                return True
            if (thrdType == self.childThreadAny) and (isRise or isSet):
                return True

        return False

    def haveRunningThreadOfType(self, thrdType=childThreadAny):
        # Look for instances of the child thread
        hasChildren = False
        for th in enumerate():
            if th is main_thread():
                continue
            if self.threadTypeIs(th, thrdType) is True:
                hasChildren = True
                break

        return hasChildren

    def launchThreadOfType(self, thrdType):
        # If there is no thread already running
        if self.haveRunningThreadOfType(self) is False:
            child = None
            if thrdType == self.childThreadSunrise:
                child = Thread(target=self.reachedSunriseThreadEntry,
                               name=self.sunriseChildName)
            elif thrdType == self.childThreadSunset:
                child = Thread(target=self.reachedSunsetThreadEntry,
                               name=self.sunsetChildName)

            if child is not None:
                child.start()

    def reachedSunrise(self):
        # self.lastY = 128.0
        # self.runEventProgram(self.getSolarCrossingProgramText(QTS_SUNRISE))
        self.launchThreadOfType(self.childThreadSunrise)

    def reachedSunset(self):
        # self.lastY = 128.0
        # self.runEventProgram(self.getSolarCrossingProgramText(QTS_SUNSET))
        self.launchThreadOfType(self.childThreadSunset)

    # Set a supplied time or the current time in the control
    def showTime(self, newTime):
        labTimeNow = self.findChild(QLabel, "timeNow")
        if labTimeNow is not None:
            if newTime is None:
                TimeNow = getTimeNowWithCorrection()
            else:
                TimeNow = newTime
            labTimeNow.setText("{}".format(TimeNow))

    # Show the sunset or sunrise time
    def showSolarCrossingTime(self, crossing=QTS_SUNRISE):
        if crossing == QTS_SUNRISE:
            theTime = getSunriseTime()
            labCtrl = self.findChild(QLabel, "sunrise")
        elif crossing == QTS_SUNSET:
            theTime = getSunsetTime()
            labCtrl = self.findChild(QLabel, "sunset")
        else:
            labCtrl = None

        if labCtrl is not None:
            labCtrl.setText("{}".format(theTime))
            if crossing == QTS_SUNRISE:
                self.shownSRise = theTime
            elif crossing == QTS_SUNSET:
                self.shownSSet = theTime

    def getTargetLineEditColor(self):
        riseRun = self.getSolarCrossingProgramControl(QTS_SUNRISE)
        setRun = self.getSolarCrossingProgramControl(QTS_SUNSET)
        if (riseRun is not None) and (setRun is not None):
            wPalette = riseRun.palette()
            bgBrush = wPalette.brush(QPalette.Active, QPalette.Base)
            self.actvRiseTgtColor = bgBrush.color()
            bgBrush = wPalette.brush(QPalette.Inactive, QPalette.Base)
            self.inactvRiseTgtColor = bgBrush.color()

            wPalette = setRun.palette()
            bgBrush = wPalette.brush(QPalette.Active, QPalette.Base)
            self.actvSetTgtColor = bgBrush.color()
            bgBrush = wPalette.brush(QPalette.Inactive, QPalette.Base)
            self.inactvSetTgtColor = bgBrush.color()
        else:
            self.actvRiseTgtColor = None
            self.inactvRiseTgtColor = None
            self.actvSetTgtColor = None
            self.inactvSetTgtColor = None

    def getMinimumRunControlColor(self):
        minColor = QColor()
        minColor.setNamedColor("darkGray")

        return minColor

    def getTargetColor(self, minColor, maxColor, fraction):
        minRed = minColor.red()
        minGreen = minColor.green()
        minBlue = minColor.blue()

        maxRed = maxColor.red()
        maxGreen = maxColor.green()
        maxBlue = maxColor.blue()

        if (maxRed >= minRed):
            newRed = int(minRed + ((maxRed - minRed) * fraction))
        else:
            newRed = int(maxRed + ((minRed - maxRed) * fraction))
        if (maxGreen >= minGreen):
            newGreen = int(minGreen + ((maxGreen - minGreen) * fraction))
        else:
            newGreen = int(maxGreen + ((minGreen - maxGreen) * fraction))
        if (maxBlue >= minBlue):
            newBlue = int(minBlue + ((maxBlue - minBlue) * fraction))
        else:
            newBlue = int(maxBlue + ((minBlue - maxBlue) * fraction))

        newColor = QColor(newRed, newGreen, newBlue)

        return newColor

    def recolorRunEditBackground(self, rise=QTS_SUNRISE):
        # Get the line edit (rise or set) and it's default background colors
        if rise == QTS_SUNRISE:
            ctrlRun = self.getSolarCrossingProgramControl(QTS_SUNRISE)
            actvTgtColor = self.actvRiseTgtColor
            inactvTgtColor = self.inactvRiseTgtColor
            lightTime = itsNighttime()
        else:
            ctrlRun = self.getSolarCrossingProgramControl(QTS_SUNSET)
            actvTgtColor = self.actvSetTgtColor
            inactvTgtColor = self.inactvSetTgtColor
            lightTime = itsDaytime()

        # IF there is a control and colors
        if (ctrlRun is not None) and\
                (actvTgtColor is not None) and\
                (inactvTgtColor is not None):
            # Get the assumed minimum color
            minColor = self.getMinimumRunControlColor()

            # Get the control palette, active and inactive background brushes
            # and colors
            wPalette = ctrlRun.palette()
            bgBrushActv = wPalette.brush(QPalette.Active, QPalette.Base)
            bgColorActv = bgBrushActv.color()
            bgBrushInactv = wPalette.brush(QPalette.Inactive, QPalette.Base)
            bgColorInactv = bgBrushInactv.color()

            # If we are waiting for the event implied by the value of
            # rise argument
            if lightTime:
                # Get the fraction of the light period passed
                x = getTimeNowFractionOfLightPeriod()

                # Use it to get faded colors that fraction between min and max
                curColorActv = self.getTargetColor(minColor,
                                                   actvTgtColor,
                                                   x)
                curColorInactv = self.getTargetColor(minColor,
                                                     inactvTgtColor,
                                                     x)
            else:
                # Specified control is not the fading one, make it minimum
                curColorActv = minColor
                curColorInactv = minColor

            # Assume no palette change
            newPalette = False

            # If a new active color was created, set the brush and palette
            if not bgColorActv.__eq__(curColorActv):
                bgBrushActv.setColor(curColorActv)
                wPalette.setBrush(QPalette.Active, QPalette.Base, bgBrushActv)
                newPalette = True
            # If a new inactive color was created, set the brush and palette
            if not bgColorInactv.__eq__(curColorInactv):
                bgBrushInactv.setColor(curColorInactv)
                wPalette.setBrush(QPalette.Inactive,
                                  QPalette.Base,
                                  bgBrushInactv)
                newPalette = True
            # If we did change the palette, use it for the control
            if newPalette is True:
                ctrlRun.setPalette(wPalette)

    # Given a number that varies between zero and one, modify it to range from
    # zero to one to zero, peaking when 0.5 is supplied
    def getTimeBounce(self, fromTimeFrac=0.0):
        if fromTimeFrac < 0.5:
            tBounce = 2.0 * fromTimeFrac
        else:
            tBounce = 2.0 * (1.0 - fromTimeFrac)

        return tBounce

    # Given a number that varies between zero and one, modify it to range from
    # one to zero to one, reaching zero when 0.5 is supplied
    def getTimeRevBounce(self, fromTimeFrac=0.0):
        return (1.0 - self.getTimeBounce(fromTimeFrac))

    def getSkyColor(self, timeFrac=0.0, assumeDaytime=False):
        tRevBounce = self.getTimeRevBounce(timeFrac)

        if (assumeDaytime is False) and itsNighttime():
            defaultSky = QColor(0x2A, 0x2A, 0x35)
            if timeFrac >= 0.0:
                skyNow = defaultSky.lighter(100.0 + (75.0 * tRevBounce))
        else:
            defaultSky = QColor(0x87, 0xCE, 0xFA)
            if timeFrac >= 0.0:
                skyScale = pow(2.0, tRevBounce) - 1.0
                skyNow = defaultSky.darker(100.0 + (150.0 * skyScale))

        if timeFrac < 0.0:
            skyNow = defaultSky

        return skyNow

    def getGroundColor(self, timeFrac=0.0):
        defaultGround = QColor(0x7C, 0xFC, 0)
        tBounce = self.getTimeBounce(timeFrac)
        tRevBounce = self.getTimeRevBounce(timeFrac)
        if timeFrac >= 0.0:
            if itsDaytime():
                groundNow = defaultGround.darker(100.0 + (200.0 * tRevBounce))
            else:
                groundNow = defaultGround.darker(300.0 + (250.0 * tBounce))
        else:
            groundNow = defaultGround

        return groundNow

    # Given ellipse width and height, their product and an angle in radians
    # around the ellipse return the polar length from center to the point on
    # the ellipse at that angle
    def polarLength(self, elA, elB, elAB, elTheta):
        aElem = (elA * sin(elTheta))**2
        bElem = (elB * cos(elTheta))**2

        return elAB / sqrt(aElem + bElem)

    def drawIconByAngle(self):
        view = self.findChild(QGraphicsView, "dayIcon")
        if view is not None:
            scene = view.scene()
            if scene is None:
                scene = QGraphicsScene()
                view.setScene(scene)

            # Get the size of the view
            vSize = view.size()
            # debugMessage("View Size: {}, {}".format(vSize.width(),
            #                                         vSize.height()))

            # Work out some sizes for objects in the sky
            objectRad = 12.0 * vSize.height() / 128.0
            objectDiam = 2.0 * objectRad

            # Get the size for the sky
            skySize = QSize(vSize.width(), int(85.0 * vSize.height() / 128.0))
            # debugMessage("Sky Size: {}, {}".format(skySize.width(),
            #                                        skySize.height()))

            # Get the size for the space containing the ellipse that the sky
            # object travels in. It's full ellipse width but half ellipse
            # height. Also allow for a top, left and right one pixel margin.
            # And compensate for the draw function taking a left co-ordinate
            # and width by subtracting the objectDiameter. This allows the
            # object to stay in view when being drawn at the ellipse's right
            # extreme
            elSize = QSize(skySize.width() - 2 - objectDiam,
                           skySize.height() - 1)
            # debugMessage("Ellipse Size: {}, {}".format(elSize.width(),
            #                                            elSize.height()))

            # Get the size of half the horizontal space containing the ellipse
            # that the sky object travels in. It's already helf ellipse height
            elHfSize = QSize(elSize.width() / 2, elSize.height())
            # debugMessage("Ellipse Half Size: {}, {}".format(elHfSize.width(),
            #                                                 elHfSize.height()))

            # Get the center of rotation for the sky object
            elCtr = QPoint(vSize.width() / 2, skySize.height())
            # debugMessage("Ellipse center: {}, {}".format(elCtr.x(),
            #                                              elCtr.y()))

            # Get the product of the ellipse width and height
            elAB = elHfSize.width() * elHfSize.height()

            # Sweep between points one pixel below the left and right
            # horizon limits...using radians
            hLimit = elHfSize.width() - objectRad
            leftStart = atan2(0 - hLimit, -1)
            rightStart = atan2(hLimit, -1)
            # Should be just over pi radians
            sweepAngle = abs(leftStart - rightStart)

            # But, if we just multiply sweepAngle by the fraction of the
            # day/night passed then one end will be at zero radians and all the
            # margin will be at the other end. We need to offset every sky
            # object's angle by half the margin
            sweepOffset = (sweepAngle - pi) / 2.0

            # msg = "Sweep angle {} ({})".format(sweepAngle,
            #                                    sweepAngle * 180.0 / pi))
            # debugMessage(msg)
            # msg = "Sweep offset {} ({})".format(sweepOffset,
            #                                     sweepOffset * 180.0 / pi))
            # debugMessage("Sweep offset {} ({})".format(msg)

            # Get the direction to the Sun (are we in the Southern or Northern
            # hemisphere). True is Northern, False is Southern. True means the
            # sun/moon in a Southerly direction
            skyViewSouth = (getLatitude() >= 0.0)
            # "View to sky object is Southerly: {}".format(skyViewSouth)
            # debugMessage(msg)

            # Ranges from 0.0 to 1.0 through the day or night, used to compute
            # an angle for the sky object.
            if self.forceTime is False:
                t = getTimeNowFractionOfLightPeriod()
            else:
                t = self.savedT + self.forceAmount
                self.savedT = t

            # Pretend it's...
            # t = 0.005

            # msg = "t now as a fraction of current light period: {}".format(t)
            # debugMessage(msg)
            # msg = "t reversed as a fraction of current light period: "
            # msg += "{}".format(tRev)
            # debugMessage(msg)

            # Calculate the current angle simply as a fraction of sweep
            angle = t * sweepAngle

            # Correct it for view direction and the below horizon margins
            if skyViewSouth:
                polAngle = (pi - angle) + sweepOffset
                # debugMessage("S: polar angle {}".format(polAngle))
            else:
                polAngle = angle - sweepOffset
                # debugMessage("N: polar {}".format(polAngle))

            # We have the polar angle, get the polar length
            polLen = self.polarLength(elHfSize.width(), elHfSize.height(),
                                      elAB, polAngle)

            # With polar co-ordinates we can compute x, y

            # x is just the polar length times the cosine of the polar angle...
            # BUT, the draw for the object does it in a rectangle that contains
            # it. So, on the left we can start at the first pixel but on the
            # right we must start object diameter pixels from the right of the
            # view in order to see it. We already made the ellipse width short
            # by the object diameter so if we position it short by object
            # radius it stays in view when above the horizon
            # BUT, the ellipse is currently centered around co-ordinate 0, 0.
            # Also re-position X to the ellipse center's X
            xObject = int(polLen * cos(polAngle) - objectRad + elCtr.x())

            # y is just the polar length times the sine of the polar angle...
            # BUT, Because the view has co-ordinates that grow from zero at the
            # top to higher numbers lower down the view we get the lower half
            # of an ellipse. We have to subtract the y value from the sky
            # height
            yObject = int(skySize.height() - polLen * sin(polAngle))

            # msg = "Sky object is at {}, {}".format(xObject, yObject)
            # msg += " based on polar {} /_ {}".format(polLen, polAngle)
            # msg += " ({})".format(polAngle * 180.0 / pi)
            # debugMessage(msg)

            # If we have changed the object position then choose colors and
            # draw the objects (sky, sky object, ground)
            if (xObject != self.lastXObject) or (yObject != self.lastYObject):
                # debugMessage("Draw new sky object at {}, {}".format(xObject,
                #                                                     yObject))

                # Compute colors based on fraction of day/night time and get
                # pen and brush for each
                groundNow = self.getGroundColor(t)
                skyNow = self.getSkyColor(t, False)
                skyPen = QPen(skyNow,
                              1,
                              Qt.SolidLine,
                              Qt.SquareCap,
                              Qt.BevelJoin)
                skyBrush = QBrush(skyNow)
                groundPen = QPen(groundNow,
                                 1,
                                 Qt.SolidLine,
                                 Qt.SquareCap,
                                 Qt.BevelJoin)
                groundBrush = QBrush(groundNow)

                # Get pen and brush for the object in the sky
                if itsDaytime():
                    # Sun color
                    objectPen = QPen(Qt.yellow,
                                     1,
                                     Qt.SolidLine,
                                     Qt.SquareCap,
                                     Qt.BevelJoin)
                    objectBrush = QBrush(Qt.yellow)
                else:
                    # Moon color
                    objectPen = QPen(Qt.lightGray,
                                     1,
                                     Qt.SolidLine,
                                     Qt.SquareCap,
                                     Qt.BevelJoin)
                    objectBrush = QBrush(Qt.lightGray)

                # Draw the view (sky, object in the sky and ground)
                scene.setSceneRect(0.0, 0.0, vSize.width() * 1.0,
                                   vSize.height() * 1.0)
                scene.clear()
                scene.addRect(0.0, 0.0, skySize.width(), skySize.height(),
                              skyPen, skyBrush)
                scene.addEllipse(xObject,
                                 yObject,
                                 objectDiam,
                                 objectDiam,
                                 objectPen,
                                 objectBrush)
                scene.addRect(0.0,
                              skySize.height(),
                              vSize.width(),
                              vSize.height() - skySize.height(),
                              groundPen,
                              groundBrush)

                # Save the position we drew the sky object at so we don't
                # re-draw in the same place
                self.lastXObject = xObject
                self.lastYObject = yObject

                view.show()

    # Returns true if we are passing sunrise/sunset
    def setNextHorizonCrossingText(self):
        crossed = False
        if itsDaytime():
            if self.nextCrossing is None:
                self.nextCrossing = "sunset"
            elif self.nextCrossing == "sunrise":
                crossed = True

                # Now we are pending sunset
                self.nextCrossing = "sunset"
        else:
            if self.nextCrossing is None:
                self.nextCrossing = "sunrise"
            elif self.nextCrossing == "sunset":
                crossed = True

                # Now we are pending sunrise
                self.nextCrossing = "sunrise"

        # Report unknown crossing name and restore based on day/night
        # time state
        if (self.nextCrossing != "sunrise") and\
                (self.nextCrossing != "sunset"):
            warningMessage("Unrecognized horizon crossing detected: {}".format(self.nextCrossing))
            if itsDaytime():
                self.nextCrossing = "sunset"
            else:
                self.nextCrossing = "sunrise"

        return crossed

    def tick(self):
        # Set the current time in the math library
        setSystemTime()

        # In the main window, show the current, sunrise and sunset times
        self.showTime(None)
        self.showSolarCrossingTime(QTS_SUNRISE)
        self.showSolarCrossingTime(QTS_SUNSET)

        # debugMessage("    Daytime as a fraction of day: {}".format(daytimeFractionOfDay()))
        # debugMessage("  Nighttime as a fraction of day: {}".format(nighttimeFractionOfDay()))
        # debugMessage("Fraction of light period elapsed: {}".format(getTimeNowFractionOfLightPeriod()))
        # debugMessage("Duration of light period elapsed: {}".format(getTimeNowDurationOfLightPeriod()))

        # How long to the next solar horizon crossing. This uses tomorrow's
        # sunrise time when used after today's sunset. The literal sunrise
        # sunset times displayed are always for today however
        diffTime = getTimeToNextHorizonCrossing()

        # Adjust our sense of which horizon crossing is next, if we have
        # just made a crossing
        if self.setNextHorizonCrossingText():
            # Crossing made, run the target program for it
            if self.nextCrossing == "sunset":
                self.reachedSunrise()
            elif self.nextCrossing == "sunrise":
                self.reachedSunset()

        # Display time until the next crossing by name
        labrTimePrompt = self.findChild(QLabel, "rTimePrompt")
        labrTimeValue = self.findChild(QLabel, "rTimeValue")
        if (labrTimePrompt is not None) and (labrTimeValue is not None):
            timeText = "Remaining time until {}:".format(self.nextCrossing)
            labrTimePrompt.setText(timeText)
            labrTimeValue.setText("{}".format(diffTime))

        # Re-color the background of the run at sunrise control
        self.recolorRunEditBackground(QTS_SUNRISE)
        # Re-color the background of the run at sunset control
        self.recolorRunEditBackground(QTS_SUNSET)

        # Show the animated pretend sky view
        self.drawIconByAngle()

    def signLatLonDirection(self, location, direction):
        # If the direction is South or West, the position is negative
        if ((direction == "South") or (direction == "West")) and\
                (location > 0.0):
            location = 0.0 - location
        elif location < 0.0:
            location = abs(location)

        return location

    def getLatitudeDirection(self, latitude):
        if latitude < 0.0:
            return "South"
        else:
            return "North"

    def getLongitudeDirection(self, longitude):
        if longitude < 0.0:
            return "West"
        else:
            return "East"

    def locationClicked(self):
        # Use a dialog to get the settings
        dlg = QDialog(self)
        ui = Ui_QtSsLocationDialog()
        ui.setupUi(dlg)
        ctrlShowLocInDMS = dlg.findChild(QCheckBox, "showLocationInDMS")
        ctrlLatitude = dlg.findChild(QLineEdit, "latitude")
        ctrlLatDir = dlg.findChild(QComboBox, "latDirection")
        ctrlLongitude = dlg.findChild(QLineEdit, "longitude")
        ctrlLonDir = dlg.findChild(QComboBox, "longDirection")
        ctrlCorrectTZ = dlg.findChild(QCheckBox, "chkCorrectForSysTZ")
        ctrlTZ = dlg.findChild(QSpinBox, "tzOffset")
        if (ctrlLatitude is not None) and (ctrlLatDir is not None) and\
                (ctrlLongitude is not None) and (ctrlLonDir is not None) and\
                (ctrlTZ is not None) and (ctrlCorrectTZ is not None) and\
                (ctrlShowLocInDMS is not None):
            debugMessage("Found latitude/longitude controls for init")

            ctrlShowLocInDMS.setChecked(self.showLocationDMS)

            lat = getLatitude()
            latDir = self.getLatitudeDirection(lat)
            lat = abs(lat)
            ctrlLatitude.setText("{}".format(lat))
            i = ctrlLatDir.findText(latDir)
            if i >= 0:
                ctrlLatDir.setCurrentIndex(i)

            lon = getLongitude()
            lonDir = self.getLongitudeDirection(lon)
            lon = abs(lon)
            ctrlLongitude.setText("{}".format(lon))
            i = ctrlLonDir.findText(lonDir)
            if i >= 0:
                ctrlLonDir.setCurrentIndex(i)

            debugMessage("Lat: {}, Lon: {}".format(lat, lon))

            tzOffset = int(getHomeTZ())
            if (tzOffset < -12) or (tzOffset > 12):
                # Invalid, assume Greenwich
                tzOffset = 0

            ctrlTZ.setValue(tzOffset)

            ctrlCorrectTZ.setChecked(getCorrectForSysTZ())

            # Repeat viewing the dialog until it has no problems or we choose
            # to ignore them
            while dlg.exec() == 1:
                debugMessage("Ok pressed")

                # Get the latitude as a number
                lat = ctrlLatitude.text()
                latDir = ctrlLatDir.currentText()
                nLat = float(lat)
                nLat = self.signLatLonDirection(nLat, latDir)

                debugMessage("Lat: {} {}".format(lat, latDir))

                # Get the longitude as a number
                lon = ctrlLongitude.text()
                lonDir = ctrlLonDir.currentText()
                fLon = float(lon)
                nLon = self.signLatLonDirection(fLon, lonDir)

                debugMessage("Lon: {} {}".format(lon, lonDir))

                # Get the timezone hour offset as a number
                tzOffset = ctrlTZ.value()

                # Assuming 360 degrees rotation in 24 hours there are 15
                # degrees of longitude or so per-time zone. Add plus or minus 1
                # for daylight savings or not then there is about a 3 hour
                # range that's realistic for each 15 degrees of rotation. See
                # if the chosen timezone offset is as-expected
                centHour = int((nLon / 15.0))
                minHour = centHour - 1
                maxHour = centHour + 1
                # debugMessage("At longitude {}: centHour {}, minHour {}, maxHour {}".format(nLon, centHour, minHour, maxHour))
                if (tzOffset < minHour) or (tzOffset > maxHour):
                    tzMsg = QMessageBox()
                    msgTxt = "The timezone offset hours is more likely to be "
                    msgTxt += "between {} and {} ".format(minHour, maxHour)
                    msgTxt += "at {} {} longitude".format(fLon, lonDir)
                    msgTxt += ", are you sure you want to use "
                    msgTxt += "{}".format(tzOffset)
                    tzMsg.setText(msgTxt)
                    tzMsg.setStandardButtons(QMessageBox.Yes |
                                             QMessageBox.Retry |
                                             QMessageBox.Cancel)
                    tzMsg.setDefaultButton(QMessageBox.Retry)
                    tzMsg.setEscapeButton(QMessageBox.Cancel)
                    ret = tzMsg.exec()
                    if ret == QMessageBox.Cancel:
                        # Cancel, exit the loop that re-shows the dialog box
                        # but don't set any configuration
                        break
                else:
                    # Timezone is in expected longitude range
                    ret = QMessageBox.Yes

                # If the timezone is in the expected range or we said we want
                # it anyway
                if ret == QMessageBox.Yes:
                    # Set the new configuration based on the entered values

                    # Location
                    self.showLocationDMS = ctrlShowLocInDMS.isChecked()
                    setLatitude(nLat)
                    setLongitude(nLon)

                    # Timezone clock offset
                    setHomeTZ(3600.0 * tzOffset)

                    # Correct our clock for a different timezone from the
                    # system clock
                    setCorrectForSysTZ(ctrlCorrectTZ.isChecked())

                    # Cause any changes to appear via a call to the timer tick
                    self.tick()

                    break

                # Retry, loop and re-show the dialog box for user correction

            # Display any new location
            self.showLocation()
        else:
            warningMessage("location controls NOT found", self.appSrcFrom)

    def getChooseDirFrom(self, curFile=None):
        if (curFile is None) or (curFile == ""):
            # No file given, use the config file directory
            useDir = self.getConfigFileDir()
        else:
            # Find the last slash
            lSlash = curFile.rfind("/")
            useDir = curFile[0:lSlash]

        return useDir

    def chooseRunnableFile(self, curFile, crossing=QTS_SUNRISE):
        if crossing == QTS_SUNRISE:
            horizonText = "sunrise"
        elif crossing == QTS_SUNSET:
            horizonText = "sunset"
        else:
            horizonText = None

        newFile = ""
        if horizonText is not None:
            homeDir = self.getChooseDirFrom(curFile)
            ofPrompt = "Choose a program to be run at {}".format(horizonText)
            (fileName, selFilter) = QFileDialog.getOpenFileName(self,
                                                                ofPrompt,
                                                                homeDir,
                                                                "Files (*)")
            if (fileName is not None) and (fileName != ""):
                if self.isRunnableFile(fileName):
                    newFile = fileName
                else:
                    msgTxt = "The chosen file does not exist or is not "
                    msgTxt += "executable and will not be used. You must "
                    msgTxt += "choose an existing, executable file."
                    QMessageBox.information(self, "Error", msgTxt)

        return newFile

    def chooseSolarCrossingRun(self, crossing=QTS_SUNRISE):
        curFile = self.getSolarCrossingProgramText(crossing)
        fileName = self.chooseRunnableFile(curFile, crossing)
        self.showSolarCrossingProgramText(fileName, crossing)

    def chooseRiseRun(self):
        self.chooseSolarCrossingRun(QTS_SUNRISE)

    def chooseSetRun(self):
        self.chooseSolarCrossingRun(QTS_SUNRISE)

    def getConfigFileDir(self):
        # Get the home directory path
        homePath = QDir.homePath()
        if homePath is not None:
            if homePath[-1] != '/':
                homePath += '/'

    # There are a few configuration items that have to be preset in case they
    # aren't loadable from a config file
    def presetConfig(self):
        self.showLocationDMS = False
        self.initRiseRun = None
        self.initSetRun = None
        self.initRunLastEventAtLaunch = False

    def loadConfig(self):
        config = SunsetterConfig()
        if config.loadConfig():
            self.showLocationDMS = config.getShowLocationDMS()
            nVal = config.getLatitude()
            if nVal is not None:
                setLatitude(nVal)
            nVal = config.getLongitude()
            if nVal is not None:
                setLongitude(nVal)
            nVal = config.getHomeTZ()
            if nVal is not None:
                setHomeTZ(nVal * 3600.0)
            bVal = config.getCorrectForSysTZ()
            if bVal is not None:
                setCorrectForSysTZ(bVal)
            self.initRiseRun = config.getSolarCrossingRun(QTS_SUNRISE)
            self.showSolarCrossingProgramText(self.initRiseRun,
                                              QTS_SUNRISE)
            # debugMessage("sunrise program = {}".format(self.initRiseRun))
            self.initSetRun = config.getSolarCrossingRun(QTS_SUNSET)
            self.showSolarCrossingProgramText(self.initSetRun,
                                              QTS_SUNSET)
            self.initRunLastEventAtLaunch = config.getRunLastEventAtLaunch()
            self.showRunLastEventAtLaunch(nVal)
            # debugMessage("sunset program = {}".format(self.initSetRun))

    # Save the config but only replace supported configuration items while
    # keeping all other content
    def saveConfig(self):
        config = SunsetterConfig()
        print("Saving Config")
        print("showLocationDMS is {}".format(self.showLocationDMS))
        config.setShowLocationFormat(self.showLocationDMS)
        config.setLatitude(getLatitude())
        config.setLongitude(getLongitude())
        config.setCorrectForSysTZ(getCorrectForSysTZ())
        config.setHomeTZ(getHomeTZ())
        crTxt = self.getSolarCrossingProgramText(QTS_SUNRISE)
        config.setSolarCrossingRun(crTxt, QTS_SUNRISE)
        crTxt = self.getSolarCrossingProgramText(QTS_SUNSET)
        config.setSolarCrossingRun(crTxt, QTS_SUNSET)
        config.setRunLastEventAtLaunch(self.getRunLastEventAtLaunch())
        config.saveConfig()
        print("Saved Config")
        print("showLocationDMS is {}".format(self.showLocationDMS))


disableDebug()
# enableDebug()

# disableWarnings()
enableWarnings()

if __name__ == "__main__":
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    app = QApplication([])
    widget = QtSunsetter()
    widget.position_ui()
    widget.show()
    sys.exit(app.exec_())
