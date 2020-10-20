# This Python file uses the following encoding: utf-8
#
# Command-line interface to the QtSsMath.py code
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
# Code for a console implementation of what QtSunsetter.py does
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
import subprocess
import time
import datetime

from QtSsDebug import debugMessage, disableDebug, enableDebug, debugIsEnabled
from QtSsMath import setLatitude, setLongitude
from QtSsMath import setHomeTZ
from QtSsMath import LocalSunrise, LocalSunset, timeFromDayFraction
from QtSsMath import SsMathTest, testFunction


def sunriseReached():
    if enableRun is True:
        # Just made the crossing to day, do our work
        sunriseReached()
        sproc = subprocess.Popen(['/root/bin/morning.sh'],
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


def sunsetReached():
    if enableRun is True:
        # Just made the crossing to night, do our work
        sproc = subprocess.Popen(['/root/bin/evening.sh'],
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


def doWait(remainingSeconds):
    interval = datetime.timedelta(hours=0,
                                  minutes=0,
                                  seconds=0)
    if remainingSeconds > 60:
        time.sleep(60)
        if SsMathTest() is True:
            interval = datetime.timedelta(hours=0,
                                          minutes=0,
                                          seconds=60)
    else:
        if SsMathTest() is True:
            interval = datetime.timedelta(hours=0,
                                          minutes=0,
                                          seconds=remainingSeconds)
            interval += datetime.timedelta(hours=0,
                                           minutes=0,
                                           seconds=1)

        time.sleep(remainingSeconds + 1)

        return interval


# No argument support, use globals to set state

# disableDebug()
enableDebug()

# Location, latitude/longitude
useLat = 29.866634
useLong = -101.866673
# useLat = 55.8
# useLong = -4.5
setLatitude(useLat)
setLongitude(useLong)
# debugMessage("Using location {}, {}".format(useLat, useLong))

# Current time and system timezone information
today = datetime.date.today()
systemTime = time.localtime()
if SsMathTest() is False:
    timeNow = datetime.time(systemTime[3], systemTime[4], systemTime[5])
else:
    # Fake a start time to test
    timeNow = datetime.time(23, 59, 20)
useTZs = 1.0 * systemTime.tm_gmtoff
useTZ = useTZs / 3600.0
setHomeTZ(useTZs)
# debugMessage("Using timezone offset {} hours".format(useTZ))

# enable exec on solar horizon crossings
enableRun = False

if __name__ == '__main__':
    aTime = datetime.time(0, 6, 0)
    testFunction(aTime)

    # Which boundary we cross next
    nextCrossing = None

    # Just keep going until stopped
    while True:
        print("")

        today = datetime.date.today()
        systemTime = time.localtime()
        # print("Now: {}:{}:{}".format(systemTime[3], systemTime[4], systemTime[5]))

        if SsMathTest() is False:
            timeNow = datetime.time(systemTime[3],
                                    systemTime[4],
                                    systemTime[5])

        # If the time-zone time offset changed, use it
        if systemTime.tm_gmtoff != int(useTZ * 3600):
            useTZ = 1.0 * systemTime.tm_gmtoff
            useTZ /= 3600.0
            setHomeTZ(useTZ)

        # print("Time: {}".format(timeNow))

        x = LocalSunrise(today, aTime)
        sRise = timeFromDayFraction(x)
        debugMessage("Sun rises at: {} ({})".format(sRise, x))
        # print("Sun rises at: {}".format(sRise))

        x = LocalSunset(today, aTime)
        sSet = timeFromDayFraction(x)
        # print(" Sun sets at: {} ({})".format(sSet, x))
        # print(" Sun sets at: {}".format(sSet))

        print("Time: {}; Sunrise: {}; Sunset: {}".format(timeNow, sRise, sSet))

        nowDelta = datetime.timedelta(hours=timeNow.hour,
                                      minutes=timeNow.minute,
                                      seconds=timeNow.second)

        srDelta = datetime.timedelta(hours=sRise.hour,
                                     minutes=sRise.minute,
                                     seconds=sRise.second)
        ssDelta = datetime.timedelta(hours=sSet.hour,
                                     minutes=sSet.minute,
                                     seconds=sSet.second)
        endOfDay = datetime.timedelta(hours=23, minutes=59, seconds=59)

        # Are we in in day or night (day is after sunrise and before sunset
        if (nowDelta > srDelta) and (nowDelta < ssDelta):
            if nextCrossing is None:
                # We are pending sunset
                nextCrossing = "sunset"
            elif nextCrossing == "sunrise":
                sunriseReached()

                # Now we are pending sunset
                nextCrossing = "sunset"

            # Daytime, get the remaining time to sunset
            diffTime = ssDelta - nowDelta
            print("Remaining time until sunset: {}".format(diffTime))
        else:
            if nextCrossing is None:
                # We are pending sunrise
                nextCrossing = "sunrise"
            elif nextCrossing == "sunset":
                sunsetReached()

                # Now we are pending sunrise
                nextCrossing = "sunrise"

            # Nighttime get the remaining time until sunrise
            if nowDelta > ssDelta:
                # After sunset but before midnight we need to combine today and
                # tomorrow
                diffTime = endOfDay - nowDelta
                diffTime += srDelta
            else:
                # After midnight
                diffTime = srDelta - nowDelta
            print("Remaining time until sunrise: {}".format(diffTime))

        # difftime has the remaining time until our next boundary crossing
        # Don't sleep for it all, to allow events to be handled
        interval = doWait(diffTime.total_seconds())

        if SsMathTest() is True:
            nextTime = datetime.timedelta(hours=timeNow.hour,
                                          minutes=timeNow.minute,
                                          seconds=timeNow.second)
            nextTime += interval
            aDay = datetime.timedelta(days=1)
            while nextTime >= aDay:
                nextTime -= aDay
            nextHour = int(nextTime.total_seconds() / 3600)
            hourSec = nextHour * 3600
            nextMinute = int((nextTime.total_seconds() - (hourSec)) / 60)
            nextSecond = int((nextTime.total_seconds() - (hourSec))) % 60
            print("NEXT: {} - {}:{}:{}".format(nextTime,
                                               nextHour,
                                               nextMinute,
                                               nextSecond))
            timeNow = datetime.time(nextHour, nextMinute, nextSecond)

    sys.exit(0)
