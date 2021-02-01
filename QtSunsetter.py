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

from math import sin, cos, atan2, pow, sqrt
# from math import tan, asin, acos, radians, pi, degrees,

from threading import enumerate, main_thread, Thread
from time import sleep

from PySide2.QtWidgets import QApplication, QWidget, QPushButton, QDialog
from PySide2.QtWidgets import QLineEdit, QLabel, QComboBox, QCheckBox
from PySide2.QtWidgets import QSpinBox, QMessageBox, QFileDialog
from PySide2.QtWidgets import QGraphicsView, QGraphicsScene
from PySide2.QtCore import Qt
from PySide2.QtCore import QFile, QPoint, QObject, QTimer, SIGNAL, SLOT
from PySide2.QtCore import QDir, QFileInfo, QCoreApplication
from PySide2.QtGui import QColor, QPen
from PySide2.QtGui import QPalette, QBrush
# from PySide2.QtGui import QPainter, QIcon
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
from QtSsMath import setLatitude, setLongitude, getLatitude, setSystemTime
from QtSsMath import getLongitude, getHomeTZ, setHomeTZ, setLocalTZ
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
        self.forceAmount = 0.02

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

            nLat = getLatitude()
            latDir = self.getLatitudeDirection(nLat)
            nLat = abs(nLat)

            nLon = getLongitude()
            lonDir = self.getLongitudeDirection(nLon)
            nLon = abs(nLon)

            locText = "{} {} {} {}".format(nLat, latDir[0], nLon, lonDir[0])
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
        print("Entered threaded sunrise reached")
        self.runEventProgram(self.getSolarCrossingProgramText(QTS_SUNRISE))
        self.lastY = 128.0
        print("Exiting threaded sunrise reached")

    def reachedSunsetThreadEntry(self):
        print("Entered threaded sunset reached")
        self.runEventProgram(self.getSolarCrossingProgramText(QTS_SUNSET))
        self.lastY = 128.0
        print("Exiting threaded sunset reached")

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

    def skyObjectHypotenuse(self, tFrac, xVal, yVal):
        tRevFrac = 1.0 - tFrac
        hyp = sqrt(pow(tRevFrac * xVal, 2)
                   + pow(tFrac * yVal, 2))
        return hyp

    def hypotenuseX(self, hyp, angle, xCenter, xOffsets):
        newX = xCenter - (cos(angle) * hyp) + xOffsets
        return newX

    def hypotenuseY(self, hyp, angle, yCenter, yOffsets):
        yNew = yCenter - (sin(angle) * hyp) + yOffsets

        # Keep a note of the maximum Y position (lower numbers are higher
        # up the view)
        if yNew < self.yMaxObject:
            self.yMaxObject = yNew

        return yNew

    # The object will reach the top before the center, cycle down and back up
    # before descending on the other side, make it lock on the top when reached
    def topLock(self, wAngle, topAngle, yObject, sweepAngle):
        yNew = yObject

        # If we are before the mid-point we shouldn't be declining
        if wAngle < topAngle:
            if yObject > self.lastYObject:
                yNew = self.yMaxObject
                if self.lockAngle == 0.0:
                    self.lockAngle = wAngle
                # print("lock /_ {}".format(self.lockAngle))
        elif wAngle >= topAngle:
            # If we are at or passing the mid-point we should stay up
            # until the opposite of the lock angle
            if self.lockAngle != 0.0:
                unlockAngle = sweepAngle - self.lockAngle
                # print("unlock /_ {}".format(unlockAngle))
                if wAngle <= unlockAngle:
                    yNew = self.yMaxObject
                else:
                    self.lockAngle = 0.0

        return yNew

    def drawIconByAngle(self):
        view = self.findChild(QGraphicsView, "dayIcon")
        if view is not None:
            scene = view.scene()
            if scene is None:
                scene = QGraphicsScene()
                view.setScene(scene)

            # Some constants used a lot so give them names
            ySize = 128.0
            maxY = 127.0
            yHalfSize = ySize / 2.0
            # minXY = 0.0
            # maxXY = 127.0
            xSize = 460.0
            maxX = 459.0
            offsetY = ySize - maxY
            objectRad = 12.0
            objectDiam = 2.0 * objectRad
            skyHeight = 85
            # groundHeight = vSize - skyHeight
            horizonLine = skyHeight - offsetY
            skyExtra = (skyHeight - yHalfSize) + offsetY
            xCenter = maxX / 2.0
            yCenter = horizonLine + 0.5
            margin = 2.0
            # topAngle = pi / 2.0
            # nudge = 0.5

            # Get the direction to the Sun (are we in the Southern or Northern
            # hemisphere). True is Northern, False is Southern
            skyViewSouth = (getLatitude() >= 0.0)
            # skyViewSouth = False
            # print("{} becomes {}".format(getLatitude(), skyViewSouth))

            # Sweep between points one pixel below the left and right
            # horizon limits
            hLimit = xCenter - objectRad
            leftStart = atan2(0 - hLimit, -1)
            rightStart = atan2(hLimit, -1)
            sweepAngle = abs(leftStart - rightStart)
            topAngle = sweepAngle / 2.0

            # The excess on each side is half of the sweep angle minus pi (180
            # degrees)
            # startAngle = (sweepAngle - pi) / 2.0

            # print("{}, {}, {}".format(sweepAngle, leftStart, rightStart))

            # Ranges from 0.0 to 1.0, used to compute a location for
            # the sky object. Get other ranges for the same
            if self.forceTime is False:
                t = getTimeNowFractionOfLightPeriod()
            else:
                t = self.savedT + self.forceAmount
                self.savedT = t
            # t = 0.9945505
            tRev = 1.0 - t
            if t < 0.5:
                tBounce = 2.0 * t
            else:
                tBounce = 2.0 * (1.0 - t)
            tRevBounce = 1.0 - tBounce
            # print("t {} / {} / {} / {}".format(t, tRev, tBounce, tRevBounce))

            # Calculate a horizontal offset for margin, it is negative on
            # the right, zero in the center and positive on the left
            xOffset = tRevBounce * 6.0
            if t > 0.5:
                xOffset = 0.0 - xOffset

            # Calculate the current angle based on a South or North view of
            # the sun/moon. Also get a single direction working angle for
            # both views
            if skyViewSouth is True:
                angle = t * sweepAngle
                wAngle = angle
            else:
                angle = tRev * sweepAngle
                wAngle = sweepAngle - angle

                # North view goes in the opposite direction from the South view
                xOffset = 0 - xOffset

            # print("/_ {}".format(angle))

            # Calculate the "hypotenuse length of the line to the object
            # DWH: 2020/11/15 hyp = round(yHalfSize + (tBounce * skyExtra), 2)
            hyp = self.skyObjectHypotenuse(tBounce, xCenter, skyHeight)
            # print("{}".format(hyp))

            # Plus a little static offset
            # xOffset += 1.0

            # Calculate a vertical offset for top margin, it is zero at
            # the horizon and positive at the top of the sky
            # yOffset = tBounce * 2.5 * margin
            yOffset = tBounce * 8.0

            # Now get x and y
            xObject = self.hypotenuseX(hyp,
                                       angle,
                                       xCenter,
                                       xOffset - objectRad)
            yNew = self.hypotenuseY(hyp,
                                    angle,
                                    yCenter,
                                    yOffset)
            yObject = self.topLock(wAngle, topAngle, yNew, sweepAngle)

            # print("{}/{} ... {}".format(yObject, self.lastYObject, self.yMaxObject))
            # print("{}, {}". format(xCenter, yCenter))
            # print("{} : {} : {} : {}".format(degrees(angle), hyp, xOffset, tRev))
            # print("pos {}, {}". format(xObject, yObject))

            # Compute colors based on fraction of day/night time
            groundColor = QColor(0x7C, 0xFC, 0)
            if itsDaytime():
                # skyColor = QColor(0x87, 0xCE, 0xEB)
                skyColor = QColor(0x87, 0xCE, 0xFA)
                # skyNow = skyColor.darker(100.0 + (150.0 * tRevBounce))
                # Use a more rapid rate of change closer to the crossing
                skyScale = pow(2.0, tRevBounce) - 1.0
                skyNow = skyColor.darker(100.0 + (150.0 * skyScale))
                groundNow = groundColor.darker(100.0 + (200.0 * tRevBounce))
                objectPen = QPen(Qt.yellow,
                                 1,
                                 Qt.SolidLine,
                                 Qt.SquareCap,
                                 Qt.BevelJoin)
                objectBrush = QBrush(Qt.yellow)
            else:
                skyColor = QColor(0x2A, 0x2A, 0x35)
                skyNow = skyColor.lighter(100.0 + (75.0 * tRevBounce))
                groundNow = groundColor.darker(300.0 + (250.0 * tBounce))
                objectPen = QPen(Qt.lightGray,
                                 1,
                                 Qt.SolidLine,
                                 Qt.SquareCap,
                                 Qt.BevelJoin)
                objectBrush = QBrush(Qt.lightGray)

            # Draw the objects if we have changed the object position
            if (xObject != self.lastXObject) or (yObject != self.lastYObject):
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

                scene.setSceneRect(0.0, 0.0, xSize, ySize)
                scene.clear()
                scene.addRect(0.0, 0.0, xSize, horizonLine, skyPen, skyBrush)
                scene.addEllipse(xObject,
                                 yObject,
                                 objectDiam,
                                 objectDiam,
                                 objectPen,
                                 objectBrush)
                scene.addRect(0.0,
                              horizonLine,
                              xSize,
                              ySize - horizonLine,
                              groundPen,
                              groundBrush)
                self.lastXObject = xObject
                self.lastYObject = yObject
                view.show()

    # Draw a pretend sun/moon position icon based on the time and horizon
    # event timestamps
    def drawIcon(self):
        view = self.findChild(QGraphicsView, "dayIcon")
        if view is not None:
            scene = view.scene()
            if scene is None:
                scene = QGraphicsScene()
                view.setScene(scene)

            # Some constants used a lot so give them names
            objectRad = 12.0
            objectDiam = 2.0 * objectRad
            horizon = 86.0
            vSize = 128.0
            margin = 2.0
            lrMargins = 2.0 * margin
            # panRange = vSize - objectDiam - lrMargins
            panRange = vSize - objectRad - lrMargins
            panOffset = lrMargins
            skyHeight = horizon
            topMargin = 2.0
            tiltRange = skyHeight - topMargin
            tiltOffset = 1.0

            # Ranges from 0.0 to 1.0, use it to compute a location for
            # the sky object
            x = getTimeNowFractionOfLightPeriod()
            # x = 0.92
            revX = 1.0 - x
            # Create xPart in range 0...1...0 evenly through light period
            if x < 0.5:
                xPart = 2.0 * x
            else:
                xPart = 2.0 * (1.0 - x)
            # Create revPart in range 1...0...1 evenly through light period
            revPart = 1.0 - xPart
            # print("{} : {} : {} : {}".format(x, xPart, revPart, panRange))

            # pan = vSize - (objectRad + (x * (vSize - objectRad - 8.0)))
            # We pan an object of a given diameter to the fraction of the
            # light period from right (max) to left (zero) so that the left
            # and right edges of it never reach or pass the horizontal edge
            # of the view. The left and right of the circle are not always
            # visible, so the range where they can be is from about 8% to
            # 92% of the light period.
            # The workspace for the left edge of the object is the view size
            # minus one radius of the object minus both margins
            # Then, shift the result two margins to the left
            # zzzX = revX
            # zzzA = panRange
            # zzzB = revX * panRange
            # zzzC = zzzB - panOffset
            # zzzD = zzzC
            # zzzE = 0.0
            # print("{} : {} : {} : {} : {} : {} : {}".format(vSize, zzzX, zzzA, zzzB, zzzC, zzzD, zzzE))
            # pan = (panRange - (x * panRange)) - margin
            # pan = zzzD
            pan = (revX * panRange) - panOffset
            # print("{} : {} : {}".format(pan, objectRad, objectDiam))
            # 0 (12)----(12) 128

            # We tilt an object of a given diameter from just under the horizon
            # up to just under the top of the view at the fraction of the light
            # period being 0.5 then down for the second half of the light
            # period. xPart already goes from 0...1...0 across the light
            # period with the peak in the middle of the light period
            # Height range is between the line under the horizon and the line
            # before the top of the view. Top of view is zero, high point of
            # range is 1.0, lower positions have higher y co-ordinate
            # Center of object moves whole skyHeight because it starts one
            # margin under horizon and peaks at one margin under top of view
            # xPart goes from zero to one at middle of day/night and back to
            # zero. So xPart is the fraction of the actual height we
            # need to be under the top of the view
            # Offset it all down (higher numbers) one margin only, the height
            # value is the y coordinate of the top of the circle
            # height = horizon - (2.0 * xPart * tiltRange)
            # print("{}".format(xPart))
            # print("{}".format(tiltRange))
            # print("{}".format(tiltOffset))
            # yPart = 0.1
            height = (horizon - (xPart * tiltRange)) + tiltOffset
            # (86 - (2.0 * 0.1 * 86)) + 13
            # (86 - (0.2 * 86)) + 13
            # (86 - 17) + 13
            # 82
            # (86 - (2.0 * 0.0 * 86)) + 13
            # (86 - (0.0 * 86)) + 13
            # (86 - 0) + 13
            # 99
            # (86 - (2.0 * 0.0 * 86)) + 1.0
            # (86 - (0.0 * 86)) + 1
            # (86 - 0) + 1
            # 87
            # (86 - (2.0 * 0.5 * 86)) + 1.0
            # (86 - (1.0 * 86)) + 1
            # (86 - 86) + 1
            # 1

            groundColor = QColor(0x7C, 0xFC, 0)
            if itsDaytime():
                # skyColor = QColor(0x87, 0xCE, 0xEB)
                skyColor = QColor(0x87, 0xCE, 0xFA)
                # Set brightness based on fraction of day (0.5 is peak)
                skyNow = skyColor.darker(125.0 + (125.0 * revPart))
                groundNow = groundColor.darker(150.0 + (150.0 * revPart))
                objectPen = QPen(Qt.yellow,
                                 1,
                                 Qt.SolidLine,
                                 Qt.SquareCap,
                                 Qt.BevelJoin)
                objectBrush = QBrush(Qt.yellow)
            else:
                skyColor = QColor(0x2A, 0x2A, 0x35)
                skyNow = skyColor.lighter(110.0 * revPart)
                groundNow = groundColor.darker(300.0 + (150.0 * xPart))
                objectPen = QPen(Qt.lightGray,
                                 1,
                                 Qt.SolidLine,
                                 Qt.SquareCap,
                                 Qt.BevelJoin)
                objectBrush = QBrush(Qt.lightGray)

            # groundNow = groundColor.darker(300.0 + 150.0)
            # skyNow = skyColor.darker(250.0 * (0.99 - 0.5))
            # skyColorB = QColor(0x2A, 0x2A, 0x35)
            # groundNow = skyColorB.lighter(110.0 * (0.99 - 0.0))
            # skyNow = groundColor.darker(300.0)
            # groundNow = groundColor.darker(300.0)

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

            scene.setSceneRect(0.0, 0.0, vSize, vSize)
            if (pan != self.lastPan) or (height != self.lastHeight):
                scene.clear()
                scene.addRect(0.0, 0.0, vSize, horizon, skyPen, skyBrush)
                scene.addEllipse(pan,
                                 height,
                                 objectDiam,
                                 objectDiam,
                                 objectPen,
                                 objectBrush)
                scene.addRect(0.0,
                              horizon,
                              vSize,
                              vSize - horizon,
                              groundPen,
                              groundBrush)
                self.lastPan = pan
                self.lastHeight = height
                view.show()

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
        if itsDaytime():
            if self.nextCrossing is None:
                self.nextCrossing = "sunset"
            elif self.nextCrossing == "sunrise":
                self.reachedSunrise()

                # Now we are pending sunset
                self.nextCrossing = "sunset"
        else:
            if self.nextCrossing is None:
                self.nextCrossing = "sunrise"
            elif self.nextCrossing == "sunset":
                self.reachedSunset()

                # Now we are pending sunrise
                self.nextCrossing = "sunrise"

        # Display it with a relevant prompt
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

        # self.drawIcon()
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
        ctrlLatitude = dlg.findChild(QLineEdit, "latitude")
        ctrlLatDir = dlg.findChild(QComboBox, "latDirection")
        ctrlLongitude = dlg.findChild(QLineEdit, "longitude")
        ctrlLonDir = dlg.findChild(QComboBox, "longDirection")
        ctrlCorrectTZ = dlg.findChild(QCheckBox, "chkCorrectForSysTZ")
        ctrlTZ = dlg.findChild(QSpinBox, "tzOffset")
        if (ctrlLatitude is not None) and (ctrlLatDir is not None) and\
                (ctrlLongitude is not None) and (ctrlLonDir is not None) and\
                (ctrlTZ is not None) and (ctrlCorrectTZ is not None):
            debugMessage("Found latitude/longitude controls for init")

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
                    setLatitude(nLat)
                    setLongitude(nLon)

                    # Timezone clock offset
                    setHomeTZ(3600.0 * tzOffset)

                    # Correct our clock for a different timezone from the
                    # system clock
                    setCorrectForSysTZ(ctrlCorrectTZ.isChecked())
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
        self.initRiseRun = None
        self.initSetRun = None
        self.initRunLastEventAtLaunch = False

    def loadConfig(self):
        config = SunsetterConfig()
        if config.loadConfig():
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


disableDebug()
# enableDebug()

disableWarnings()
# enableWarnings()

if __name__ == "__main__":
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    app = QApplication([])
    widget = QtSunsetter()
    widget.position_ui()
    widget.show()
    sys.exit(app.exec_())
