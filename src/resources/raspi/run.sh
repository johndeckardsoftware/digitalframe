#!/bin/bash

ssid=$(iwgetid -r)
echo "'$ssid'"

if [ "$ssid" != "YOUR WIFI SSID" ]; then
    read -p "wifi not available, press ctrl C to exit" -t 120
fi

sudo iw dev wlan0 set power_save off

cd /home/pi/digitalframe

LOG="digitalframe.log"

if grep -q "ERROR" $LOG; then
    echo "errors from last run:"
    tail -40 digitalframe.log
    read -p "Press key to continue.. " -n1 -s
    cp $LOG $LOG.old
    rm $LOG
fi

# Start a loop that runs indefinitely until an explicit exit or reboot occurs
while true; do
    /home/pi/digitalframe/venv/bin/python /home/pi/digitalframe/src/df.py --fullscreen >> $LOG 2>&1
    ret=$?
    echo $ret > run.log

    if [ $ret -eq 0 ]; then
        echo "ok"
        break  # Exit the loop and finish the script

    elif [ $ret -eq 1 ]; then
        echo "ERROR"
        tail -n 20 $LOG
        break  # Exit the loop on standard error

    elif [ $ret -eq 100 ]; then
        sudo poweroff --reboot -f
        break

    elif [ $ret -eq 101 ]; then
        sudo poweroff --poweroff -f
        break

    elif [ $ret -eq 102 ]; then
        echo "Reloading application..."
        # Do NOT break. The loop will naturally cycle back to the top
        # and re-execute the python command.
        sleep 3  # Optional: short delay to prevent aggressive looping if something goes wrong

    elif [ $ret -gt 127 ]; then
        echo "Fatal error:"
        tail -n 20 $LOG
        break  # Exit the loop on fatal errors
    else
        # Fallback for any other unhandled exit codes so the script doesn't loop infinitely by mistake
        break
    fi
done
