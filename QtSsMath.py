# -*- coding: utf-8 -*-
#
# Manage the switching of QtSunsetter between day and night targets based on
# the sunrise/sunset times without user intervention. This is based on
# spreadsheet based examples published by the NOAA organization at the
# following location:
#     https://www.esrl.noaa.gov/gmd/grad/solcalc/calcdetails.html
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

import time
import datetime
from math import sin, cos, tan, asin, acos, atan, atan2, degrees, radians, pi
from QtSsDebug import debugMessage, debugIsEnabled


def refDays(aDate):
    # baseDate = datetime.date(1900, 1, 14)
    baseDate = datetime.date(1899, 12, 30)
    deltaDate = abs(aDate - baseDate)
    return deltaDate.days
# refDays


def fracOfLocalDay(aTime):
    # Get second of the day from the time
    fDay = aTime.hour * 3600.0
    fDay += aTime.minute * 60.0
    fDay += aTime.second * 1.0

    # Fraction of day is the second of the day divided by seconds in a day
    fDay /= 86400.0

    return fDay
# fracOfLocalDay


def timeFromDayFraction(fracOfDay):
    if (fracOfDay < 0.0) or (fracOfDay >= 1.0):
        # Bad fraction of the day, use midnight
        print("Bad fraction of day: {}, using midnight".format(fracOfDay))
        fracOfDay = 0.0

    # Convert to second of the day
    fracOfDay *= 86400.0

    # Get the h:m:s
    h = int(fracOfDay / 3600.0)
    m = int((fracOfDay - (3600.0 * h)) / 60.0)
    s = int(fracOfDay) % 60
    t = datetime.time(h, m, s)

    return t
# timeFromDayFraction


def JulianDay(aDate, aTime=datetime.time(0, 0, 0)):
    global HomeTZ

    jDay = refDays(aDate) + 2415018.5 + fracOfLocalDay(aTime) - HomeTZ / 24.0
    # =D2+2415018.5+E2-$B$5/24

    return jDay
# JulianDay


def JulianCentury(aDate, aTime=datetime.time(0, 0, 0)):
    jCent = JulianDay(aDate, aTime)
    jCent -= 2451545.0
    jCent /= 36525.0
    # =(F2-2451545)/36525

    return jCent
# JulianCentury


def SunGeomMeanLong(aDate, aTime=datetime.time(0, 0, 0)):
    jCent = JulianCentury(aDate, aTime)
    mLong = (280.46646 + jCent * (36000.76983 + jCent * 0.0003032)) % 360
    # =MOD(280.46646+G2*(36000.76983+G2*0.0003032),360)

    return mLong
# SunGeomMeanLong


def SunGeomMeanAnom(aDate, aTime=datetime.time(0, 0, 0)):
    jCent = JulianCentury(aDate, aTime)
    mAnom = 357.52911 + jCent * (35999.05029 - 0.0001537 * jCent)
    # =357.52911+G2*(35999.05029-0.0001537*G2)

    return mAnom
# SunGeomMeanAnom


def SunEqOfCtr(aDate, aTime=datetime.time(0, 0, 0)):
    jCent = JulianCentury(aDate, aTime)
    mAnom = SunGeomMeanAnom(aDate, aTime)
    sEqC = sin(radians(mAnom))
    sEqC *= (1.914602 - jCent * (0.004817 + 0.000014 * jCent))
    sEqC += sin(radians(2 * mAnom)) * (0.019993 - 0.000101 * jCent)
    sEqC += sin(radians(3 * mAnom)) * 0.000289
    # =SIN(RADIANS(J2))*(1.914602-G2*(0.004817+0.000014*G2))+SIN(RADIANS(2*J2))*(0.019993-0.000101*G2)+SIN(RADIANS(3*J2))*0.000289

    return sEqC
# SunEqOfCtr


def SunTrueLong(aDate, aTime=datetime.time(0, 0, 0)):
    tLong = SunGeomMeanLong(aDate, aTime) + SunEqOfCtr(aDate, aTime)
    # =I2+L2

    return tLong
