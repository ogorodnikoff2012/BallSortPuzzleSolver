from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
import pytesseract as tess

import algorithm as algo
import log
import logic


class GUIConnector:
    __pytesseractConfig = r'-l eng --oem 3 --psm 10 -c tessedit_char_whitelist="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ" '

    def __init__(self, adb_connector, device):
        self.logger = log.get_logger(log.class_fullname(self))
        self.adb_connector = adb_connector
        self.device = device
        self.flask_coordinates = []

    @staticmethod
    def __threshold(grayscale_image, thresh=100):
        return cv2.threshold(grayscale_image, thresh, 255, cv2.THRESH_BINARY)[1]

    @staticmethod
    def __grayscale(image):
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def __preprocess(image):
        thresholds = []
        for i in range(image.shape[-1]):
            thresholds.append(GUIConnector.__threshold(image[:, :, i]))
        grayscale = GUIConnector.__grayscale(image)
        thresholds.append(GUIConnector.__threshold(grayscale))

        threshold = np.max(np.array(thresholds), axis=0)
        # flask_borders = GUIConnector.__threshold(cv2.blur(GUIConnector.__threshold(grayscale, 225), (5, 5)), 1)
        # threshold = np.bitwise_and(threshold, np.bitwise_not(flask_borders))

        # Cut header and footer
        img_height = image.shape[0]
        header_height = int(img_height / 10)
        footer_height = int(img_height / 10)
        threshold[:header_height] = 0
        threshold[-footer_height:] = 0

        return threshold

    @staticmethod
    def __find_objects(image):
        items = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = items[0] if len(items) == 2 else items[1]
        return contours

    @staticmethod
    def __get_bounding_rectangles(contours):
        return [cv2.boundingRect(contour) for contour in contours]

    def __recognize_glyphs(self, thresh, contours, rectangles):
        inv_thresh = np.bitwise_not(thresh)
        base = np.full(inv_thresh.shape, 255, dtype=thresh.dtype)

        glyphs = []

        for contour, (x, y, w, h) in zip(contours, rectangles):
            base[y:y + h, x:x + w] = inv_thresh[y:y + h, x:x + w]
            txt = tess.image_to_string(base, config=GUIConnector.__pytesseractConfig).strip()
            self.logger.debug("Found %s at %dx%d+%d+%d", repr(txt), w, h, x, y)
            glyphs.append(txt)
            base[y:y + h, x:x + w] = 255

        return glyphs

    def __recognize_glyphs_v2(self, thresh, contours, rectangles):
        inv_thresh = np.bitwise_not(thresh)
        base = np.full(inv_thresh.shape, 255, dtype=thresh.dtype)

        # noinspection PyShadowingNames
        def func(image, rect):
            w, h, x, y = rect
            txt = tess.image_to_string(image, config=GUIConnector.__pytesseractConfig).strip()
            self.logger.debug(f"Found {repr(txt)} at {w}x{h}+{x}+{y}")
            return txt

        images = [base.copy() for _ in rectangles]
        for i, (x, y, w, h) in enumerate(rectangles):
            images[i][y:y + h, x:x + w] = inv_thresh[y:y + h, x:x + w]

        with ThreadPoolExecutor(max_workers=1) as executor:
            self.logger.debug("Running ThreadPoolExecutor")
            glyphs = list(executor.map(func, images, rectangles))
            # See https://docs.python.org/3/library/functions.html?highlight=unzip#zip
            return glyphs

    @staticmethod
    def __find_flasks(rects, screen_width):
        visible_flasks, rect_to_visible_flask = algo.Geometry.clusterize_rects(rects, 0.5, 1)
        mirrored_flasks = [(screen_width - x - w, y, w, h) for x, y, w, h in visible_flasks]
        flasks, old_flask_to_new = algo.Geometry.clusterize_rects(visible_flasks + mirrored_flasks, 0.5, 0.5)
        rect_to_flask = [old_flask_to_new[rect_to_visible_flask[i]] for i in range(len(rects))]
        return flasks, rect_to_flask

    @staticmethod
    def __build_game_configuration(rects, glyphs, rect_to_flask, flask_cnt):
        flasks = [[] for _ in range(flask_cnt)]
        for rect_id, flask_id in enumerate(rect_to_flask):
            flasks[flask_id].append(rect_id)

        for flask in flasks:
            flask.sort(key=lambda rect_id: algo.Geometry.rect_y(rects[rect_id]), reverse=True)

        return tuple(tuple(map(lambda rect_id: glyphs[rect_id], flask)) for flask in flasks)

    def read_game(self):
        image = self.adb_connector.take_screenshot(self.device)
        preprocessed_image = GUIConnector.__preprocess(image)
        objects = GUIConnector.__find_objects(preprocessed_image)
        rects = GUIConnector.__get_bounding_rectangles(objects)
        glyphs = self.__recognize_glyphs(preprocessed_image, objects, rects)
        flasks, rect_to_flask = GUIConnector.__find_flasks(rects, image.shape[1])
        self.flask_coordinates = [algo.Geometry.rectangle_center(flask) for flask in flasks]

        game_configuration = GUIConnector.__build_game_configuration(rects, glyphs, rect_to_flask, len(flasks))
        self.logger.debug("Discovered configuration: %s", logic.Game.serialize_configuration(game_configuration))
        game_parameters = logic.Game.find_optimal_parameters(game_configuration)
        game = logic.Game(game_parameters, game_configuration)
        if not game.is_valid():
            raise RuntimeError("Failed to recognize game")
        return game

    def do_action(self, flask_id):
        self.adb_connector.tap(self.device, self.flask_coordinates[flask_id])
