Control Dell Poweredge R730xd Fan Speeds
========================================

Written in order to manually manage fan control due to my use of "unapproved"
storage devices (in my case, a couple of Samsung EVO 850 SATA SSDs) which
causes fans to spin up to 100% under Dell dynamic fan control.  When the script
is used, Dell dynamic fan control is turned off, and it is only reenabled when
the script cannot get temps under control itself or when it exits due to an
error or is terminated.

Requires Python3.6+ as well as ``ipmitool``.

Tested only on Linux, not on Windows, although in theory it should work on
both.  Must be run as root on Linux.

The output of ``idracfanctl.py --help`` is::

  usage: idracfanctl.py [-h] [--temp-cpu-min TEMP_CPU_MIN]
                        [--temp-cpu-max TEMP_CPU_MAX]
                        [--temp-exhaust-max TEMP_EXHAUST_MAX]
                        [--fan-percent-min FAN_PERCENT_MIN]
                        [--fan-percent-max FAN_PERCENT_MAX]
                        [--fan-step FAN_STEP] [--hysteresis HYSTERESIS]
                        [--sleep SLEEP]
                        [--disable-pcie-cooling-response DISABLE_PCIE_COOLING_RESPONSE]
                        [--ipmitool IPMITOOL]

  Script to control Dell Poweredge fan speeds. All temps in °C. Must be run as
  root. Options that refer to CPU temp refer to the hottest CPU temp in the
  system, not an average of all CPU temps.

  optional arguments:
    -h, --help            show this help message and exit
    --temp-cpu-min TEMP_CPU_MIN
                          Script won't adjust fans from fan-percent-min til
                          temp-cpu-min in °C is reached. (default: 45)
    --temp-cpu-max TEMP_CPU_MAX
                          Max CPU temp in °C that should be allowed before
                          revert to Dell dynamic dan control. (default: 97)
    --temp-exhaust-max TEMP_EXHAUST_MAX
                          When exhaust temp reaches this value in °C, revert to
                          Dell dynamic fan control. (default: 65)
    --fan-percent-min FAN_PERCENT_MIN
                          The minimum percentage that the fans should run at
                          when under script control. (default: 13)
    --fan-percent-max FAN_PERCENT_MAX
                          The maxmum percentage that the fans should run at when
                          under script control. (default: 60)
    --fan-step FAN_STEP   The number of percentage points to step the fan curve
                          by. (default: 2)
    --hysteresis HYSTERESIS
                          Don't change fan speed unless the temp difference in
                          °C exceeds this number of degrees since the last fan
                          speed change. (default: 2)
    --sleep SLEEP         The number of seconds between attempts to readjust the
                          fan speed the script will wait within the main loop.
                          (default: 10)
    --disable-pcie-cooling-response DISABLE_PCIE_COOLING_RESPONSE
                          If 0, use the default Dell PCIe cooling response,
                          otherwise rely on this script to do the cooling even
                          for PCIe cards that may not have fans. NB: changes
                          IPMI settings. (default: 0)
    --ipmitool IPMITOOL   Path to ipmitool binary to use (default: ipmitool)

I use something like the following ``systemd`` service unit named
``idracfanctl.service`` to start the script at system startup::

  [Unit]
  After=local-fs.target
  Before=multi-user.target
  Description=Control Dell R730xd fans

  [Service]
  ExecStart=/path/to/python3 /path/to/idracfanctl.py
  Restart=always
  User=root
  KillSignal=SIGINT

  [Install]
  WantedBy=multi-user.target

Then to see how the script is working, you can do::

   sudo journalctl -u idracfanctl.service  -f

To see the information that this script operates against in real time, do::

   watch sudo ipmitool sdr type temperature

NB: be careful with the ``--disable-pci-cooling-response`` flag, I'm not sure
how to reenable Dell stock settings if it gets disabled without resetting your
iDRAC.  I use it because I have unapproved PCI hardware too, and this can cause
fans to always run at 100%, so I always want to disable it.

Tested only on a 128G Dell Poweredge R730xd with iDRAC 8 Enterprise 2.63.60.61
(Build 06) in a room with ambient temperatures around 23°C / 70°F.  There are
two E5-2697 v4 @ 2.30GHz CPUs in the system, each of which has 18 cores.  It
has 6 spinning rust SAS drives in it, 5 SATA SSDs on the front panel, 2 SATA
SSDs on the back panel, and 2 NVME drives on a PCI card inside.

Defaults to this script are slightly more aggressive fan-RPM-wise than Dell
dynamic fan control in that environment.

At near-zero CPU usage, with the default settings, my fans are usually at
13-20% and my CPU temps hover between 48-56°C.  With those same defaults, at
100% CPU usage, my fans are at 52-56%, and my CPU temps seem to top out at
between 87-90°C.

This works for me noise-wise and performance-wise; you might want to play
around with nondefault settings.  On my system, when CPU temps exceed 92°C or
so, the CPU temperature sensors get flaky and occasionally can't return a
value, so I like to keep them below that number.

Under script control, the stepping of the fans is less smooth than under Dell
dynamic control, and the script does not control individual fan RPMs like
dynamic control does; it sets all of them together to the same single
percentage value. I suspect each of these factors contribute to the
script-controlled fans sounding more aggressive than under Dell fan control
when load gets high.  But at least it doesn't sound like a jet engine when I
plug an unapproved device in.

