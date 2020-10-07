# This Python file uses the following encoding: utf-8
#
# This file contains some generic functions to perform math based on time of
# day with awareness of day/night times and the elapsed light period
# (day/night) with the ability to operate in h:m:s based absolute times,
# h:m:s relative times, time differences and fractions of the day. Note
# Fractions of day that are night are the fraction for the day in which the
# calculation is made, e.g. after sunset the nighttime after midnight is not
# added. It means that as midnight is reached the fraction will "shuffle" a
# little.
#
# Version: 1.0
# Copyright (C) 2020/10/05 David A. Mair
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

import time
import datetime

from QtSsMath import LocalSunrise, LocalSunset, getHomeTZ, timeFromDayFraction


# Get the current time
# Returns a daytime type (h:m:s)
def getTimeNow():
    systemTime = time.localtime()
    return datetime.time(systemTime[3], systemTime[4], systemTime[5])


# Get the current time and correct from system timezone to a saved timezone
# Returns a daytime type (h:m:s)
def getTimeNowWithCorrection():
    global CorrectForSysTZ

    timeNow = getTimeNow()
    correctHour = timeNow.hour
    if CorrectForSysTZ is True:
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


# Get the current time
# Returns a timedelta object
def getTimeNowDelta():
    TimeNow = getTimeNow()

    return datetime.timedelta(hours=TimeNow.hour,
                              minutes=TimeNow.minute,
                              seconds=TimeNow.second)


# Get the current time and correct from system timezone to a saved timezone
# Returns a timedelta object
def getTimeNowDeltaWithCorrection():
    TimeNow = getTimeNowWithCorrection()

    return datetime.timedelta(hours=TimeNow.hour,
                              minutes=TimeNow.minute,
                              seconds=TimeNow.second)


# Get the current time as a fraction of a 24 hour day
# Returns a float in the range zero to one inclusive
def getTimeNowFractionofDay():
    timeNow = getTimeNowWithCorrection()
    y = timeNow.hour * 3600.0
    y += timeNow.minute * 60.0
    y += timeNow.second
    return (y / 86400.0)


# Get today's sunrise time as a fraction of a 24 hour day
# Returns a float in the range zero to one inclusive
def getSunriseFractionOfDay():
    Today = datetime.date.today()
    aTime = datetime.time(0, 6, 0)

    return LocalSunrise(Today, aTime)


# Get today's sunrise time
# Returns a datetime object (h:m:s)
def getSunriseTime():
    x = getSunriseFractionOfDay()
    return timeFromDayFraction(x)


# Get today's sunrise time
# Returns a timedelta object
def getSunriseDelta():
    sRise = getSunriseTime()
    return datetime.timedelta(hours=sRise.hour,
                              minutes=sRise.minute,
                              seconds=sRise.second)


# Get tomorrow's sunrise time as a fraction of a 24 hour day
# Returns a float in the range zero to one inclusive
def getTomorrowSunriseFractionOfDay():
    Tomorrow = datetime.date.fromtimestamp(86400.0 + time.time())
    aTime = datetime.time(0, 6, 0)

    return LocalSunrise(Tomorrow, aTime)


# Get tomorrow's sunrise time
# Returns a datetime object (h:m:s)
def getTomorrowSunriseTime():
    x = getTomorrowSunriseFractionOfDay()
    return timeFromDayFraction(x)


# Get tomorrow's sunrise time
# Returns a timedelta object
def getTomorrowSunriseDelta():
    sRise = getTomorrowSunriseTime()
    return datetime.timedelta(hours=sRise.hour,
                              minutes=sRise.minute,
                              seconds=sRise.second)


# Get today's sunset time as a fraction of a 24 hour day
# Returns a float in the range zero to one inclusive
def getSunsetFractionOfDay():
    Today = datetime.date.today()
    aTime = datetime.time(0, 6, 0)

    return LocalSunset(Today, aTime)


# Get today's sunset time
# Returns a datetime object (h:m:s)
def getSunsetTime():
    x = getSunsetFractionOfDay()
    return timeFromDayFraction(x)


# Get today's sunset time
# Returns a timedelta object
def getSunsetDelta():
    sSet = getSunsetTime()
    return datetime.timedelta(hours=sSet.hour,
                              minutes=sSet.minute,
                              seconds=sSet.second)


# Returns true if the time now is in today's daytime
# Returns a bool
def itsDaytime():
    srDelta = getSunriseDelta()
    ssDelta = getSunsetDelta()
    nowDelta = getTimeNowDeltaWithCorrection()

    return (nowDelta >= srDelta) and (nowDelta < ssDelta)


