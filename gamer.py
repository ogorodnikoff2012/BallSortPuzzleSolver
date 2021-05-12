import re
import time

import adb_tools
import gui
import log
import logic
import ui_tools


class Gamer:
    __gameAppActivity = re.compile(r"^com\.spicags\.ballsort/.*$")
    __gameActivity = re.compile(r"^com\.spicags\.ballsort/com\.unity3d\.player\.UnityPlayerActivity$")
    __gameAdActivity = re.compile(r"^com\.spicags\.ballsort/com\.google\.android\.gms\.ads\.AdActivity$")

    def __init__(self):
        self.logger = log.get_logger(log.class_fullname(self))
        self.adb_connector = adb_tools.ADBConnector(retry_delay=1)
        self.selected_device = None
        self.wait_delay = 0.05
        self.retry_delay = 4
        self.solver = logic.Solver()

        self.logger.info("Initializing Gamer instance")
        self.select_device()

    def select_device(self):
        self.logger.info("Selecting Android device...")
        try:
            device_list = self.adb_connector.device_list()
        except Exception as exp:
            raise self.error("Failed to get device list: %s", exp)

        if len(device_list) == 0:
            raise self.error("Empty device list")

        selection_index = 0
        if len(device_list) > 1:
            selection_index = ui_tools.select_from_list(device_list)

        self.logger.info("Selected device: %s", device_list[selection_index])
        self.selected_device = device_list[selection_index]

    def error(self, *args, **kwargs):
        self.logger.error(*args, **kwargs)
        return RuntimeError(*args)

    def try_close_ad(self):
        # It's a stub
        ui_tools.msg("Please close the advertisement")
        time.sleep(self.wait_delay)

    @staticmethod
    def __transform_to_steps(solution):
        steps = []
        for i in range(1, len(solution)):
            src = None
            dst = None
            for j, (old, new) in enumerate(zip(solution[i - 1], solution[i])):
                if len(old) < len(new):
                    dst = j
                if len(new) < len(old):
                    src = j
            steps.append(src)
            steps.append(dst)
        return steps

    def pass_level(self):
        while self.adb_connector.check_activity(self.selected_device, Gamer.__gameActivity) is None:
            self.try_close_ad()

        gui_connector = gui.GUIConnector(self.adb_connector, self.selected_device)
        self.logger.debug("Trying to recognize screen")

        try:
            game = gui_connector.read_game()
            self.logger.info("Screen recognized, configuration: %s", repr(game))
            solution = self.solver.solve(game)
            self.logger.info("Solution found, %d moves, starting play", len(solution) - 1)
            steps = Gamer.__transform_to_steps(solution)
            for step in steps:
                if self.adb_connector.check_activity(self.selected_device, Gamer.__gameActivity) is None:
                    raise RuntimeError("Game is closed")
                gui_connector.do_action(step)
                time.sleep(self.wait_delay)
            self.logger.info("Level passed")
        except Exception as exp:
            self.logger.error("Exception: %s", exp)
            raise exp

    def run(self):
        self.logger.info("Running Gamer")
        self.adb_connector.wait_for_activity(self.selected_device, Gamer.__gameAppActivity,
                                             comment="Please open the game")
        self.logger.debug("Waiting while game is launched")
        time.sleep(self.retry_delay)

        while True:
            try:
                self.pass_level()
            except Exception as exp:
                self.logger.warn("Verify that game is in proper state (exp=%s)", exp)

            time.sleep(self.wait_delay)
            while self.adb_connector.check_activity(self.selected_device, Gamer.__gameActivity) is None:
                self.try_close_ad()
            self.logger.debug("Waiting while game is ready")
            time.sleep(self.retry_delay)