# SunTrueLong


def SunTrueAnom(aDate, aTime=datetime.time(0, 0, 0)):
    tAnom = SunGeomMeanAnom(aDate, aTime) + SunEqOfCtr(aDate, aTime)
    # =J2+L2

    return tAnom
# SunTrueAnom


def SunRadVector(aDate, aTime=datetime.time(0, 0, 0)):
    oEccent = EarthOrbitEccent(aDate, aTime)
    tAnom = SunTrueAnom(aDate, aTime)
    rVec = (1.000001018 * (1 - oEccent * oEccent))
    rVec /= (1 + oEccent * cos(radians(tAnom)))
    # =(1.000001018*(1-K2*K2))/(1+K2*COS(RADIANS(N2)))

    return rVec
# SunRadVector


def SunAppLongDegrees(aDate, aTime=datetime.time(0, 0, 0)):
    jCent = JulianCentury(aDate, aTime)
    tLong = SunTrueLong(aDate, aTime)
    aLong = tLong - 0.00569 - 0.00478 * sin(radians(125.04 - 1934.136 * jCent))
    # =M2-0.00569-0.00478*SIN(RADIANS(125.04-1934.136*G2))

    return aLong
# SunAppLongDegrees

def SunRightAscension(aDate, aTime=datetime.time(0, 0, 0)):
    aLong = radians(SunAppLongDegrees(aDate, aTime))
    oCorr = radians(ObliqCorrDegrees(aDate, aTime))

    x = cos(aLong)
    y = cos(oCorr) * sin(aLong)

    rAscRad = atan2(y, x)
    rAscDeg = degrees(rAscRad)

    # aLong = 84.61
    # oCorr = 23.44
    # rAsc = degrees(atan2(cos(radians(aLong)),
    #                cos(radians(oCorr)) * sin(radians(aLong))))

    # =DEGREES(ATAN2(COS(RADIANS(P2)),COS(RADIANS(R2))*SIN(RADIANS(P2))))
    # For atan2:
    # x is COS(RADIANS(P2))
    # y is COS(RADIANS(R2))*SIN(RADIANS(P2))
    # In python math function is atan2(y, x)
    # In LibreOffice function is atan2(x, y)

    return rAscDeg
# SunRightAscension


def SunDeclination(aDate, aTime=datetime.time(0, 0, 0)):
    aLong = SunAppLongDegrees(aDate, aTime)
    oCorr = ObliqCorrDegrees(aDate, aTime)
    sDec = degrees(asin(sin(radians(oCorr)) * sin(radians(aLong))))
    # =DEGREES(ASIN(SIN(RADIANS(R2))*SIN(RADIANS(P2))))

    return sDec
# SunDeclination


def SunVariance(aDate, aTime=datetime.time(0, 0, 0)):
    oCorr = ObliqCorrDegrees(aDate, aTime)
    sVar = tan(radians(oCorr / 2)) * tan(radians(oCorr / 2))
    # =TAN(RADIANS(R2/2))*TAN(RADIANS(R2/2))

    return sVar
# SunVariance


def HASunrise(aDate, aTime=datetime.time(0, 0, 0)):
    global HomeLat

    sDecRad = radians(SunDeclination(aDate, aTime))
    homeLatRad =radians(HomeLat)
    haRiseIn = acos(cos(radians(90.833)) / (cos(homeLatRad) *
                    cos(sDecRad)) - tan(homeLatRad) *
                    tan(sDecRad))
    haRise = degrees(haRiseIn)
    # =DEGREES(ACOS(COS(RADIANS(90.833))/(COS(RADIANS($B$3))*COS(RADIANS(T2)))-TAN(RADIANS($B$3))*TAN(RADIANS(T2))))

    return haRise
# HASunrise


