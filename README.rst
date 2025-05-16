Control Dell Poweredge R730XD Fan Speeds
========================================

My script to control fan speeds.  Requires Python3.6+ and its stdlib as well
as ``ipmitool``.

Written in order to manage fan control manually due to use of "unapproved"
disks (in my case, a couple of Samsung EVO 850 SSDs) causing fans to spin up to
100% under Dell dynamic fan control.  When the script is used, dynamic fan
control is turned off, and it is only reenabled when the script cannot get
temps under control itself.

Must be run as root.

Run ``idracfanctl.py --help`` to see the options of the script.

NB: be careful with the ``--disable-pci-cooling-response`` flag, I'm not sure
how to reenable Dell stock settings if it gets disabled without resetting your
iDRAC.  I use it because I have unapproved PCI hardware too, and I don't want
it to cause fans to always run at 100%, so I always want to disable it.

Tested only on a Dell Poweredge R730XD in a room with ambient temperatures
around 23°C / 70°F.  Defaults to this script are slightly more aggressive at
running fans than Dell dynamic fan control in that environment.  At zero load,
with the default settings, my fans are usually at 10%.  At 100% load, my fans
are at 50%, and my CPU temps are between 86-90°F.

