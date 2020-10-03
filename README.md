# QtSunsetter
Python/Qt application to give the sunset/sunrise time for a location and count the time to the next. Project files provided for Qt Creator (4.13.0)

Using python 3(.8) and Qt 5(.15) create a widget based application to allow input of a latitude, longitude and timezone clock offset in hours then use those to show the current time, the sunrise and sunset times on this day and the time until the next solar horizon crossing. Allows the user to specify whether to correct the local system clock for the chosen timezone and show the current time and remaining time to next solar horizon in that case. For example, allows the input of a different location from the one where it is run and see the sun rise/set details there rather than here.

Use by placing the .py and .ui files in a directory and launch by running thy python 3.8 program with the QtSunSetter.py file as an argument, e.g.:

\<path-to\>/python \<path-to\>/QtSunsetter.py

Required libraries include:

* The PySide2 Qt libraries (v 5.15 was used to develop)
* random
* subprocess
* time
* datetime
* math

Some of those will be installed by default with Pythoin 3.8+

The goal in writing this was for use of a live webcam frame capture application that requires manual modification of brightness/contrast type controls where day and night required different assumptions. A console version is used at present and this is a partially complete Qt UI based version that requires addition of the ability to execute a pair of "on sunrise/sunset" external applications at the correct time.

The solar time code is based on spreadsheet based examples published by the NOAA organization at: https://www.esrl.noaa.gov/gmd/grad/solcalc/calcdetails.html

As-of Spetember 2020, the intended target platform is Linux, no effort has been made to test functionality on other platforms.

Persistent configuration can be stored in the user's home directory, it current supports comments beginning at # characters and supports four settings:


Latitude as a signed decimal floating point number (positive values are North, negative values are South). Longitude as a signed decimal floating point number (positive values are East, negative values are West). The clock timezone offset in hours for the configured latitude/longitude as a signed decimal number. An optional switch to correct the displayed time from local system clock to the configured timezone clock offset. If not present the local system clock is used as the time at the configured latitude/longitude. Two options, one each to specify a program to run as sunrise or sunset is passed while QtSunsetter.py is running. Each can be a shell script. An example configuration might look like:


\# A place to watch

latitude=58.8

longitude=-4.5

timezone=1.0

CorrectForSystemTimezone

sunriserun=/path/to/AtSunriseProgram

sunsetrun=/path/to/AtSunsetProgram
