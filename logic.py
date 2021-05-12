from collections import namedtuple
from collections.abc import Hashable
from dataclasses import dataclass, field
from typing import Any
from queue import PriorityQueue

import log


"""
Эта программа решает задачу поиска решения в игре "Ball sort puzzle".

Игра устроена следующим образом:
Есть натуральные параметры $N$, $M$ и $K$. В игре есть два типа сущностей:
колбочки и шарики. Колбочек $N + M$ штук, каждая вмещает в себя до $K$
шариков. При этом шарики могут извлекаться из колбочки только в порядке,
обратном порядку их туда попадания (как стек). Шариков в игре $NK$ штук.
Каждый шарик покрашен в один из $N$ цветов, шариков каждого цвета ровно
$K$ штук.

Цель игры: переложить шарики таким образом, чтобы в каждой колбе были
шарики только одного цвета, и при этом чтобы не было частично заполненных
колбочек. За один ход можно переложить шарик из любой колбы в любую
другую, если:
 - колба-источник непустая;
 - в колбе-приёмнике есть свободное место;
 - колба-приёмник либо пустая, либо верхний шарик в этой колбе того же
 цвета, что и перемещаемый.
"""


GameParameters = namedtuple("GameParameters", ["N", "M", "K"])


class Game:
    def __init__(self, parameters, configuration):
        self.parameters = parameters
        self.configuration = configuration

    def priority(self):
        return self.count_color_changes()

    def count_flask_fullness(self):
        result = 0
        for flask in self.configuration:
            result += min(len(flask), self.parameters.K - len(flask))
        return result

    @staticmethod
    def __is_positive_int(arg):
        return (type(arg) is int) and arg > 0

    def __repr__(self):
        return f"Game(parameters={repr(self.parameters)}, configuration={repr(self.configuration)})"

    @staticmethod
    def serialize_configuration(configuration, ball_sep='', flask_sep=';'):
        return flask_sep.join(map(lambda flask: ball_sep.join(map(str, flask)), configuration))

    @staticmethod
    def deserialize_configuration(configuration, ball_sep='', flask_sep=';'):
        flasks = configuration.split(flask_sep)
        if len(ball_sep) > 0:
            return tuple(map(lambda flask: tuple(flask.split(ball_sep)), flasks))
        else:
            return tuple(map(tuple, flasks))

    @staticmethod
    def find_optimal_parameters(configuration):
        flask_cnt = len(configuration)
        capacity = 0
        ball_cnt = 0

        for flask in configuration:
            ball_cnt += len(flask)
            capacity = max(capacity, len(flask))

        colors = ball_cnt // capacity

        return GameParameters(colors, flask_cnt - colors, capacity)

    def can_do_a_move(self, i, j):
        if type(i) is not int:
            return False
        if type(j) is not int:
            return False

        if i >= len(self.configuration) or i < 0:
            return False
        if j >= len(self.configuration) or j < 0:
            return False

        if i == j:
            return False
        if len(self.configuration[i]) == 0:
            return False
        if len(self.configuration[j]) == self.parameters.K:
            return False
        if len(self.configuration[j]) > 0 and self.configuration[j][-1] != self.configuration[i][-1]:
            return False

        if self.__is_out_of_game(i):
            return False

        return True

    def do_a_move_unsafe(self, i, j):
        new_configuration = list(self.configuration)
        ball = new_configuration[i][-1]
        new_configuration[i] = new_configuration[i][:-1]
        new_configuration[j] = new_configuration[j] + (ball,)
        return Game(self.parameters, tuple(new_configuration))

    def __is_out_of_game(self, i):
        return len(self.configuration[i]) == self.parameters.K and len(set(self.configuration[i])) == 1

    def count_color_changes(self):
        result = 0
        for flask in self.configuration:
            for i in range(1, len(flask)):
                if flask[i] != flask[i - 1]:
                    result += 1
        return result

    def do_a_move(self, i, j):
        if not self.can_do_a_move(i, j):
            raise ValueError("Impossible move")
        return self.do_a_move_unsafe(i, j)

    def serialized_configuration(self):
        return Game.serialize_configuration(self.configuration)

    def is_winning_configuration(self):
        for flask in self.configuration:
            if 0 < len(flask) < self.parameters.K:
                return False
            if len(set(flask)) > 1:
                return False
        return True

    def is_valid(self):
        if not Game.__is_positive_int(self.parameters.N):
            return False
        if not Game.__is_positive_int(self.parameters.M):
            return False
        if not Game.__is_positive_int(self.parameters.K):
            return False

        if type(self.configuration) is not tuple:
            return False
        if len(self.configuration) != self.parameters.N + self.parameters.M:
            return False

        unique_elements_counter = dict()

        for flask in self.configuration:
            if type(flask) is not tuple:
                return False
            if len(flask) > self.parameters.K:
                return False

            for ball in flask:
                if not isinstance(ball, Hashable):
                    return False
                unique_elements_counter[ball] = unique_elements_counter.get(ball, 0) + 1

        if len(unique_elements_counter) != self.parameters.N:
            return False

        for key, value in unique_elements_counter.items():
            if value != self.parameters.K:
                return False

        return True


@dataclass(order=True)
class PrioritizedItem:
    priority: int
    item: Any = field(compare=False)


class Solver:
    def __init__(self):
        self.logger = log.get_logger(log.class_fullname(self))

    def solve(self, initial_game):
        num_of_flasks = initial_game.parameters.N + initial_game.parameters.M

        heap = PriorityQueue()
        heap.put(PrioritizedItem(initial_game.priority(), initial_game))

        discovered = dict()
        discovered[initial_game.configuration] = None

        winning_game = None

        while not heap.empty():
            prior_item = heap.get()
            # priority = prior_item.priority
            game = prior_item.item

            if game.is_winning_configuration():
                self.logger.info("Found winning configuration")
                winning_game = game
                break

            for i in range(num_of_flasks):
                for j in range(num_of_flasks):
                    if game.can_do_a_move(i, j):
                        new_game = game.do_a_move_unsafe(i, j)
                        if new_game.configuration not in discovered:
                            discovered[new_game.configuration] = game.configuration
                            heap.put(PrioritizedItem(new_game.priority(), new_game))

        if winning_game is None:
            return None

        result = list()
        result.append(winning_game.configuration)
        while discovered[result[-1]] is not None:
            result.append(discovered[result[-1]])

        result.reverse()
        return result
