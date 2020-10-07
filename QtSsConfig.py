# This Python file uses the following encoding: utf-8

import re

from PySide2.QtCore import QDir, QFile, QIODevice, QTextStream, QFileInfo
from QtSsDebug import debugMessage


class SunsetterConfig:
    def __init__(self, cfgFileName=None):
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

    def getSunriseRun(self):
        return self.sunriseRun

    def getSunsetRun(self):
        return self.sunsetRun

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

    def setLongitude(self, newLon):
        if (newLon >= -180.0) and (newLon <= 180.0):
            self.longitude = newLon

    def setHomeTZ(self, newTZ):
        if (newTZ >= -12.0) and (newTZ <= 12):
            self.homeTZ = newTZ

    def setCorrectForSysTZ(self, newVal):
        if (newVal is True) or (newVal is False):
            self.correctForSysTZ = newVal

    def setSunriseRun(self, newFileName):
        if self.isRunnableFile(newFileName):
            self.sunriseRun = newFileName

    def setSunsetRun(self, newFileName):
        if self.isRunnableFile(newFileName):
            self.sunsetRun = newFileName

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
        isLat = True
        nVal = None
        m = re.search('^latitude=(\\-{0,1}\\d+\\.{0,1}\\d*)$',
                      cfgLine,
                      flags=re.IGNORECASE)
        if m is None:
            isLat = False
            m = re.search('^longitude=(\\-{0,1}\\d+\\.{0,1}\\d*)$',
                          cfgLine,
                          flags=re.IGNORECASE)
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

    def sunriseRunConfig(self, cfgLine):
        result = False
        m = re.search('^sunriserun=(.*)$',
                      cfgLine,
                      flags=re.IGNORECASE)
        if m is not None:
            fileName = m.group(1)
            if self.isRunnableFile(fileName):
                self.setSunriseRun(fileName)
                result = True
            debugMessage("sunrise program = {}".format(fileName))

        return result

    def sunsetRunConfig(self, cfgLine):
        result = False
        m = re.search('^sunsetrun=(.*)$',
                      cfgLine,
                      flags=re.IGNORECASE)
        if m is not None:
            fileName = m.group(1)
            if self.isRunnableFile(fileName):
                self.setSunsetRun(fileName)
                result = True
            debugMessage("sunset program = {}".format(fileName))

        return result

    def processConfigLine(self, theLine):
        # Comments begin with a # character, remove them
        m = re.search('^(.+)\\#.+$', theLine)
        if m is not None:
            theLine = m.group(1)

        # If there is nothing left we are finished with the line
        if (theLine == "") or (theLine is None):
            return

        # If we have a latitude (signed decimal)
        if self.latlonConfig(theLine) is True:
            return

        # If we have a longitude (signed decimal)
        if self.latlonConfig(theLine) is True:
            return

        # If we have a timezone (signed decimal clock offset in hours)
        if self.timezoneConfig(theLine) is True:
            return

        # If we are to correct system time from system timezone to
        # configured timezone
        if self.correctTimezoneConfig(theLine) is True:
            return

        # If we have a program to run on sunrise
        if self.sunriseRunConfig(theLine) is True:
            return

        # If we have a program to run on sunset
        if self.sunsetRunConfig(theLine) is True:
            return

        debugMessage("Unprocessed config line: {}".format(theLine))

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
        isLat = True
        m = re.search('^latitude=(\\-{0,1}\\d+\\.{0,1}\\d*)$',
                      cfgLine,
                      flags=re.IGNORECASE)
        if m is None:
            isLat = False
            m = re.search('^longitude=(\\-{0,1}\\d+\\.{0,1}\\d*)$',
                          cfgLine,
                          flags=re.IGNORECASE)
        if m is not None:
            if isLat:
                # If we haven't already saved latitude
                if not self.savedLat:
                    # Re-build using the current latitude
                    outLine = "latitude={}".format(self.getLatitude())
                    self.savedLat = True
                else:
                    # Saved it already, make the line a comment
                    outLine = "# "
            else:
                # If we haven't already saved longitude
                if not self.savedLon:
                    # Re-build using the current longitude
                    outLine = "longitude={}".format(self.getLongitude())
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

    def riseRunProcessOutput(self, cfgLine):
        outLine = None
        m = re.search('^sunriserun=(.*)$',
                      cfgLine,
                      flags=re.IGNORECASE)
        if m is not None:
            # If we haven't already saved it
            if not self.savedRiseRun:
                # Re-build using the current value
                outLine = "sunriserun={}".format(self.getSunriseRun())
                self.savedRiseRun = True
            else:
                # Saved it already
                outLine = "#"

        return outLine

    def setRunProcessOutput(self, cfgLine):
        outLine = None
        m = re.search('^sunsetrun=(.+)$',
                      cfgLine,
                      flags=re.IGNORECASE)
        if m is not None:
            # If we haven't already saved it
            if not self.savedSetRun:
                # Re-build using the current value
                outLine = "sunsetrun={}".format(self.getSunsetRun())
                self.savedSetRun = True
            else:
                # Saved it already
                outLine = "#"

        return outLine

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
                tmpLine = self.timezoneProcessOutputLine(theLine)
                if tmpLine is None:
                    # If we have a program to run at sunrise (string)
                    tmpLine = self.riseRunProcessOutputLine(theLine)
                    if tmpLine is None:
                        # If we have a program to run at sunset (string)
                        tmpLine = self.setRunProcessOutputLine(theLine)

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
                        (self.getCorrectForSysTZ() is True):
                    self.processOutputConfigLine(outStream,
                                                 "CorrectForSystemTimezone")
                if not self.savedRiseRun:
                    self.processOutputConfigLine(outStream, "sunriserun=abc")
                if not self.savedSetRun:
                    self.processOutputConfigLine(outStream, "sunsetrun=abc")

                # Rename the temp file as the config file
                tmpFile.rename(cfgFilename)


# if __name__ == "__main__":
#     pass
