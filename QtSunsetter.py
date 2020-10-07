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

import sys
import os
import re
import subprocess

from PySide2.QtWidgets import QApplication, QWidget, QPushButton, QDialog
from PySide2.QtWidgets import QLineEdit, QLabel, QComboBox, QCheckBox
from PySide2.QtWidgets import QSpinBox, QMessageBox, QFileDialog
from PySide2.QtCore import QFile, QPoint, QObject, QTimer, SIGNAL, SLOT
from PySide2.QtCore import QDir, QIODevice, QTextStream, QFileInfo
from PySide2.QtGui import QColor, QPalette, QBrush
from PySide2.QtUiTools import QUiLoader
from random import seed, randint
from QtSsLocationDialog import Ui_QtSsDialog
# from QtSsLocation import Ui_QtSsDialog
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
from QtSsConfig import SunsetterConfig
from QtSsDebug import debugMessage, disableDebug, enableDebug, debugIsEnabled


class QtSunsetter(QWidget):
    def __init__(self):
        super(QtSunsetter, self).__init__()
        self.nextCrossing = None
        setLocalTZ()
        self.loadConfig()
        self.timer = QTimer(self)
        self.load_ui()

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

        # Show any saved sunset/sunrise programs
        if self.initRiseRun is not None:
            riseRun = self.findChild(QLineEdit, "lnRiseRun")
            if riseRun is not None:
                riseRun.setText(self.initRiseRun)
        if self.initSetRun is not None:
            setRun = self.findChild(QLineEdit, "lnSetRun")
            if setRun is not None:
                setRun.setText(self.initSetRun)

        # Connect the set location button to our slot
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
        self.timer.timeout.connect(self.tick)
        if debugIsEnabled():
            # If debugging, watch the clocks tick
            self.timer.start(1000)
        else:
            # Not debugging, just update them every minute
            self.timer.start(60000)

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

    def sunriseReached(self):
        riseRun = self.findChild(QLineEdit, "lnRiseRun")
        if riseRun is not None:
            self.runEventProgram(riseRun.text())

    def sunsetReached(self):
        setRun = self.findChild(QLineEdit, "lnSetRun")
        if setRun is not None:
            self.runEventProgram(setRun.text())

    # Set a supplied time or the current time in the control
    def showTime(self, newTime):
        labTimeNow = self.findChild(QLabel, "timeNow")
        if labTimeNow is not None:
            if newTime is None:
                TimeNow = getTimeNowWithCorrection()
            else:
                TimeNow = newTime
            labTimeNow.setText("{}".format(TimeNow))

    def showSunriseTime(self):
        # Get today's sunrise time and show it if it is not what we last showed
        # NB: Although we use tomorrow's sunrise to give the time until sunrise
        # after sunset has passed, we only show today's sunrise and sunset
        # literal times
        sRise = getSunriseTime()
        if sRise != self.shownSRise:
            labSunrise = self.findChild(QLabel, "sunrise")
            if labSunrise is not None:
                labSunrise.setText("{}".format(sRise))
                self.shownSRise = sRise

    def showSunsetTime(self):
        # Get today's sunset time and show it if it is not what we last showed
        sSet = getSunsetTime()
        if sSet != self.shownSSet:
            labSunset = self.findChild(QLabel, "sunset")
            if labSunset is not None:
                labSunset.setText("{}".format(sSet))
                self.shownSSet = sSet

    def getTargetLineEditColor(self):
        riseRun = self.findChild(QLineEdit, "lnRiseRun")
        setRun = self.findChild(QLineEdit, "lnSetRun")
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

    def recolorRunEditBackground(self, rise=True):
        # Get the line edit (rise or set) and it's default background colors
        if rise is True:
            ctrlRun = self.findChild(QLineEdit, "lnRiseRun")
            actvTgtColor = self.actvRiseTgtColor
            inactvTgtColor = self.inactvRiseTgtColor
            lightTime = itsNighttime()
        else:
            ctrlRun = self.findChild(QLineEdit, "lnSetRun")
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

    def tick(self):
        # Set the current time in the math library
        setSystemTime()

        # In the main window, show the current, sunrise and sunset times
        self.showTime(None)
        self.showSunriseTime()
        self.showSunsetTime()

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
                self.sunriseReached()

                # Now we are pending sunset
                self.nextCrossing = "sunset"
        else:
            if self.nextCrossing is None:
                self.nextCrossing = "sunrise"
            elif self.nextCrossing == "sunset":
                self.sunsetReached()

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
        self.recolorRunEditBackground(True)
        # Re-color the background of the run at sunset control
        self.recolorRunEditBackground(False)

    def signLatLonDirection(self, location, direction):
        # If the direction is South or West, the position is negative
        if ((direction == "South") or (direction == "West")) and\
                (location > 0.0):
            location = 0 - location
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
        ui = Ui_QtSsDialog()
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
            debugMessage("location controls NOT found")

    def getChooseDirFrom(self, curFile=None):
        if (curFile is None) or (curFile == ""):
            # No file given, use the config file directory
            useDir = self.getConfigFileDir()
        else:
            # Find the last slash
            lSlash = curFile.rfind("/")
            useDir = curFile[0:lSlash]

        return useDir

    def chooseRunnableFile(self, sunHorizon, curFile):
        newFile = ""
        if (sunHorizon == "sunrise") or (sunHorizon == "sunset"):
            homeDir = self.getChooseDirFrom(curFile)
            ofPrompt = "Choose a program to be run at {}".format(sunHorizon)
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

    def chooseRiseRun(self):
        riseRun = self.findChild(QLineEdit, "lnRiseRun")
        if riseRun is not None:
            fileName = self.chooseRunnableFile("sunrise", riseRun.text())
            if (fileName is not None) and (fileName != ""):
                riseRun.setText("{}".format(fileName))

    def chooseSetRun(self):
        setRun = self.findChild(QLineEdit, "lnSetRun")
        if setRun is not None:
            fileName = self.chooseRunnableFile("sunset", setRun.text())
            if (fileName is not None) and (fileName != ""):
                setRun.setText("{}".format(fileName))

    def getConfigFileDir(self):
        # Get the home directory path
        homePath = QDir.homePath()
        if homePath is not None:
            if homePath[-1] != '/':
                homePath += '/'

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
            self.initRiseRun = config.getSunriseRun()
            if self.initRiseRun is not None:
                if self.isRunnableFile(self.initRiseRun):
                    riseRun = self.findChild(QLineEdit, "lnRiseRun")
                    if riseRun is not None:
                        riseRun.setText("{}".format(self.initRiseRun))
                # debugMessage("sunrise program = {}".format(self.initRiseRun))
            self.initSetRun = config.getSunsetRun()
            if self.initSetRun is not None:
                if self.isRunnableFile(self.initSetRun):
                    setRun = self.findChild(QLineEdit, "lnSetRun")
                    if setRun is not None:
                        setRun.setText("{}".format(self.initSetRun))
                # debugMessage("sunset program = {}".format(self.initSetRun))

    # Save the config but only replace supported configuration items while
    # keeping all other content
    def saveConfig(self):
        config = SunsetterConfig()
        config.setLatitude(getLatitude())
        config.setLongitude(getLongitude())
        config.setCorrectForSysTZ(getCorrectForSysTZ())
        config.setHomeTZ(getHomeTZ())
        riseRun = self.findChild(QLineEdit, "lnRiseRun")
        if riseRun is not None:
            config.setSunriseRun(riseRun.text())
        setRun = self.findChild(QLineEdit, "lnSetRun")
        if setRun is not None:
            config.setSunsetRun(setRun.text())
        config.saveConfig()


disableDebug()
# enableDebug()

if __name__ == "__main__":
    app = QApplication([])
    widget = QtSunsetter()
    widget.position_ui()
    widget.show()
    sys.exit(app.exec_())