def MeanObliqEcliptic(aDate, aTime=datetime.time(0, 0, 0)):
    jCent = JulianCentury(aDate, aTime)
    mObEcclip = 23 + (26 + ((21.448 - jCent * (46.815 + jCent * (0.00059 -
                            jCent * 0.001813)))) / 60) / 60
    # =23+(26+((21.448-G2*(46.815+G2*(0.00059-G2*0.001813))))/60)/60

    return mObEcclip
# MeanObliqEcliptic


def ObliqCorrDegrees(aDate, aTime=datetime.time(0, 0, 0)):
    jCent = JulianCentury(aDate, aTime)
    mObEcclip = MeanObliqEcliptic(aDate, aTime)
    oCorr = mObEcclip + 0.00256 * cos(radians(125.04 - 1934.136 * jCent))
    # =Q2+0.00256*COS(RADIANS(125.04-1934.136*G2))

    return oCorr
# ObliqCorrDegrees


def EarthOrbitEccent(aDate, aTime=datetime.time(0, 0, 0)):
    jCent = JulianCentury(aDate, aTime)
    oEccent = 0.016708634 - jCent * (0.000042037 + 0.0000001267*jCent)
    # =0.016708634-G2*(0.000042037+0.0000001267*G2)

    return oEccent
# EarthOrbitEccent


# Eq of Time (minutes)
def eqOfTime(aDate, aTime=datetime.time(0, 0, 0)):
    mLong = SunGeomMeanLong(aDate, aTime)
    mAnom = SunGeomMeanAnom(aDate, aTime)
    oEccent = EarthOrbitEccent(aDate, aTime)
    sVary = SunVariance(aDate, aTime)
    # eTime = -1
    eTime = 4 * degrees(sVary * sin(2 * radians(mLong)) - 2 * oEccent *
                        sin(radians(mAnom)) + 4 * oEccent * sVary *
                        sin(radians(mAnom)) * cos(2 * radians(mLong)) - 0.5 *
                        sVary * sVary * sin(4 * radians(mLong)) - 1.25 *
                        oEccent * oEccent * sin(2 * radians(mAnom)))
    # =4*DEGREES(U2*SIN(2*RADIANS(I2))-2*K2*SIN(RADIANS(J2))+4*K2*U2*SIN(RADIANS(J2))*COS(2*RADIANS(I2))-0.5*U2*U2*SIN(4*RADIANS(I2))-1.25*K2*K2*SIN(2*RADIANS(J2)))

    return eTime
# egOfTime


def SolarNoon(aDate, aTime=datetime.time(0, 0, 0)):
    global HomeLat, HomeLong, HomeTZ

    # rDays = refDays(aDate)
    eTime = eqOfTime(aDate, aTime)
    sNoon = (720 - 4 * HomeLong - eTime + HomeTZ * 60) / 1440
    # =(720-4*$B$4-V2+$B$5*60)/1440

    return sNoon
# SolarNoon


def LocalSunrise(aDate, aTime=datetime.time(0, 0, 0)):
    hRise = abs(HASunrise(aDate, aTime))
    sNoon = abs(SolarNoon(aDate, aTime))
    lRise = sNoon - hRise * 4 / 1440
    # =X2-W2*4/1440

    return lRise
# LocalSunrise


def LocalSunset(aDate, aTime=datetime.time(0, 0, 0)):
    hRise = abs(HASunrise(aDate, aTime))
    sNoon = abs(SolarNoon(aDate, aTime))
    lSet = sNoon + hRise * 4 / 1440
    # =X2+W2*4/1440

    return lSet
# LocalSunset


def SunlightDuration(aDate, aTime=datetime.time(0, 0, 0)):
    sDur = 8 * HASunrise(aDate, aTime)
    # =8*W2

    return sDur
# SunlightDuration


