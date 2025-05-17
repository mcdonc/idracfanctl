Control Dell Poweredge R730XD Fan Speeds
========================================

My script to control fan speeds.  Requires Python3.6+ and its stdlib as well
as ``ipmitool``.

Written in order to manually manage fan control manually due to my use of
"unapproved" storage devices (in my case, a couple of Samsung EVO 850 SSDs)
which causes fans to spin up to 100% under Dell dynamic fan control.  When the
script is used, dynamic fan control is turned off, and it is only reenabled
when the script cannot get temps under control itself or when it is exited.

Must be run as root.

The output of ``idracfanctl.py --help`` is::

    usage: idracfanctl.py [-h] [--temp-cpu-min TEMP_CPU_MIN] [--temp-cpu-max TEMP_CPU_MAX] [--temp-exhaust-max TEMP_EXHAUST_MAX]
                          [--fan-percent-min FAN_PERCENT_MIN] [--fan-percent-max FAN_PERCENT_MAX] [--fan-step FAN_STEP] [--hysteresis HYSTERESIS]
                          [--sleep SLEEP] [--disable-pcie-cooling-response DISABLE_PCIE_COOLING_RESPONSE] [--ipmitool IPMITOOL]

    Script to control Dell Poweredge fan speeds. All temps in °C.

    options:
      -h, --help            show this help message and exit
      --temp-cpu-min TEMP_CPU_MIN
                            Script won't adjust fans from fan-percent-min til temp-cpu-min in °C is reached. (default: 45)
      --temp-cpu-max TEMP_CPU_MAX
                            Max CPU temp in °C that should be allowed before revert to Dell dynamic dan control. (default: 97)
      --temp-exhaust-max TEMP_EXHAUST_MAX
                            When exhaust temp reaches this value in °C, revert to Dell dynamic fan control. (default: 60)
      --fan-percent-min FAN_PERCENT_MIN
                            The minimum percentage that the fans should run at when under script control. (default: 10)
      --fan-percent-max FAN_PERCENT_MAX
                            The maxmum percentage that the fans should run at when under script control. (default: 57)
      --fan-step FAN_STEP   The number of percentage points to step the fan curve by. (default: 2)
      --hysteresis HYSTERESIS
                            Don't change fan speed unless the temp difference in °C exceeds this number of degrees since the last fan speed
                            change. (default: 2)
      --sleep SLEEP         The number of seconds between attempts to readjust the fan speed the script will wait within the main loop. (default:
                            10)
      --disable-pcie-cooling-response DISABLE_PCIE_COOLING_RESPONSE
                            If 0, use the default Dell PCIe cooling response, otherwise rely on this script to do the cooling even for PCIe cards
                            that may not have fans. NB: changes IPMI settings. (default: 0)
      --ipmitool IPMITOOL   Path to ipmitool binary to use (default: ipmitool)
  
And them are the docs.
      
NB: be careful with the ``--disable-pci-cooling-response`` flag, I'm not sure
how to reenable Dell stock settings if it gets disabled without resetting your
iDRAC.  I use it because I have unapproved PCI hardware too, and this can cause
fans to always run at 100%, so I always want to disable it.

Tested only on a Dell Poweredge R730XD with iDRAC 8 Enterprise 2.63.60.61
(Build 06) in a room with ambient temperatures around 23°C / 70°F.  There are
two E5-2697 v4 @ 2.30GHz CPUs in the system, each of which has 18 cores.  It
has 6 spinning rust SAS drives in it, 5 SATA SSDs on the front panel, 2 SATA
SSDs on the back panel, and 2 NVME drives on a PCI card inside.

Defaults to this script are slightly more aggressive fan-RPM-wise than Dell
dynamic fan control in that environment.  At near-zero load, with the default
settings, my fans are usually at 10% and my CPU temps hover between 50-52°C.
At 100% load, my fans are at 50%, and my CPU temp seem to top out at between
86-90°C.

Under manual control, the stepping of the fans is less smooth than under
dynamic control, and the script does not control individual fan RPMs like
dynamic control does; it sets all of them together to a single percentage, each
of which I suspect is why it at least sounds more aggressive than the default
fan control.  But at least it doesn't sound like a jet engine when I plug an
unapproved device in.
