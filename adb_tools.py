import base64
import re
import subprocess
import time

import cv2
import numpy as np

import log


class Device:
    def __init__(self, device_info):
        self.raw_str = device_info
        tokens = device_info.split()
        self.serial = tokens[0]
        self.status = tokens[1]

        for token in tokens[2:]:
            key, value = token.split(':', 1)
            self.__setattr__(key, value)

    def __str__(self):
        return self.raw_str


class ADBConnector:
    __activityRecord = re.compile(r"^mResumedActivity:\s*ActivityRecord{\w+\s+\w+\s+(\S+)\s+\w+}$")

    def __init__(self, retry_delay):
        self.logger = log.get_logger(log.class_fullname(self))
        self.retry_delay = retry_delay

    @staticmethod
    def device_list():
        process = subprocess.Popen(["adb", "devices", "-l"], stdout=subprocess.PIPE, universal_newlines=True)
        out, _ = process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"Non-zero exit code: {process.returncode}")

        body = out.split('\n', 1)[1]
        return list(map(Device, body.strip().split('\n')))

    def check_if_screen_is_on(self, device):
        self.logger.debug("Checking if device screen is on")
        adb = subprocess.Popen(["adb", "-s", device.serial, "shell",
                                "dumpsys activity | grep 'mWakefulness'"], stdout=subprocess.PIPE,
                                universal_newlines=True)
        adb_output, _ = adb.communicate()
        exit_code = adb.returncode

        if exit_code != 0:
            self.logger.warn("Non-zero exit code %s", exit_code)
            raise RuntimeError(f"Non-zero exit code: {exit_code}")

        line = adb_output.split('\n')[0].strip()
        kv = line.split('=', 1)
        if len(kv) != 2:
            raise RuntimeError(f"Cannot parse response: {line}")

        key, value = kv
        if key != 'mWakefulness':
            raise RuntimeError(f"Bad key: {key}")

        if value == 'Asleep':
            return False
        elif value == 'Awake':
            return True
        else:
            raise RuntimeError(f"Bad value: {value}")


    def check_activity(self, device, activity_re):
        adb = subprocess.Popen(["adb", "-s", device.serial, "shell",
                                "dumpsys activity a | grep -E 'mResumedActivity'"], stdout=subprocess.PIPE,
                               universal_newlines=True)
        adb_output, _ = adb.communicate()
        exit_code = adb.returncode

        if exit_code != 0:
            self.logger.warn("Non-zero exit code %s", exit_code)
            return None

        line = adb_output.split('\n')[0].strip()
        m = ADBConnector.__activityRecord.match(line)
        if m is None:
            self.logger.warn("Malformed response from ADB (line=%s)", repr(line))

        activity_name = m.group(1)
        if activity_re.match(activity_name):
            self.logger.info("Match: %s", activity_name)
            return activity_name
        else:
            self.logger.info("Mismatch: %s", activity_name)
            return None

    def wait_for_activity(self, device, activity_re, comment=None):
        self.logger.debug("Waiting for activity %s", activity_re)

        activity = None
        while activity is None:
            activity = self.check_activity(device, activity_re)
            if activity is None:
                self.logger.info("Retry in %f seconds", self.retry_delay)
                time.sleep(self.retry_delay)

        return activity

    def take_screenshot(self, device):
        # See https://stackoverflow.com/a/61629220
        self.logger.debug("Taking screenshot")
        # noinspection SpellCheckingInspection
        adb = subprocess.Popen(["adb", "-s", device.serial, "shell",
                                "screencap -p | base64"], stdout=subprocess.PIPE)
        adb_output, _ = adb.communicate()
        png_screenshot_data = base64.b64decode(adb_output)
        image = cv2.imdecode(np.frombuffer(png_screenshot_data, np.uint8), cv2.IMREAD_COLOR)
        return image

    def tap(self, device, point):
        self.logger.debug("Tap at (%d, %d)", *point)
        subprocess.run(["adb", "-s", device.serial, "shell", "input", "tap", str(point[0]), str(point[1])])
