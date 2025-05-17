#!/usr/bin/env python3
import argparse
import time
import subprocess
import logging
import sys


class Fans:
    DISABLE_PCIE_COOLING_RESPONSE = (
        "raw 0x30 0xCE 0x00 0x16 0x05 0x00 0x00 0x00 0x05 0x00 0x01 0x00 0x00"
    )

    def __init__(
        self,
        temp_cpu_min,
        temp_cpu_max,
        temp_exhaust_max,
        fan_percent_min=10,
        fan_percent_max=80,
        fan_step=5,
        hysteresis=2,
        sleep=30,
        disable_pcie_cooling_response=True,
        ipmitool="ipmitool",
    ):
        self.sleep = sleep
        self.last_pct = 0
        self.last_temp = 0
        self.temp_exhaust_max = temp_exhaust_max
        self.temp_cpu_max = temp_cpu_max
        self.disable_pcie_cooling_response = disable_pcie_cooling_response
        self.hysteresis = hysteresis
        self.ipmitool = ipmitool
        self.fan_mode = "dynamic"
        self.cpu_curve = {}
        temp_cpu_range = temp_cpu_max - temp_cpu_min
        for pct in range(0, fan_percent_max + fan_step, fan_step):
            temp = temp_cpu_min + (pct / fan_percent_max) * temp_cpu_range
            if pct < fan_percent_min:
                pct = fan_percent_min
            self.cpu_curve[temp] = pct
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)

    def run(self, command, **runargs):
        self.out(f"{command}", severity=logging.DEBUG)
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            **runargs,
        )
        return result

    def get_temps(self):
        cpus = ("0Eh", "0Fh")
        exhaust = "01h"
        cmd = f"{self.ipmitool} sdr type temperature"
        result = self.run(cmd)
        cpu_temps = []
        for line in result.stdout.split("\n"):
            if not line:
                continue
            desc, offset, _, _, deg = [x.strip() for x in line.split("|")]
            temp = deg.split()[0]
            if offset in cpus:
                try:
                    cpu_temps.append(int(temp))
                except ValueError:  # cannot convert "No reading" to int
                    self.out(
                        f"Problem reading cpu {offset} temp, got {temp}, "
                        f"using max {self.temp_cpu_max}"
                    )
                    cpu_temps.append(self.temp_cpu_max)
            if offset == exhaust:
                try:
                    exhaust_temp = int(temp)
                except ValueError:  # cannot convert "No reading" to int
                    self.out(
                        f"Problem reading exhaust temp, got {temp}, "
                        f"using max {self.temp_exhaust_max}"
                    )
                    exhaust_temp = self.temp_exhaust_max
        temps = {
            "cpu_max": max(cpu_temps),
            "cpu_avg": sum(cpu_temps) / len(cpu_temps),
            "exhaust": exhaust_temp,
        }
        return temps

    def set_fan_percent(self, pct):
        hexspeed = hex(pct)
        cmd = f"{self.ipmitool} raw 0x30 0x30 0x02 0xff {hexspeed}"
        self.run(cmd)

    def adjust(self):
        cpu_temps = sorted(self.cpu_curve.items())
        temps = self.get_temps()
        current_cpu_temp = temps["cpu_max"]
        current_exhaust_temp = temps["exhaust"]

        if current_exhaust_temp > self.temp_exhaust_max:
            # panic
            self.out(
                f"exhaust: {current_exhaust_temp}° > max "
                f"{self.temp_exhaust_max}°, go dynamic"
            )
            self.dynamic()
            return

        for cpu_temp in cpu_temps:
            compare_temp, target_pct = cpu_temp
            if current_cpu_temp > compare_temp:
                continue
            else:
                hm = abs(current_cpu_temp - self.last_temp) > self.hysteresis
                if target_pct != self.last_pct and hm:
                    self.last_pct = target_pct
                    self.last_temp = current_cpu_temp
                    self.manual()
                    self.out(
                        f"setting fans to {target_pct}% @ {current_cpu_temp}°"
                    )
                    self.set_fan_percent(target_pct)
                else:
                    if hm:
                        self.out(
                            f"fans already @ {target_pct}% {current_cpu_temp}°",
                            severity=logging.DEBUG,
                        )
                    else:
                        self.out(
                            f"last temp {self.last_temp}° "
                            f"curr temp {current_cpu_temp}° "
                            f"curr pct {self.last_pct}% "
                            f"target pct {target_pct}% "
                            f"hysteresis {self.hysteresis}",
                            severity=logging.DEBUG,
                        )
                break
        else:  # nobreak
            self.out(
                f"cpu temp uncontrollable, go dynamic @ {current_cpu_temp}°"
            )
            self.dynamic()

    def manual(self):
        if self.fan_mode != "manual":
            self.out("going manual mode")
            self.fan_mode = "manual"
            cmd = f"{self.ipmitool} raw 0x30 0x30 0x01 0x00"
            self.run(cmd)

    def dynamic(self):
        if self.fan_mode != "dynamic":
            self.out("going dynamic (Dell) mode")
            self.fan_mode = "dynamic"
            cmd = f"{self.ipmitool} raw 0x30 0x30 0x01 0x01"
            self.run(cmd)

    def control(self):
        self.out("triggers")
        for k, v in sorted(self.cpu_curve.items()):
            self.out(f"{k:.2f}° -> {v}%")
        if self.disable_pcie_cooling_response:
            self.out("disabling pcie cooling response")
            # NB: no idea how to reenable cooling response
            self.run(f"{self.ipmitool} {self.DISABLE_PCIE_COOLING_RESPONSE}")
        try:
            self.manual()
            while True:
                self.adjust()
                time.sleep(self.sleep)
        finally:
            self.dynamic()

    def out(self, msg, severity=logging.INFO):
        self.logger.log(severity, msg)
        sys.stdout.flush()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description=(
            "Script to control Dell Poweredge fan speeds. All temps in °C. "
            "Must be run as root.  Options that refer to CPU temp refer to "
            "the hottest CPU temp in the system, not an average of all CPU "
            "temps."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    ap.add_argument(
        "--temp-cpu-min",
        help=(
            "Script won't adjust fans from fan-percent-min til temp-cpu-min "
            "in °C is reached."
        ),
        type=int,
        default=45,
    )
    ap.add_argument(
        "--temp-cpu-max",
        help=(
            "Max CPU temp in °C that should be allowed before revert to Dell "
            "dynamic dan control."
        ),
        type=int,
        default=97,
    )
    ap.add_argument(
        "--temp-exhaust-max",
        help=(
            "When exhaust temp reaches this value in °C, revert to Dell "
            "dynamic fan control."
        ),
        type=int,
        default=60,
    )
    ap.add_argument(
        "--fan-percent-min",
        help=(
            "The minimum percentage that the fans should run at when under "
            "script control."
        ),
        type=int,
        default=10,
    )
    ap.add_argument(
        "--fan-percent-max",
        help=(
            "The maxmum percentage that the fans should run at when under "
            "script control."
        ),
        type=int,
        default=60,
    )
    ap.add_argument(
        "--fan-step",
        help="The number of percentage points to step the fan curve by.",
        type=int,
        default=2,
    )
    ap.add_argument(
        "--hysteresis",
        help=(
            "Don't change fan speed unless the temp difference in °C exceeds "
            "this number of degrees since the last fan speed change."
        ),
        type=int,
        default=2,
    )
    ap.add_argument(
        "--sleep",
        help=(
            "The number of seconds between attempts to readjust the fan speed "
            "the script will wait within the main loop."
        ),
        type=int,
        default=10,
    )
    ap.add_argument(
        "--disable-pcie-cooling-response",
        help=(
            "If 0, use the default Dell PCIe cooling response, otherwise "
            "rely on this script to do the cooling even for PCIe cards that "
            "may not have fans.  NB: changes IPMI settings."
        ),
        type=bool,
        default=0,
    )
    ap.add_argument(
        "--ipmitool", help="Path to ipmitool binary to use", default="ipmitool"
    )
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    # all temps in °C
    fans = Fans(
        temp_cpu_min=args.temp_cpu_min,
        temp_cpu_max=args.temp_cpu_max,
        temp_exhaust_max=args.temp_exhaust_max,
        fan_percent_min=args.fan_percent_min,
        fan_percent_max=args.fan_percent_max,
        fan_step=args.fan_step,
        hysteresis=args.hysteresis,
        sleep=args.sleep,
        disable_pcie_cooling_response=args.disable_pcie_cooling_response,
        ipmitool=args.ipmitool,
    )
    try:
        fans.control()
    except KeyboardInterrupt:
        pass
