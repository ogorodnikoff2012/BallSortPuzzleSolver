class DisjointSetUnionWithBoundingRects:
    def __init__(self, points):
        self.points = points
        self.rects = [(x, y, 0, 0) for x, y in points]
        self.parents = list(range(len(points)))
        self.weights = [1] * len(points)

    def union(self, i, j):
        i = self.find(i)
        j = self.find(j)
        if self.weights[i] < self.weights[j]:
            i, j = j, i

        self.parents[j] = i
        self.rects[i] = Geometry.combine_two_rects(self.rects[i], self.rects[j])
        self.weights[i] += self.weights[j]

        return i

    def find(self, i):
        while self.parents[i] != i:
            self.parents[i] = self.find(self.parents[i])
            i = self.parents[i]

        return i

    def point(self, i):
        return self.points[i]

    def bounding_rect(self, i):
        return self.rects[self.find(i)]


def listify(index_to_object, index_list):
    list_of_objects = [None] * len(index_to_object)
    index_to_pos = dict()

    for pos, (index, obj) in enumerate(index_to_object.items()):
        index_to_pos[index] = pos
        list_of_objects[pos] = obj

    return list_of_objects, list(map(lambda idx: index_to_pos[idx], index_list))


class Geometry:
    @staticmethod
    def rect_x(rect):
        return rect[0]

    @staticmethod
    def rect_y(rect):
        return rect[1]

    @staticmethod
    def rect_width(rect):
        return rect[2]

    @staticmethod
    def rect_height(rect):
        return rect[3]

    @staticmethod
    def rectangle_center(rect):
        return rect[0] + rect[2] // 2, rect[1] + rect[3] // 2

    @staticmethod
    def combine_two_rects(rect_a, rect_b):
        min_x = min(rect_a[0], rect_b[0])
        min_y = min(rect_a[1], rect_b[1])
        max_x = max(rect_a[0] + rect_a[2], rect_b[0] + rect_b[2])
        max_y = max(rect_a[1] + rect_a[3], rect_b[1] + rect_b[3])
        return min_x, min_y, max_x - min_x, max_y - min_y

    @staticmethod
    def join_neighbours(rects, x_scale, y_scale):
        arcs = []

        for i, rect_i in enumerate(rects):
            center_i = Geometry.rectangle_center(rect_i)
            for j, rect_j in enumerate(rects):
                if i == j:
                    continue

                center_j = Geometry.rectangle_center(rect_j)
                dx = abs(center_i[0] - center_j[0])
                dy = abs(center_i[1] - center_j[1])
                sum_width = Geometry.rect_width(rect_i) + Geometry.rect_width(rect_j)
                sum_height = Geometry.rect_height(rect_i) + Geometry.rect_height(rect_j)

                if dx <= sum_width * x_scale and dy <= sum_height * y_scale:
                    arcs.append((i, j))

        return arcs

    @staticmethod
    def clusterize_rects(rects, x_scale, y_scale):
        arcs = Geometry.join_neighbours(rects, x_scale, y_scale)

        points = []
        for x, y, w, h in rects:
            points.append((x, y))
            points.append((x, y + h))
            points.append((x + w, y))
            points.append((x + w, y + h))

        dsu = DisjointSetUnionWithBoundingRects(points)
        for i in range(len(rects)):
            for delta in range(1, 4):
                dsu.union(4 * i, 4 * i + delta)

        for i, j in arcs:
            dsu.union(4 * i, 4 * j)

        unique_rects = dict()
        parent_link = list()

        for i in range(len(rects)):
            parent = dsu.find(4 * i)
            parent_link.append(parent)
            unique_rects[parent] = dsu.bounding_rect(4 * i)

        return listify(unique_rects, parent_link)
