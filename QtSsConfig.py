# This Python file uses the following encoding: utf-8
#
# Configuration file handler for QtSunsetter
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

import re

from PySide2.QtCore import QDir, QFile, QIODevice, QTextStream, QFileInfo
from QtSsDebug import warningMessage, debugMessage


class SunsetterConfig:
    def __init__(self, cfgFileName=None):
        # A name for this object in warning messages
        self.configSrcFrom = "Config"

        # If no config filename was supplied generate one
        if cfgFileName is None:
            self.fileName = self.getConfigFilename()
        else:
            self.fileName = cfgFileName

        self.latitude = None
        self.longitude = None
        self.homeTZ = None
        self.correctForSysTZ = None
        self.sunriseRun = None
        self.sunsetRun = None

    def getLatitude(self):
        return self.latitude

    def getLongitude(self):
        return self.longitude

    def getHomeTZ(self):
        return self.homeTZ

    def getHomeTZSeconds(self):
        return (3600.0 * self.homeTZ)

    def getCorrectForSysTZ(self):
        return self.correctForSysTZ

    def getSolarCrossingRun(self, crossing):
        global QTS_SUNRISE, QTS_SUNSET

        if crossing == QTS_SUNRISE:
            return self.sunriseRun
        elif crossing == QTS_SUNSET:
            return self.sunsetRun
        else:
            warningMessage("Attempt to get run program for "
                           "unrecognized solar horizon"
                           "crossing: {}".format(crossing),
                           self.configSrcFrom)

        return None

    # Return True if fileName argument is an existing, executable file
    # else return False
    def isRunnableFile(self, fileName):
        result = False
        if (fileName is not None) and (fileName != ""):
            fInfo = QFileInfo(fileName)
            if (fInfo.exists()) and (fInfo.isExecutable()):
                result = True
        return result

    def setLatitude(self, newLat):
        if (newLat >= -90.0) and (newLat <= 90.0):
            self.latitude = newLat
        else:
            warningMessage("Attempt to set invalid"
                           "latitude: {}".format(newLat),
                           self.configSrcFrom)

    def setLongitude(self, newLon):
        if (newLon >= -180.0) and (newLon <= 180.0):
            self.longitude = newLon
        else:
            warningMessage("Attempt to set invalid"
                           "longitude: {}".format(newLon),
                           self.configSrcFrom)

    def setHomeTZ(self, newTZ):
        if (newTZ >= -12.0) and (newTZ <= 12):
            self.homeTZ = newTZ
        else:
            warningMessage("Attempt to set invalid"
                           "timezone: {}".format(newTZ),
                           self.configSrcFrom)

    def setCorrectForSysTZ(self, newVal):
        if (newVal is True) or (newVal is False):
            self.correctForSysTZ = newVal
        else:
            warningMessage("Attempt to set invalid"
                           "correct for system timezone: {}".format(newVal),
                           self.configSrcFrom)

    def setSolarCrossingRun(self, newFileName, crossing):
        global QTS_SUNRISE, QTS_SUNSET

        if self.isRunnableFile(newFileName):
            if crossing == QTS_SUNRISE:
                self.sunriseRun = newFileName
            elif crossing == QTS_SUNSET:
                self.sunsetRun = newFileName
            else:
                warningMessage("Attempt to set run program "
                               "for unrecognized solar horizon "
                               "crossing: {}".format(crossing),
                               self.configSrcFrom)
        else:
            if crossing == QTS_SUNRISE:
                eventName = "sunrise"
            elif crossing == QTS_SUNSET:
                eventName = "sunset"
            else:
                eventName = "unrecognized"

            warningMessage("Attempt to set missing or non "
                           "executable file as {} run "
                           "program {}".format(eventName, newFileName),
                           self.configSrcFrom)

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

    def latlonConfig(self, cfgLine):
        nVal = None
        m = re.search('^latitude=(\\-{0,1}\\d+\\.{0,1}\\d*)$',
                      cfgLine,
                      flags=re.IGNORECASE)
        if m is None:
            m = re.search('^longitude=(\\-{0,1}\\d+\\.{0,1}\\d*)$',
                          cfgLine,
                          flags=re.IGNORECASE)
            isLat = False
        else:
            isLat = True

        if m is not None:
            val = m.group(1)
            try:
                nVal = float(val)
            except Exception:
                nVal = 0.0

            if isLat is True:
                self.setLatitude(nVal)
                debugMessage("lat = {} => {}".format(val, nVal))
            else:
                self.setLongitude(nVal)
                debugMessage("lon = {} => {}".format(val, nVal))

        return (nVal is not None)

    def timezoneConfig(self, cfgLine):
        nTZ = None
        m = re.search('^timezone=(\\-{0,1}\\d+\\.{0,1}\\d*)$',
                      cfgLine,
                      flags=re.IGNORECASE)
        if m is not None:
            tz = m.group(1)
            try:
                nTZ = float(tz)
            except Exception:
                nTZ = 0.0
            self.setHomeTZ(nTZ)
            debugMessage("TZ = {} => {}".format(tz, nTZ))

        return (nTZ is not None)

    def correctTimezoneConfig(self, cfgLine):
        result = False
        m = re.search('^CorrectForSystemTimezone$',
                      cfgLine,
                      flags=re.IGNORECASE)
        if m is not None:
            self.setCorrectForSysTZ(True)
            result = True
            debugMessage("CorrectForSystemTimezone ENABLED")

        return result

    def solarCrossingRunConfig(self, cfgLine):
        global QTS_SUNRISE, QTS_SUNSET

        result = False

        # Apply the sunrise regexp
        m = re.search('^sunriserun=(.*)$', cfgLine, flags=re.IGNORECASE)
        if m is None:
            # No match, apply the sunset regexp
            m = re.search('^sunsetrun=(.*)$', cfgLine, flags=re.IGNORECASE)
            if m is not None:
                crossing = QTS_SUNSET
        else:
            # Sunrise regexp matched
            crossing = QTS_SUNRISE

        # If we matched either regexp
        if m is not None:
            fileName = m.group(1)
            if self.isRunnableFile(fileName):
                self.setSolarCrossingRun(fileName, crossing)
                result = True

        return result

    def processConfigLine(self, theLine):
        # Comments begin with a # character, remove them
        m = re.search('^(.*)\\s*\\#.*$', theLine)
        if m is not None:
            theLine = m.group(1)

        # If there is nothing left we are finished with the line
        if (theLine == "") or (theLine is None):
            return

        # If we have a latitude or longitude (signed decimal)
        if self.latlonConfig(theLine) is True:
            return

        # If we have a timezone (signed decimal clock offset in hours)
        if self.timezoneConfig(theLine) is True:
            return

        # If we are to correct system time from system timezone to
        # configured timezone
        if self.correctTimezoneConfig(theLine) is True:
            return

        # If we have a program to run on sunrise or sunset
        if self.solarCrossingRunConfig(theLine) is True:
            return

        warningMessage("Unprocessed config file line: {}".format(theLine),
                       self.configSrcFrom)

    def loadConfig(self):
        self.initRiseRun = None
        self.initSetRun = None
        cfgFile = QFile(self.fileName)
        if cfgFile is not None:
            if cfgFile.exists():
                debugMessage("Config file found")

                if cfgFile.open(QIODevice.ReadOnly | QIODevice.Text):
                    inStream = QTextStream(cfgFile)
                    if inStream is not None:
                        # Assume correct for system timezone is OFF
                        self.setCorrectForSysTZ(False)
                        while not inStream.atEnd():
                            inStream.skipWhiteSpace()
                            line = inStream.readLine()
                            self.processConfigLine(line)
            else:
                debugMessage("Config file NOT found")
                self.setCorrectForSysTZ(False)

        result = (self.latitude is not None)\
            and (self.longitude is not None)\
            and (self.homeTZ is not None)
        return result

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

    def latLonProcessOutput(self, cfgLine):
        outLine = None

        # Match the latitude regexp with the line
        m = re.search('^latitude=(\\-{0,1}\\d+\\.{0,1}\\d*)$',
                      cfgLine,
                      flags=re.IGNORECASE)
        if m is None:
            # Failed, match the longitude regexp with the line
            m = re.search('^longitude=(\\-{0,1}\\d+\\.{0,1}\\d*)$',
                          cfgLine,
                          flags=re.IGNORECASE)
            if m is not None:
                # Matched longitude
                isLat = False
                coordName = "longitude"
                posn = self.getLongitude()
                saved = self.savedLon
        else:
            # Matched latitude
            isLat = True
            coordName = "latitude"
            posn = self.getLatitude()
            saved = self.savedLat

        # If we have a latitude or longitude line
        if m is not None:
            # If it's not already saved
            if saved is False:
                # Re-build with the current position
                outLine = "{}={}".format(coordName, posn)
                if isLat:
                    self.savedLat = True
                else:
                    self.savedLon = True
            else:
                # Saved it already, make the line a comment
                outLine = "#"

        return outLine

    def timezoneProcessOutput(self, cfgLine):
        outLine = None
        m = re.search('^timezone=(\\-{0,1}\\d+\\.{0,1}\\d*)$',
                      cfgLine,
                      flags=re.IGNORECASE)
        if m is not None:
            # If we haven't already saved it
            if not self.savedTZ:
                # Re-build using the current timezone
                outLine = "timezone={}".format(self.getHomeTZ())
                self.savedTZ = True
            else:
                # Saved it already
                outLine = "#"

        return outLine

    def solarCrossingRunProcessOutput(self, cfgLine):
        global QTS_SUNRISE, QTS_SUNSET

        outLine = None

        # Try the sunrise regexp against the line
        m = re.search('^sunriserun=(.*)$',
                      cfgLine,
                      flags=re.IGNORECASE)
        if m is None:
            # Sunrise failed, try the sunset regexp against the line
            m = re.search('^sunsetrun=(.+)$',
                          cfgLine,
                          flags=re.IGNORECASE)
            if m is not None:
                # Sunset matched
                saved = self.savedSetRun
                cfgName = "sunsetrun"
                crossing = QTS_SUNSET
        else:
            # Sunrise matched
            saved = self.savedRiseRun
            cfgName = "sunriserun"
            crossing = QTS_SUNRISE

        # If either regexp matched
        if m is not None:
            # ...and we haven't already saved the option
            if saved is False:
                # Re-build using the current value
                runName = self.getSolarCrossingRun(crossing)
                outLine = "{}={}".format(cfgName, runName)

                if crossing == QTS_SUNRISE:
                    self.savedRiseRun = True
                elif crossing == QTS_SUNSET:
                    self.savedSetRun = True
            else:
                # Saved it already
                outLine = "#"

        return outLine

    def processOutputConfigLine(self, outStream, theLine):
        global QTS_SUNRISE, QTS_SUNSET

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

        # If we are to correct system time based on system timezone and
        # configured timezone (present is ON, not-present is OFF)
        m = re.search('^CorrectForSystemTimezone$',
                      theLine,
                      flags=re.IGNORECASE)
        if m is not None:
            if self.getCorrectForSysTZ() is False:
                debugMessage("CorrectForSystemTimezone DISABLED")
                # If there's no gap and no comment then don't write an empty
                # line as a replacement
                if ((theGap is None) or (theGap == "")) and\
                        ((theComment is None) or (theComment == "")):
                    outLine = None
                else:
                    outLine = ""

            self.savedCorrectForSysTZ = True
        else:
            # If we have a latitude or longitude (signed decimal)
            tmpLine = self.latLonProcessOutput(theLine)
            if tmpLine is None:
                # If we have a timezone (signed decimal clock offset in hours)
                tmpLine = self.timezoneProcessOutput(theLine)
                if tmpLine is None:
                    # If we have a program to run at sunrise or sunset (string)
                    tmpLine = self.solarCrossingRunProcessOutput(theLine)

            # If we get here with tmpLine not None we can treat it generically
            # for all cases
            if tmpLine is not None:
                # not saved already, tmpLine is the output line
                if tmpLine != "#":
                    outLine = tmpLine
                else:
                    # Saved it already, make the line a comment
                    outLine = "# " + outLine
                    theGap = None
                    theComment = None

        self.saveConfigLine(outStream, outLine, theGap, theComment)

    # Save the config but only replace supported configuration items while
    # keeping all other content
    def saveConfig(self):
        # We haven't yet saved each property
        self.savedLat = False
        self.savedLon = False
        self.savedTZ = False
        self.savedCorrectForSysTZ = False
        self.savedRiseRun = False
        self.savedSetRun = False

        # Get the config and temp filenames
        cfgFilename = self.getConfigFilename()
        tmpFilename = self.getConfigTempFilename()

        # Use any original config file to read and a temp file to write
        cfgFile = QFile(cfgFilename)
        tmpFile = QFile(tmpFilename)
        if (cfgFile is not None) and (tmpFile is not None):
            # Open the input
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
                else:
                    warningMessage("Unable to open file to save "
                                   "configuration: {}".format(tmpFilename),
                                   self.configSrcFrom)

                # Fixup anything we didn't save in the temp file
                if not self.savedLat:
                    self.processOutputConfigLine(outStream, "latitude=0")
                if not self.savedLon:
                    self.processOutputConfigLine(outStream, "longitude=0")
                if not self.savedTZ:
                    self.processOutputConfigLine(outStream, "timezone=0")
                if (not self.savedCorrectForSysTZ) and\
                        (self.getCorrectForSysTZ() is True):
                    self.processOutputConfigLine(outStream,
                                                 "CorrectForSystemTimezone")
                if not self.savedRiseRun:
                    self.processOutputConfigLine(outStream, "sunriserun=abc")
                if not self.savedSetRun:
                    self.processOutputConfigLine(outStream, "sunsetrun=abc")

                # Rename the temp file as the config file
                tmpFile.rename(cfgFilename)
            else:
                warningMessage("Unable to open previous file to save "
                               "configuration: {}".format(cfgFilename),
                               self.configSrcFrom)


# These "constants" are used to allow shared implementation details for some
# functionality applying to both sunrise and sunset in a similar way
QTS_SUNRISE = 1
QTS_SUNSET = 2

# if __name__ == "__main__":
#     pass