def testFunction(aTime):
    global doDBug, Today
    if doDBug is True:
        x = JulianDay(Today, aTime)
        print("JulianDay: {}".format(x))
        x = JulianCentury(Today, aTime)
        print("JulianCentury: {}".format(x))
        x = SunGeomMeanLong(Today, aTime)
        print("SunGeomMeanLong: {}".format(x))
        x = SunGeomMeanAnom(Today, aTime)
        print("SunGeomMeanAnom: {}".format(x))
        x = EarthOrbitEccent(Today, aTime)
        print("EarthOrbitEccent: {}".format(x))
        x = SunEqOfCtr(Today, aTime)
        print("SunEqOfCtr: {}".format(x))
        x = SunTrueLong(Today, aTime)
        print("SunTrueLong: {}".format(x))
        x = SunTrueAnom(Today, aTime)
        print("SunTrueAnom: {}".format(x))
        x = SunRadVector(Today, aTime)
        print("SunRadVector: {}".format(x))
        x = SunAppLongDegrees(Today, aTime)
        print("SunAppLongDegrees: {}".format(x))
        x = MeanObliqEcliptic(Today, aTime)
        print("MeanObliqEcliptic: {}".format(x))
        x = ObliqCorrDegrees(Today, aTime)
        print("ObliqCorrDegrees: {}".format(x))
        x = SunRightAscension(Today, aTime)
        print("SunRightAscension: {}".format(x))
        x = SunDeclination(Today, aTime)
        print("SunDeclination: {}".format(x))
        x = SunVariance(Today, aTime)
        print("SunVariance: {}".format(x))
        x = eqOfTime(Today, aTime)
        print("eqOfTime: {}".format(x))
        x = HASunrise(Today, aTime)
        print("HASunrise: {}".format(x))
        x = SolarNoon(Today, aTime)
        x *= 24 * 3600
        h = int(x / 3600)
        m = int((x - (3600 * h)) / 60)
        s = int(x) % 60
        t = datetime.time(h, m, s)
        # t = datetime.time(0, 0, 0)
        print("SolarNoon: {} - {}:{}:{} - {}".format(x, h, m, s, t))
        x = abs(LocalSunrise(Today, aTime))
        x *= 24 * 3600
        h = int(x / 3600)
        m = int((x - (3600 * h)) / 60)
        s = int(x) % 60
        t = datetime.time(h, m, s)
        # t = datetime.time(0, 0, 0)
        print("LocalSunrise: {} - {}:{}:{} - {}".format(x, h, m, s, t))
        x = abs(LocalSunset(Today, aTime))
        x *= 24 * 3600
        h = int(x / 3600)
        m = int((x - (3600 * h)) / 60)
        s = int(x) % 60
        t = datetime.time(h, m, s)
        # t = datetime.time(0, 0, 0)
        print("LocalSunset: {} - {}:{}:{} - {}".format(x, h, m, s, t))
        x = SunlightDuration(Today, aTime)
        print("SunlightDuration: {}".format(x))
# testFunction


def getLatitude():
    global HomeLat

    return HomeLat


def setLatitude(newLat):
    global HomeLat

    if (newLat >= -90.0) and (newLat <= 90.0):
        HomeLat = newLat


def getLongitude():
    global HomeLong

    return HomeLong


def setLongitude(newLon):
    global HomeLong

    if (newLon >= -180.0) and (newLon <= 180.0):
        HomeLong = newLon


def setSystemTime():
    global systemTime

    systemTime = time.localtime()


def getHomeTZ():
    global HomeTZ

    return HomeTZ


def setHomeTZ(tzOffset):
    global HomeTZ

    if tzOffset < 86400:
        HomeTZ = 1.0 * tzOffset
        HomeTZ /= 3600.0


def setLocalTZ():
    global HomeTZ

    HomeTZ = 1.0 * systemTime.tm_gmtoff
    HomeTZ /= 3600.0

    # print("TZ: {}".format(HomeTZ))


def SsMathDebug():
    global doDBug

    return doDBug


def SsMathTest():
    global doTest

    return doTest


# Global state
doDBug = True
doTest = False

HomeLat = 29.976634
HomeLong = -101.766673
# HomeLat = 55.8
# HomeLong = -4.5
Today = datetime.date.today()
systemTime = time.localtime()
HomeTZ = 1.0 * systemTime.tm_gmtoff
HomeTZ /= 3600.0
