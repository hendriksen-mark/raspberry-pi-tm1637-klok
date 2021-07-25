import sys
import time
import datetime
import RPi.GPIO as GPIO
import tm1637

Display = tm1637.TM1637(23,24,tm1637.BRIGHT_TYPICAL)
brightness = int(0)
pref_bri = int(0)
pref_currenttime = int()
pref_ShowDoublepoint = int()
ShowDoublepoint = False

Display.Clear()
Display.SetBrightnes(0)

while(True):
    now = datetime.datetime.now()
    hour = now.hour
    minute = now.minute
    second = now.second
    microsecond = now.microsecond
    currenttime = [ int(hour / 10), hour % 10, int(minute / 10), minute % 10 ]
    if pref_currenttime != currenttime:
        Display.Show(currenttime)
        pref_currenttime = currenttime

    if pref_ShowDoublepoint != ShowDoublepoint:
        Display.ShowDoublepoint(ShowDoublepoint)
        pref_ShowDoublepoint = ShowDoublepoint
        
    time.sleep(0.5)
    ShowDoublepoint = not ShowDoublepoint
