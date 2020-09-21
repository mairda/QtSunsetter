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
import time
import datetime
import re

from PySide2.QtWidgets import QApplication, QWidget, QPushButton, QDialog
from PySide2.QtWidgets import QLineEdit, QLabel, QComboBox, QCheckBox
from PySide2.QtWidgets import QSpinBox, QMessageBox
from PySide2.QtCore import QFile, QPoint, QObject, QTimer, SIGNAL, SLOT
from PySide2.QtCore import QDir, QIODevice, QTextStream
from PySide2.QtUiTools import QUiLoader
from random import seed, randint
from QtSsLocationDialog import Ui_QtSsDialog
# from QtSsLocation import Ui_QtSsDialog
from QtSsDebug import debugMessage, disableDebug, enableDebug, debugIsEnabled
from QtSsMath import LocalSunrise, LocalSunset, timeFromDayFraction
from QtSsMath import setLatitude, setLongitude, getLatitude, setSystemTime
from QtSsMath import getLongitude, getHomeTZ, setHomeTZ, setLocalTZ


class QtSunsetter(QWidget):
    def __init__(self):
        super(QtSunsetter, self).__init__()
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

        # Cause the time to set
        self.tick()

        # Show any saved location
        self.showLocation()

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

    def getTimeNow(self):
        systemTime = time.localtime()
        return datetime.time(systemTime[3], systemTime[4], systemTime[5])

    def getTimeNowDelta(self):
        TimeNow = self.getTimeNow()

        return datetime.timedelta(hours=TimeNow.hour,
                                  minutes=TimeNow.minute,
                                  seconds=TimeNow.second)

    def getTimeNowWithCorrection(self):
        timeNow = self.getTimeNow()
        correctHour = timeNow.hour
        if self.CorrectForSysTZ is True:
            systemTime = time.localtime()
            sysTZ = 1.0 * systemTime.tm_gmtoff
            sysTZ /= 3600.0
            usingTZ = getHomeTZ()

            correction = int(usingTZ - sysTZ)

            correctHour += correction
            while correctHour < 0:
                correctHour += 24
            while correctHour > 23:
                correctHour -= 24

        correctedTime = datetime.time(correctHour,
                                      timeNow.minute,
                                      timeNow.second)
        # debugMessage("UsingTZ: {}, SysTZ: {}, Correction: {}, Hour: {} => {}".format(usingTZ, sysTZ, correction, timeNow.hour, correctHour))

        return correctedTime

    def getTimeNowDeltaWithCorrection(self):
        TimeNow = self.getTimeNowWithCorrection()

        return datetime.timedelta(hours=TimeNow.hour,
                                  minutes=TimeNow.minute,
                                  seconds=TimeNow.second)

    def getSunriseTime(self):
        Today = datetime.date.today()
        aTime = datetime.time(0, 6, 0)

        x = LocalSunrise(Today, aTime)
        return timeFromDayFraction(x)

    def getSunsetTime(self):
        Today = datetime.date.today()
        aTime = datetime.time(0, 6, 0)

        x = LocalSunset(Today, aTime)
        return timeFromDayFraction(x)

    def getSunriseDelta(self):
        sRise = self.getSunriseTime()
        return datetime.timedelta(hours=sRise.hour,
                                  minutes=sRise.minute,
                                  seconds=sRise.second)

    def getSunsetDelta(self):
        sSet = self.getSunsetTime()
        return datetime.timedelta(hours=sSet.hour,
                                  minutes=sSet.minute,
                                  seconds=sSet.second)

    def itsDaytime(self):
        srDelta = self.getSunriseDelta()
        ssDelta = self.getSunsetDelta()
        nowDelta = self.getTimeNowDeltaWithCorrection()

        return (nowDelta >= srDelta) and (nowDelta < ssDelta)

    def itsNighttime(self):
        # Implicitly not daytime
        return not self.itsDaytime()

    def getTimeToNextHorizonCrossing(self):
        nowDelta = self.getTimeNowDeltaWithCorrection()
        ssDelta = self.getSunsetDelta()
        if self.itsDaytime():
            # Daytime, get the remaining fraction of the day until sunset
            diffTime = ssDelta - nowDelta
        else:
            # Nighttime, get the remaining fraction of the day until sunrise
            srDelta = self.getSunriseDelta()
            if nowDelta > ssDelta:
                # After sunset but before midnight we need to combine today and
                # tomorrow, plus a second because the day ends at 23:59:59
                endOfDay = datetime.timedelta(hours=23, minutes=59, seconds=59)
                diffTime = endOfDay - nowDelta + 1
                diffTime += srDelta
            else:
                # After midnight
                diffTime = srDelta - nowDelta

        return diffTime

    # Set a supplied time or the current time in the control
    def showTime(self, newTime):
        labTimeNow = self.findChild(QLabel, "timeNow")
        if labTimeNow is not None:
            if newTime is None:
                TimeNow = self.getTimeNowWithCorrection()
            else:
                TimeNow = newTime
            labTimeNow.setText("{}".format(TimeNow))

    def showSunriseTime(self):
        sRise = self.getSunriseTime()
        labSunrise = self.findChild(QLabel, "sunrise")
        if labSunrise is not None:
            labSunrise.setText("{}".format(sRise))

    def showSunsetTime(self):
        sSet = self.getSunsetTime()
        labSunset = self.findChild(QLabel, "sunset")
        if labSunset is not None:
            labSunset.setText("{}".format(sSet))

    def tick(self):
        # Set the current time in the math library
        setSystemTime()

        # In the main window, show the current, sunrise and sunset times
        self.showTime(None)
        self.showSunriseTime()
        self.showSunsetTime()

        # How long to the next solar horizon crossing
        diffTime = self.getTimeToNextHorizonCrossing()
        if self.itsDaytime():
            nextCrossing = "sunset"
        else:
            nextCrossing = "sunrise"

        # Display it with a relevant prompt
        labrTimePrompt = self.findChild(QLabel, "rTimePrompt")
        labrTimeValue = self.findChild(QLabel, "rTimeValue")
        if (labrTimePrompt is not None) and (labrTimeValue is not None):
            labrTimePrompt.setText("Remaining time until {}:".format(nextCrossing))
            labrTimeValue.setText("{}".format(diffTime))

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

            ctrlCorrectTZ.setChecked(self.CorrectForSysTZ)

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
                    self.CorrectForSysTZ = ctrlCorrectTZ.isChecked()
                    break

                # Retry, loop and re-show the dialog box for user correction

            # Display any new location
            self.showLocation()
        else:
            debugMessage("location controls NOT found")

    def getConfigFileDir(self):
        # Get the home directory path
        homePath = QDir.homePath()
        if homePath is not None:
            if homePath[-1] != '/':
                homePath += '/'

        debugMessage("HOMEDIR: {}".format(homePath))
        return homePath

    def getConfigFilename(self):
        cfgFilename = self.getConfigFileDir()
        if cfgFilename is not None:
            cfgFilename += '.QtSunsetter'
        else:
            cfgFilename = None

        debugMessage("CONFIG FILE: {}".format(cfgFilename))
        return cfgFilename

    def getConfigTempFilename(self):
        tmpFilename = self.getConfigFileDir()
        if tmpFilename is not None:
            tmpFilename += '.QtSunsetter.tmp'
        else:
            tmpFilename = None

        debugMessage("TEMP FILE: {}".format(tmpFilename))
        return tmpFilename

    def processConfigLine(self, theLine):
        # Comments begin with a # character, remove them
        m = re.search('^(.+)\\#.+$', theLine)
        if m is not None:
            theLine = m.group(1)

        # If there is nothing left we are finished with the line
        if (theLine == "") or (theLine is None):
            return

        # If we have a latitude (signed decimal)
        m = re.search('^latitude=(\\-{0,1}\\d+\\.{0,1}\\d*)$',
                      theLine,
                      flags=re.IGNORECASE)
        if m is not None:
            lat = m.group(1)
            try:
                nLat = float(lat)
            except Exception:
                nLat = 0.0
            setLatitude(nLat)
            debugMessage("lat = {} => {}".format(lat, nLat))
            return

        # If we have a longitude (signed decimal)
        m = re.search('^longitude=(\\-{0,1}\\d+\\.{0,1}\\d*)$',
                      theLine,
                      flags=re.IGNORECASE)
        if m is not None:
            lon = m.group(1)
            try:
                nLon = float(lon)
            except Exception:
                nLon = 0.0
            setLongitude(nLon)
            debugMessage("lon = {} => {}".format(lon, nLon))
            return

        # If we have a timezone (signed decimal clock offset in hours)
        m = re.search('^timezone=(\\-{0,1}\\d+\\.{0,1}\\d*)$',
                      theLine,
                      flags=re.IGNORECASE)
        if m is not None:
            tz = m.group(1)
            try:
                nTZ = float(tz)
            except Exception:
                nTZ = 0.0
            setHomeTZ(nTZ * 3600.0)
            debugMessage("TZ = {} => {}".format(tz, nTZ))
            return

        # If we are to correct system time from system timezone to
        # configured timezone
        m = re.search('^CorrectForSystemTimezone$',
                      theLine,
                      flags=re.IGNORECASE)
        if m is not None:
            self.CorrectForSysTZ = True
            debugMessage("CorrectForSystemTimezone ENABLED")
            return

        # print("{}".format(theLine))

    def loadConfig(self):
        cfgFilename = self.getConfigFilename()
        cfgFile = QFile(cfgFilename)
        if cfgFile is not None:
            if cfgFile.exists():
                debugMessage("Config file found")

                if cfgFile.open(QIODevice.ReadOnly | QIODevice.Text):
                    inStream = QTextStream(cfgFile)
                    if inStream is not None:
                        # Assume correct for system timezone is OFF
                        self.CorrectForSysTZ = False
                        while not inStream.atEnd():
                            inStream.skipWhiteSpace()
                            line = inStream.readLine()
                            self.processConfigLine(line)
            else:
                debugMessage("Config file NOT found")
                self.CorrectForSysTZ = False

    def saveConfigLine(self, outStream, outLine, theGap, theComment):
        if (outStream is None) or (outLine is None):
            return

        # If there was a comment
        if theComment is not None:
            if theComment != "":
                # Append any gap spaces
                if theGap is not None:
                    if theGap != "":
                        outLine += theGap

                # Append the comment
                outLine += theComment

        # Save the line
        outLine += "\n"
        outStream << outLine

    def processOutputConfigLine(self, outStream, theLine):
        if (outStream is None) or (theLine is None):
            return

        outLine = theLine

        # Comments begin with a # character, split them into
        # setting, gap to comment and comment
        m = re.search('^(.+)(\\s*)(\\#.*)$', theLine)
        if m is not None:
            theLine = m.group(1)
            theGap = m.group(2)
            theComment = m.group(3)
        else:
            theGap = None
            theComment = None

        # If we have a latitude (signed decimal)
        m = re.search('^latitude=(\\-{0,1}\\d+\\.{0,1}\\d*)$',
                      theLine,
                      flags=re.IGNORECASE)
        if m is not None:
            # If we haven't already saved it
            if not self.savedLat:
                # Re-build using the current latitude
                outLine = "latitude={}".format(getLatitude())
                self.savedLat = True
            else:
                # Saved it already, make the line a comment
                outLine = "#" + outLine
                theGap = None
                theComment = None

        # If we have a longitude (signed decimal)
        m = re.search('^longitude=(\\-{0,1}\\d+\\.{0,1}\\d*)$',
                      theLine,
                      flags=re.IGNORECASE)
        if m is not None:
            # If we haven't already saved it
            if not self.savedLon:
                # Re-build using the current longitude
                outLine = "longitude={}".format(getLongitude())
                self.savedLon = True
            else:
                # Saved it already, make the line a comment
                outLine = "#" + outLine
                theGap = None
                theComment = None

        # If we have a timezone (signed decimal clock offset in hours)
        m = re.search('^timezone=(\\-{0,1}\\d+\\.{0,1}\\d*)$',
                      theLine,
                      flags=re.IGNORECASE)
        if m is not None:
            # If we haven't already saved it
            if not self.savedTZ:
                # Re-build using the current timezone
                outLine = "timezone={}".format(getHomeTZ())
                self.savedTZ = True
            else:
                # Saved it already, make the line a comment
                outLine = "#" + outLine
                theGap = None
                theComment = None

        # If we are to correct system time based on system timezone and
        # configured timezone (present is ON, not-present is OFF)
        m = re.search('^CorrectForSystemTimezone$',
                      theLine,
                      flags=re.IGNORECASE)
        if m is not None:
            if self.CorrectForSysTZ is False:
                debugMessage("CorrectForSystemTimezone DISABLED")
                # If there's no gap and no comment then don't write an empty
                # line as a replacement
                if ((theGap is None) or (theGap == "")) and\
                        ((theComment is None) or (theComment == "")):
                    outLine = None
                else:
                    outLine = ""

            self.savedCorrectForSysTZ = True

        self.saveConfigLine(outStream, outLine, theGap, theComment)

    # Save the config but only replace supported configuration items while
    # keeping all other content
    def saveConfig(self):
        # We haven't yet saved each property
        self.savedLat = False
        self.savedLon = False
        self.savedTZ = False
        self.savedCorrectForSysTZ = False

        # Get the config and temp filenames
        cfgFilename = self.getConfigFilename()
        tmpFilename = self.getConfigTempFilename()

        # Use any original config file and a temp file to write
        cfgFile = QFile(cfgFilename)
        tmpFile = QFile(tmpFilename)
        if (cfgFile is not None) and (tmpFile is not None):
            inStream = None
            if cfgFile.exists():
                debugMessage("Config file found")

                if cfgFile.open(QIODevice.ReadOnly | QIODevice.Text):
                    inStream = QTextStream(cfgFile)

            # Open the output
            if tmpFile.open(QFile.WriteOnly | QFile.Truncate | QIODevice.Text):
                outStream = QTextStream(tmpFile)
            else:
                outStream = None

            if outStream is not None:
                # If we have an input file, read through it re-writing it to
                # the temp file and change any known settings to current values
                if inStream is not None:
                    while not inStream.atEnd():
                        line = inStream.readLine()
                        self.processOutputConfigLine(outStream, line)

                    # Remove the original config file
                    cfgFile.remove()
                    cfgFile = None

                # Fixup anything we didn't save in the temp file
                if not self.savedLat:
                    self.processOutputConfigLine(outStream, "latitude=0")
                if not self.savedLon:
                    self.processOutputConfigLine(outStream, "longitude=0")
                if not self.savedTZ:
                    self.processOutputConfigLine(outStream, "timezone=0")
                if (not self.savedCorrectForSysTZ) and\
                        (self.CorrectForSysTZ is True):
                    self.processOutputConfigLine(outStream,
                                                 "CorrectForSystemTimezone")

                # Rename the temp file as the config file
                tmpFile.rename(cfgFilename)


disableDebug()

if __name__ == "__main__":
    app = QApplication([])
    widget = QtSunsetter()
    widget.position_ui()
    widget.show()
    sys.exit(app.exec_())