# Returns true if the time now is in today's nighttime
# Returns a bool
def itsNighttime():
    # Implicitly not daytime
    return not itsDaytime()


# Return trus if it's after sunset but before midnight
# Returns a bool
def itsAfterSunsetToday():
    ssDelta = getSunsetFractionOfDay()
    nowDelta = getTimeNowFractionofDay()
    if nowDelta > ssDelta:
        return True

    return False


# Returns the fraction of the day that is daytime
# Returns a float with value greater than zero and less than one
def daytimeFractionOfDay():
    Today = datetime.date.today()
    aTime = datetime.time(0, 6, 0)

    r = LocalSunrise(Today, aTime)
    s = LocalSunset(Today, aTime)

    return (s - r)


# Returns the duration of the day (24 hours) that is daytime
# Returns a datetime object (h:m:s)
def daytimeDuration():
    return timeFromDayFraction(daytimeFractionOfDay())


# Get the fraction of the day that is nighttime
# Returns a fload with value greater than zero and less than one
def nighttimeFractionOfDay():
    return (1.0 - daytimeFractionOfDay())


# Returns the duration of the day (24 hours) that is nighttime
# Returns a datetime object (h:m:s)
def nighttimeDuration():
    return timeFromDayFraction(nighttimeFractionOfDay())


# Get the current time as a fraction of the light period it is within
# e.g. if it's daytime, what fraction of daytime has elapsed at current time
# Automatically chooses daytime or nighttime
# Returns a float in the range zero to one
def getTimeNowFractionOfLightPeriod():
    srDelta = getSunriseFractionOfDay()
    ssDelta = getSunsetFractionOfDay()
    nowDelta = getTimeNowFractionofDay()
    if itsDaytime():
        # Subtract sunrise from now, all as a fraction of ratio of daytime
        elapsedFraction = nowDelta - srDelta
        elapsedFraction /= daytimeFractionOfDay()
    else:
        # Night crosses midnight, take care
        if itsAfterSunsetToday():
            # Evening, subtract sunset
            elapsedFraction = nowDelta - ssDelta
        else:
            # Morning, Add whole evening to current part of morning
            elapsedFraction = 1.0 - ssDelta + nowDelta

        # As a fraction of nighttime
        elapsedFraction /= nighttimeFractionOfDay()

    # debugMessage("time now as a fraction of current light period: {}".format(elapsedFraction))

    return elapsedFraction


# Get the current time as an elapsed time into the light period it is within
# e.g. if it's daytime, how much of of daytime has elapsed at current time
# Automatically chooses daytime or nighttime
# Returns a datetime object (h:m:s)
def getTimeNowDurationOfLightPeriod():
    elapsedFraction = getTimeNowFractionOfLightPeriod()
    if itsDaytime():
        elapsedFraction *= daytimeFractionOfDay()
    else:
        elapsedFraction *= nighttimeFractionOfDay()

    return timeFromDayFraction(elapsedFraction)


# Get the remaining time until the next solar crossing of the horizon
# Returns a timedelta object
def getTimeToNextHorizonCrossing():
    nowDelta = getTimeNowDeltaWithCorrection()
    ssDelta = getSunsetDelta()
    if itsDaytime():
        # Daytime, get the remaining fraction of the day until sunset
        diffTime = ssDelta - nowDelta
    else:
        # Nighttime, get the remaining fraction of the day until next sunrise
        if itsAfterSunsetToday():
            # After sunset but before midnight we need to combine today and
            # tomorrow, plus a second because the day ends at 23:59:59
            srDelta = getTomorrowSunriseDelta()
            endOfDay = datetime.timedelta(hours=23, minutes=59, seconds=59)
            plusSecond = datetime.timedelta(hours=0, minutes=0, seconds=1)
            diffTime = endOfDay - nowDelta + plusSecond
            diffTime += srDelta
        else:
            # After midnight, use time until sunrise today
            srDelta = getSunriseDelta()
            diffTime = srDelta - nowDelta

    return diffTime


# Store whether we are to correct from system to configured timezone
def setCorrectForSysTZ(newVal=True):
    global CorrectForSysTZ

    CorrectForSysTZ = newVal


# Get whether we are to correct from system to configured timezone
# Returns a bool
def getCorrectForSysTZ():
    global CorrectForSysTZ

    return CorrectForSysTZ


CorrectForSysTZ = True


# if __name__ == "__main__":
#     pass
