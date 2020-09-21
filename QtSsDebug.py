# This Python file uses the following encoding: utf-8
#
# Code for debug logging to the console
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


def debugMessage(txt):
    global doDebug

    if doDebug is True:
        print(txt)


def debugIsEnabled():
    global doDebug

    return doDebug


def disableDebug():
    global doDebug

    doDebug = False


def enableDebug():
    global doDebug

    doDebug = True


doDebug = False

# if __name__ == "__main__":
#     pass
