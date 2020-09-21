# QtSunsetter
Python/Qt application to give the sunset/sunrise time for a location and count the time to the next

Using python 3(.8) and Qt 5(.15) create a widget based application to allow input of a latitude, longitude and timezone clock offset in hours then use those to show the current time, the sunrise and sunset times on this day and the time until the next solar horizon crossing. Allows the user to specify whether to correct the local system clock for the chosen timezone and show the current time and remaining time to next solar horizon in that case. For example, allows the input of a different location from the one where it is run and see the sun rise/set details there rather than here.

The goal in writing was for use of a live webcam frame capture application that requires manual modification of brightness/contrast type controls where day and night required different assumptions. A console version is used at present and this is a partially complete Qt UI based version that requires addition of the ability to execute a pair of "on sunrise/sunset" external applications at the correct time.

The solar time code is based on spreadsheet based examples supplied by the NOAA organization at: https://www.esrl.noaa.gov/gmd/grad/solcalc/calcdetails.html

As-of Spetember 2020, the intended target platform is Linux, no effort has been made to test functionality on other platforms.
