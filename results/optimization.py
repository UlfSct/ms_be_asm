import logging
import time
from collections import defaultdict

from django.db import transaction
from krashemit.algorithms.country_optimization_v4 import CountriesAlgorithm
from django.db.models import Prefetch
from results.models import Result, ResultEquipment, ResultConnection, ResultConnectionPoint
import numpy as np
import heapq

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ
# ══════════════════════════════════════════════════════════════════════

# Веса для фитнес-функции (можно настраивать)
FITNESS_WEIGHTS = {
    'pipe_length': 0.1,      # вес для длины труб
    'scheme_volume': 0.001,  # вес для объёма схемы
    'pipe_bends': 0.01,      # вес для количества изгибов
    'center_distance': 1.0,  # вес для удалённости от центра
}

# Параметры трассировки
DEFAULT_PIPE_RADIUS = 50.0   # радиус изгиба трубы по умолчанию
MIN_PIPE_SEGMENT = 10.0      # минимальная длина сегмента трубы

# Параметры коллизий
COLLISION_MARGIN = 100.0     # минимальный отступ между оборудованием (мм)

# Границы пространства
SPACE_BOUNDS = {
    'min': -5000.0,
    'max': 5000.0,
}

# Параметры генетического алгоритма
GA_PARAMS = {
    'population_size': 100,      # N - больше особей = лучше поиск
    'imperialists': 15,          # M - больше империалистов
    'colonies_range': [3, 20],   # n - диапазон колоний у империалиста
    'imperialists_range': [2, 8],  # m
    'assimilation_rate': 12,     # k - быстрее движение к оптимуму
    'revolution_rate': 5,        # l - меньше революций = стабильнее
    'exploitation': [0.1, 0.3],  # ep - локальный поиск
    'exploration': [0.0001, 1],  # p - глобальный поиск
    'max_mutation': 50,          # больше мутаций для разнообразия
    'max_iterations': 1,        # tmax - самое важное! Было 2, стало 50
    'angle_precision': 2,        # меньше генов на угол = грубее, но быстрее
    'coord_precision': 20,       # меньше генов на координату
}


# ══════════════════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ══════════════════════════════════════════════════════════════════════

def get_orthogonal_direction(normal):
    """
    Определяет ортогональное направление по нормали.
    Возвращает единичный вектор строго по X или Z.
    """
    abs_x = abs(normal[0])
    abs_z = abs(normal[2])

    if abs_x > abs_z:
        return np.array([1 if normal[0] > 0 else -1, 0, 0])
    else:
        return np.array([0, 0, 1 if normal[2] > 0 else -1, 0])


def _is_path_orthogonal(path_points, tolerance=1e-3):
    """
    Проверяет, что ВСЕ сегменты пути строго параллельны либо оси X, либо оси Z.
    """
    if len(path_points) < 2:
        return True

    for i in range(len(path_points) - 1):
        p1 = np.array(path_points[i])
        p2 = np.array(path_points[i + 1])

        dx = abs(p2[0] - p1[0])
        dz = abs(p2[2] - p1[2])

        # Проверяем, что сегмент не диагональный
        # Одно из движений должно быть практически нулевым
        if dx > tolerance and dz > tolerance:
            logger.debug(f"Неортогональный сегмент: ({p1[0]:.1f}, {p1[2]:.1f}) -> ({p2[0]:.1f}, {p2[2]:.1f}), "
                         f"dx={dx:.1f}, dz={dz:.1f}")
            return False

        # Проверяем, что Y не меняется (все трубы на одной высоте)
        dy = abs(p2[1] - p1[1])
        if dy > tolerance:
            logger.debug(f"Изменение высоты в сегменте: dy={dy:.3f}")
            # Пока разрешаем изменение высоты, но логируем

    return True


def rotate_vector(v, angle_deg):
    """Поворот вектора вокруг оси Y."""
    angle = np.radians(angle_deg)
    cos_a, sin_a = np.cos(angle), np.sin(angle)
    x = v[0] * cos_a - v[2] * sin_a
    z = v[0] * sin_a + v[2] * cos_a
    return (x, v[1], z)


def get_hole_world_position(eq, hole):
    """Мировые координаты отверстия."""
    offset = hole['offset']
    angle = np.radians(eq['rotate_y'])
    cos_a, sin_a = np.cos(angle), np.sin(angle)
    offset_x = offset[0] * cos_a + offset[2] * sin_a
    offset_z = -offset[0] * sin_a + offset[2] * cos_a
    return np.array([
        eq['x'] + offset_x,
        eq['y'] + offset[1],
        eq['z'] + offset_z
    ])


def safe_distance(point1, point2):
    """Безопасное вычисление расстояния между точками."""
    p1 = np.array(point1) if not isinstance(point1, np.ndarray) else point1
    p2 = np.array(point2) if not isinstance(point2, np.ndarray) else point2
    return np.linalg.norm(p1 - p2)


def get_equipment_aabb(eq, margin=0.0):
    """AABB оборудования с отступом margin."""
    hx = eq['width'] / 2.0 + margin
    hy = eq['height'] / 2.0 + margin
    hz = eq['depth'] / 2.0 + margin
    return (
        eq['x'] - hx, eq['y'] - hy, eq['z'] - hz,
        eq['x'] + hx, eq['y'] + hy, eq['z'] + hz,
    )


def check_equipment_collisions(equipments, margin=None):
    """
    Проверяет, не накладываются ли AABB оборудований.
    Возвращает список пар пересекающихся аппаратов.
    """
    if margin is None:
        margin = COLLISION_MARGIN

    collisions = []
    n = len(equipments)

    for i in range(n):
        a_i = get_equipment_aabb(equipments[i], margin)
        for j in range(i + 1, n):
            a_j = get_equipment_aabb(equipments[j], margin)
            if (a_i[0] < a_j[3] and a_i[3] > a_j[0] and
                    a_i[1] < a_j[4] and a_i[4] > a_j[1] and
                    a_i[2] < a_j[5] and a_i[5] > a_j[2]):
                collisions.append((i, j))

    return collisions


def check_pipe_equipment_collisions(path, equipments, exclude_indices=None):
    """
    Проверяет, пересекает ли путь трубы другие оборудования.
    exclude_indices - индексы оборудования, которые нужно исключить (начало/конец трубы).
    """
    if exclude_indices is None:
        exclude_indices = []

    if not path or len(path) < 2:
        return False

    collisions = []

    for i, eq in enumerate(equipments):
        if i in exclude_indices:
            continue

        aabb = get_equipment_aabb(eq, margin=DEFAULT_PIPE_RADIUS)

        # Проверяем каждый сегмент пути
        for j in range(len(path) - 1):
            if _orthogonal_segment_intersects_aabb(path[j], path[j + 1], aabb):
                collisions.append((i, j))

    return collisions


def check_bounds(equipments):
    """
    Проверяет, не выходят ли аппараты за границы пространства.
    Возвращает список индексов аппаратов за границами.
    """
    out_of_bounds = []

    for i, eq in enumerate(equipments):
        aabb = get_equipment_aabb(eq)
        if (aabb[0] < SPACE_BOUNDS['min'] or aabb[3] > SPACE_BOUNDS['max'] or
                aabb[2] < SPACE_BOUNDS['min'] or aabb[5] > SPACE_BOUNDS['max']):
            out_of_bounds.append(i)

    return out_of_bounds


# ══════════════════════════════════════════════════════════════════════
# ПОСТРОЕНИЕ ГРАФА
# ══════════════════════════════════════════════════════════════════════

def get_hole_approach_point(eq, hole, approach_distance=None):
    """
    Создаёт точку подхода к отверстию на заданном расстоянии по нормали.
    Труба должна пройти через эту точку перед входом в отверстие.
    """
    if approach_distance is None:
        approach_distance = MIN_PIPE_SEGMENT * 2

    # Получаем мировые координаты отверстия
    hole_pos = get_hole_world_position(eq, hole)

    # Получаем нормаль отверстия в мировых координатах
    normal = np.array(hole['normal'])
    angle = np.radians(eq['rotate_y'])
    cos_a, sin_a = np.cos(angle), np.sin(angle)

    # Поворачиваем нормаль вместе с оборудованием
    normal_x = normal[0] * cos_a + normal[2] * sin_a
    normal_z = -normal[0] * sin_a + normal[2] * cos_a
    normal_world = np.array([normal_x, normal[1], normal_z])

    # Нормализуем
    norm = np.linalg.norm(normal_world)
    if norm > 1e-9:
        normal_world = normal_world / norm

    # Точка подхода = отверстие + нормаль * расстояние
    approach_point = hole_pos + normal_world * approach_distance

    return approach_point, normal_world


def get_hole_connection_points(eq, hole, radius):
    """
    Создаёт точки для подключения к отверстию с учётом ортогональности.
    Точка подхода всегда выровнена по мировым осям X или Z.
    """
    hole_pos = get_hole_world_position(eq, hole)

    # Получаем нормаль отверстия в мировых координатах
    normal = np.array(hole['normal'])
    angle = np.radians(eq['rotate_y'])
    cos_a, sin_a = np.cos(angle), np.sin(angle)

    # Поворачиваем нормаль вместе с оборудованием
    normal_x = normal[0] * cos_a + normal[2] * sin_a
    normal_z = -normal[0] * sin_a + normal[2] * cos_a
    normal_world = np.array([normal_x, normal[1], normal_z])

    # Нормализуем
    norm = np.linalg.norm(normal_world)
    if norm > 1e-9:
        normal_world = normal_world / norm

    # Определяем, в каком направлении смотрит отверстие по X и Z
    # Нам нужно выровнять точку подхода по доминирующей оси
    abs_x = abs(normal_world[0])
    abs_z = abs(normal_world[2])

    # Создаём ортогональную точку подхода
    if abs_x > abs_z:
        # Отверстие смотрит преимущественно по оси X
        direction = 1 if normal_world[0] > 0 else -1
        approach_point = hole_pos + np.array([direction * radius, 0, 0])
        # Корректируем Z чтобы было строго по оси
        approach_point[2] = hole_pos[2]
    else:
        # Отверстие смотрит преимущественно по оси Z
        direction = 1 if normal_world[2] > 0 else -1
        approach_point = hole_pos + np.array([0, 0, direction * radius])
        # Корректируем X чтобы было строго по оси
        approach_point[0] = hole_pos[0]

    # Всегда сохраняем Y как у отверстия
    approach_point[1] = hole_pos[1]

    return {
        'hole_position': hole_pos,
        'approach_point': approach_point,
        'normal': normal_world
    }


def build_graph(equipments, connections):
    """Строит простой граф, где все соединения идут через точку (0,0)."""
    t_start = time.time()

    # Собираем все радиусы
    radii = set()
    for conn in connections:
        radii.add(conn.get('r', 50.0))

    graphs_by_radius = {}

    for radius in radii:
        # Фильтруем соединения для этого радиуса
        radius_connections = [(i, c) for i, c in enumerate(connections) if c.get('r', 50.0) == radius]

        if not radius_connections:
            continue

        graph_data = _build_graph_for_radius(equipments, radius_connections, radius)
        graphs_by_radius[radius] = graph_data

    logger.info(f"Все графы построены за {time.time() - t_start:.2f}s")
    return graphs_by_radius


def _build_graph_for_radius(equipments, connections_for_radius, radius):
    """
    Упрощённая версия графа для ортогональной трассировки.
    Храним только точки отверстий и подходов.
    """
    logger.info(f"Строим граф для радиуса {radius:.0f} ({len(connections_for_radius)} соединений)")

    nodes = []
    node_metadata = []

    for conn_idx, conn in connections_for_radius:
        for endpoint in ['start', 'end']:
            eq_idx = conn[f'{endpoint}_eq_idx']
            eq = equipments[eq_idx]
            hole = eq['holes'][conn[f'{endpoint}_hole_idx']]

            # Получаем точки подключения
            points = get_hole_connection_points(eq, hole, radius)

            # Добавляем точку отверстия
            hole_idx = len(nodes)
            nodes.append(points['hole_position'])
            node_metadata.append({
                'type': 'hole',
                'conn_idx': conn_idx,
                'endpoint': endpoint,
                'eq_idx': eq_idx
            })

            # Добавляем точку подхода
            approach_idx = len(nodes)
            nodes.append(points['approach_point'])
            node_metadata.append({
                'type': 'approach',
                'conn_idx': conn_idx,
                'endpoint': endpoint,
                'eq_idx': eq_idx
            })

    logger.info(f"  Создано {len(nodes)} узлов для ортогональной трассировки")

    # Граф не нужен для ортогональной трассировки, но оставим для совместимости
    graph = defaultdict(dict)

    return {
        'graph': dict(graph),
        'nodes': nodes,
        'node_metadata': node_metadata,
        'radius': radius,
    }


# ══════════════════════════════════════════════════════════════════════
# ПОИСК ПУТИ
# ══════════════════════════════════════════════════════════════════════

def find_path_on_graph(graph, nodes, start_idx, end_idx):
    """A* поиск пути по взвешенному графу."""
    if start_idx == end_idx:
        return [nodes[start_idx]]

    if start_idx not in graph or end_idx not in graph:
        return None

    def heuristic(i, j):
        return safe_distance(nodes[i], nodes[j])

    counter = 0
    open_set = [(0, counter, start_idx)]
    came_from = {start_idx: None}
    g_score = {start_idx: 0.0}
    visited = set()

    while open_set:
        _, _, current = heapq.heappop(open_set)

        if current in visited:
            continue
        visited.add(current)

        if current == end_idx:
            path = []
            node = current
            while node is not None:
                path.append(nodes[node])
                node = came_from[node]
            path.reverse()
            return path

        for neighbor, weight in graph[current].items():
            if neighbor in visited:
                continue

            tentative_g = g_score[current] + weight

            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score = tentative_g + heuristic(neighbor, end_idx)
                counter += 1
                heapq.heappush(open_set, (f_score, counter, neighbor))

    return None


def simplify_path(path):
    """
    Убирает промежуточные точки на одной прямой.
    Также убирает точки, которые создают возвратные движения.
    """
    if len(path) <= 2:
        return path

    # Первый проход: убираем коллинеарные точки
    simplified = [path[0]]
    for i in range(1, len(path) - 1):
        prev = np.array(simplified[-1])
        curr = np.array(path[i])
        next_pt = np.array(path[i + 1])

        # Проверяем, лежат ли три точки на одной прямой
        v1 = curr - prev
        v2 = next_pt - curr

        # Если обе проекции (X и Z) коллинеарны
        same_x = abs(v1[0]) > 1e-6 and abs(v2[0]) > 1e-6 and abs(v1[2]) < 1e-6 and abs(v2[2]) < 1e-6
        same_z = abs(v1[2]) > 1e-6 and abs(v2[2]) > 1e-6 and abs(v1[0]) < 1e-6 and abs(v2[0]) < 1e-6

        if same_x or same_z:
            # Точка на прямой линии - пропускаем
            continue

        simplified.append(path[i])

    simplified.append(path[-1])

    # Второй проход: убираем возвратные движения (змейки)
    if len(simplified) > 3:
        optimized = [simplified[0]]
        i = 1

        while i < len(simplified) - 1:
            prev = np.array(optimized[-1])
            curr = np.array(simplified[i])
            next_pt = np.array(simplified[i + 1])

            # Проверяем, не делает ли путь зигзаг
            # Если движение идёт в одном направлении, потом в другом, потом снова в первом
            v1 = curr - prev
            v2 = next_pt - curr

            # Определяем направления
            dir1_x = 1 if v1[0] > 1e-6 else (-1 if v1[0] < -1e-6 else 0)
            dir1_z = 1 if v1[2] > 1e-6 else (-1 if v1[2] < -1e-6 else 0)
            dir2_x = 1 if v2[0] > 1e-6 else (-1 if v2[0] < -1e-6 else 0)
            dir2_z = 1 if v2[2] > 1e-6 else (-1 if v2[2] < -1e-6 else 0)

            # Если следующая точка тоже меняет направление обратно - это зигзаг
            if i + 2 < len(simplified):
                next_next = np.array(simplified[i + 2])
                v3 = next_next - next_pt
                dir3_x = 1 if v3[0] > 1e-6 else (-1 if v3[0] < -1e-6 else 0)
                dir3_z = 1 if v3[2] > 1e-6 else (-1 if v3[2] < -1e-6 else 0)

                # Проверяем возвратное движение
                if (dir1_x != 0 and dir2_x == 0 and dir3_x != 0 and dir1_x == -dir3_x and
                        abs(v2[2]) > 1e-6 and abs(v2[2]) < abs(v1[0]) + abs(v3[0])):
                    # Это зигзаг: X, Z, -X - можно сократить, убрав промежуточные точки
                    logger.debug(f"Обнаружен зигзаг X-Z-X, убираем лишние точки")
                    # Пропускаем текущую и следующую точки
                    optimized.append(next_next)
                    i += 3
                    continue

                if (dir1_z != 0 and dir2_x == 0 and dir3_z != 0 and dir1_z == -dir3_z and
                        abs(v2[0]) > 1e-6 and abs(v2[0]) < abs(v1[2]) + abs(v3[2])):
                    # Это зигзаг: Z, X, -Z
                    logger.debug(f"Обнаружен зигзаг Z-X-Z, убираем лишние точки")
                    optimized.append(next_next)
                    i += 3
                    continue

            optimized.append(curr)
            i += 1

        optimized.append(simplified[-1])
        simplified = optimized

    return simplified


def make_orthogonal_path(start_point, end_point, obstacles=None):
    """
    Создаёт строго ортогональный путь по мировым осям.
    Всегда использует A* на сетке для поиска оптимального пути.
    """
    # Всегда используем A* на сетке
    path = _find_path_a_star_grid(start_point, end_point, obstacles)

    if path:
        return path

    # Если A* не нашёл путь (крайний случай), пробуем с очень крупной сеткой
    path = _find_path_a_star_grid(start_point, end_point, obstacles, grid_step=500.0)

    if path:
        return path

    # Если совсем ничего не работает, возвращаем прямой путь с предупреждением
    logger.warning("Не удалось найти ортогональный путь даже с крупной сеткой")
    return [np.array(start_point), np.array(end_point)]


def _make_best_l_path(start, end):
    """Выбирает лучший из двух L-образных путей."""
    path1 = [np.array(start),
             np.array([end[0], start[1], start[2]]),
             np.array(end)]

    path2 = [np.array(start),
             np.array([start[0], start[1], end[2]]),
             np.array(end)]

    len1 = _calculate_path_length(path1)
    len2 = _calculate_path_length(path2)

    return path1 if len1 <= len2 else path2


def _find_path_a_star_grid(start, end, obstacles=None, grid_step=200.0):
    """
    Поиск ортогонального пути через A* на регулярной сетке.
    Все движения только по осям X и Z.
    Гарантирует ортогональность всех сегментов.
    """
    if obstacles is None:
        obstacles = []

    # Определяем границы поиска с хорошим запасом
    margin = max(1000.0, grid_step * 5)

    all_points = [start, end]

    # Добавляем углы препятствий как опорные точки
    for obs in obstacles:
        all_points.extend([
            np.array([obs[0], 0, obs[2]]),
            np.array([obs[0], 0, obs[5]]),
            np.array([obs[3], 0, obs[2]]),
            np.array([obs[3], 0, obs[5]]),
        ])

    min_x = min(p[0] for p in all_points) - margin
    max_x = max(p[0] for p in all_points) + margin
    min_z = min(p[2] for p in all_points) - margin
    max_z = max(p[2] for p in all_points) + margin

    # Округляем до шага сетки
    min_x = np.floor(min_x / grid_step) * grid_step
    min_z = np.floor(min_z / grid_step) * grid_step
    max_x = np.ceil(max_x / grid_step) * grid_step
    max_z = np.ceil(max_z / grid_step) * grid_step

    # Создаём множество заблокированных узлов сетки
    blocked = set()
    for obs in obstacles:
        obs_min_x = np.floor((obs[0] - DEFAULT_PIPE_RADIUS * 2) / grid_step) * grid_step
        obs_max_x = np.ceil((obs[3] + DEFAULT_PIPE_RADIUS * 2) / grid_step) * grid_step
        obs_min_z = np.floor((obs[2] - DEFAULT_PIPE_RADIUS * 2) / grid_step) * grid_step
        obs_max_z = np.ceil((obs[5] + DEFAULT_PIPE_RADIUS * 2) / grid_step) * grid_step

        x = obs_min_x
        while x <= obs_max_x:
            z = obs_min_z
            while z <= obs_max_z:
                blocked.add((round(x, 6), round(z, 6)))
                z += grid_step
            x += grid_step

    # Приводим start и end к ближайшим узлам сетки
    def snap_to_grid(point):
        x = round(np.round(point[0] / grid_step) * grid_step, 6)
        z = round(np.round(point[2] / grid_step) * grid_step, 6)
        return (x, z)

    start_node = snap_to_grid(start)
    end_node = snap_to_grid(end)

    # Если start или end в препятствии, ищем ближайший свободный узел
    if start_node in blocked:
        start_node = _find_nearest_free(start_node, blocked, grid_step,
                                        min_x, max_x, min_z, max_z)
    if end_node in blocked:
        end_node = _find_nearest_free(end_node, blocked, grid_step,
                                      min_x, max_x, min_z, max_z)

    if start_node is None or end_node is None:
        logger.warning("Не удалось найти свободные узлы для start/end")
        return None

    # Специальная эвристика для ортогональных путей
    def heuristic(a, b):
        # Манхэттенское расстояние
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def get_neighbors(node):
        x, z = node
        # Только ортогональные движения (вдоль осей X и Z)
        candidates = [
            (round(x + grid_step, 6), round(z, 6)),
            (round(x - grid_step, 6), round(z, 6)),
            (round(x, 6), round(z + grid_step, 6)),
            (round(x, 6), round(z - grid_step, 6)),
        ]
        return [n for n in candidates
                if n not in blocked
                and min_x <= n[0] <= max_x
                and min_z <= n[1] <= max_z]

    # A* поиск
    open_set = [(0, 0, start_node)]
    came_from = {start_node: None}
    g_score = {start_node: 0.0}
    visited = set()
    counter = 0

    # Ограничение на количество итераций
    max_iterations = 10000
    iterations = 0

    while open_set and iterations < max_iterations:
        iterations += 1
        _, _, current = heapq.heappop(open_set)

        if current in visited:
            continue
        visited.add(current)

        if current == end_node:
            # Восстанавливаем путь
            path = []
            node = current
            while node is not None:
                path.append(np.array([node[0], start[1], node[1]]))
                node = came_from[node]
            path.reverse()

            # Заменяем первую и последнюю точки на точные позиции
            if len(path) > 0:
                path[0] = np.array(start)
            if len(path) > 0:
                path[-1] = np.array(end)

            # Упрощаем путь
            simplified = simplify_path(path)

            # Проверяем ортогональность
            if not _is_path_orthogonal(simplified):
                logger.warning("Путь после упрощения не ортогонален!")
                return path  # возвращаем не упрощённый

            return simplified

        for neighbor in get_neighbors(current):
            if neighbor in visited:
                continue

            tentative_g = g_score[current] + grid_step

            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score = tentative_g + heuristic(neighbor, end_node)
                counter += 1
                heapq.heappush(open_set, (f_score, counter, neighbor))

    if iterations >= max_iterations:
        logger.warning(f"A* превысил лимит итераций ({max_iterations})")

    return None


def _find_nearest_free(node, blocked, grid_step, min_x, max_x, min_z, max_z):
    """Находит ближайший свободный узел сетки в заданных границах."""
    if node not in blocked:
        return node

    # Поиск по расширяющейся спирали
    max_radius = 20  # максимальный радиус поиска в шагах сетки
    for radius in range(1, max_radius + 1):
        # Проверяем квадрат со стороной 2*radius вокруг узла
        for dx in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                # Проверяем только точки на границе квадрата
                if abs(dx) == radius or abs(dz) == radius:
                    candidate_x = round(node[0] + dx * grid_step, 6)
                    candidate_z = round(node[1] + dz * grid_step, 6)

                    # Проверяем границы
                    if not (min_x <= candidate_x <= max_x and min_z <= candidate_z <= max_z):
                        continue

                    candidate = (candidate_x, candidate_z)
                    if candidate not in blocked:
                        return candidate

    return None


def _path_intersects_obstacles(path_points, obstacles):
    """
    Проверяет, пересекает ли ортогональный путь препятствия.
    """
    if not obstacles:
        return False

    for i in range(len(path_points) - 1):
        p1 = path_points[i]
        p2 = path_points[i + 1]

        # Определяем, параллелен ли сегмент оси X или Z
        dx = abs(p2[0] - p1[0])
        dz = abs(p2[2] - p1[2])

        if dx < 1e-6 and dz < 1e-6:
            continue  # точка, не сегмент

        for obs in obstacles:
            if _orthogonal_segment_intersects_aabb(p1, p2, obs):
                return True

    return False


def _orthogonal_segment_intersects_aabb(p1, p2, aabb):
    """
    Проверяет пересечение ортогонального сегмента с AABB.
    Сегмент параллелен либо оси X, либо оси Z.
    """
    min_x, min_y, min_z, max_x, max_y, max_z = aabb

    # Добавляем отступ для трубы
    margin = DEFAULT_PIPE_RADIUS * 1.5
    min_x -= margin
    min_z -= margin
    max_x += margin
    max_z += margin

    # Определяем направление сегмента
    dx = abs(p2[0] - p1[0])
    dz = abs(p2[2] - p1[2])

    if dx < 1e-6:  # Сегмент параллелен оси Z
        x = p1[0]
        z_min = min(p1[2], p2[2])
        z_max = max(p1[2], p2[2])

        return (min_x <= x <= max_x and
                z_min <= max_z and z_max >= min_z)

    elif dz < 1e-6:  # Сегмент параллелен оси X
        z = p1[2]
        x_min = min(p1[0], p2[0])
        x_max = max(p1[0], p2[0])

        return (min_z <= z <= max_z and
                x_min <= max_x and x_max >= min_x)

    return False


def _calculate_path_length(path_points):
    """Вычисляет длину ортогонального пути."""
    length = 0.0
    for i in range(len(path_points) - 1):
        p1 = np.array(path_points[i])
        p2 = np.array(path_points[i + 1])
        length += np.linalg.norm(p2 - p1)
    return length

# ══════════════════════════════════════════════════════════════════════
# ТРАССИРОВКА
# ══════════════════════════════════════════════════════════════════════


def trace_pipe(conn, conn_idx, equipments, graphs_by_radius):
    """Трассирует одно соединение с полностью ортогональными путями."""
    r = conn.get('r', DEFAULT_PIPE_RADIUS)

    # Получаем оборудование и отверстия
    start_eq = equipments[conn['start_eq_idx']]
    end_eq = equipments[conn['end_eq_idx']]
    start_hole_data = start_eq['holes'][conn['start_hole_idx']]
    end_hole_data = end_eq['holes'][conn['end_hole_idx']]

    # Получаем мировые координаты отверстий
    start_hole_pos = get_hole_world_position(start_eq, start_hole_data)
    end_hole_pos = get_hole_world_position(end_eq, end_hole_data)

    # Получаем ортогональные точки подхода
    start_points = get_hole_connection_points(start_eq, start_hole_data, r)
    end_points = get_hole_connection_points(end_eq, end_hole_data, r)

    # Собираем препятствия (все оборудования, кроме start и end)
    obstacles = []
    for i, eq in enumerate(equipments):
        if i != conn['start_eq_idx'] and i != conn['end_eq_idx']:
            aabb = get_equipment_aabb(eq)
            obstacles.append(aabb)

    # Строим ортогональный путь между точками подхода
    middle_path = make_orthogonal_path(
        start_points['approach_point'],
        end_points['approach_point'],
        obstacles
    )

    if middle_path is None:
        logger.warning(f"Не удалось построить путь для соединения {conn_idx}")
        return float('inf'), None

    # Формируем полный путь
    # Начальный сегмент: отверстие -> точка подхода (строго по X или Z)
    full_path = [start_hole_pos, start_points['approach_point']]

    # Добавляем промежуточные точки из middle_path
    # Проверяем, нужно ли включать первую точку middle_path
    if len(middle_path) > 0:
        # Если первая точка middle_path совпадает с точкой подхода, пропускаем её
        first_middle = np.array(middle_path[0])
        approach = np.array(start_points['approach_point'])

        if np.linalg.norm(first_middle - approach) > 1e-6:
            full_path.append(first_middle)

        # Добавляем остальные точки (кроме последней, если она совпадает с конечной точкой подхода)
        if len(middle_path) > 2:
            full_path.extend(middle_path[1:-1])

        # Проверяем последнюю точку
        if len(middle_path) > 1:
            last_middle = np.array(middle_path[-1])
            end_approach = np.array(end_points['approach_point'])

            if np.linalg.norm(last_middle - end_approach) > 1e-6:
                full_path.append(last_middle)

    # Конечный сегмент: точка подхода -> отверстие (строго по X или Z)
    full_path.append(end_points['approach_point'])
    full_path.append(end_hole_pos)

    # Упрощаем путь (уберёт лишние точки на прямых)
    full_path = simplify_path(full_path)

    # Проверяем, что все сегменты ортогональны
    if not _is_path_orthogonal(full_path):
        logger.debug(f"Соединение {conn_idx}: путь не ортогонален - применяем штраф")
        # Пытаемся исправить, делая все сегменты строго ортогональными
        full_path = _force_orthogonal_path(full_path)
        if not _is_path_orthogonal(full_path):
            length = _calculate_path_length(full_path) * 2.0
            return float(length), full_path

    # Проверяем пересечения с препятствиями
    if _path_intersects_obstacles(full_path, obstacles):
        logger.debug(f"Соединение {conn_idx}: пересекает препятствия - большой штраф")
        length = _calculate_path_length(full_path) * 5.0
        return float(length), full_path

    # Всё хорошо - вычисляем нормальную длину
    length = _calculate_path_length(full_path)

    return float(length), full_path


def _force_orthogonal_path(path):
    """
    Принудительно делает все сегменты пути ортогональными.
    Каждый сегмент будет строго параллелен либо X, либо Z.
    """
    if len(path) < 2:
        return path

    orthogonal_path = [np.array(path[0])]

    for i in range(len(path) - 1):
        current = np.array(orthogonal_path[-1])
        target = np.array(path[i + 1])

        dx = target[0] - current[0]
        dz = target[2] - current[2]

        # Определяем, какое движение доминирует
        if abs(dx) > abs(dz):
            # Движение по X, затем по Z
            intermediate = np.array([target[0], current[1], current[2]])

            # Проверяем, не слишком ли короткий сегмент
            if np.linalg.norm(intermediate - current) > 1e-6:
                orthogonal_path.append(intermediate)

            if np.linalg.norm(target - intermediate) > 1e-6:
                orthogonal_path.append(target)
        else:
            # Движение по Z, затем по X
            intermediate = np.array([current[0], current[1], target[2]])

            if np.linalg.norm(intermediate - current) > 1e-6:
                orthogonal_path.append(intermediate)

            if np.linalg.norm(target - intermediate) > 1e-6:
                orthogonal_path.append(target)

    return orthogonal_path

def trace_all_pipes(equipments, connections):
    """Трассирует все соединения."""
    for conn in connections:
        conn['path'] = None
        conn['length'] = 0.0

    graphs_by_radius = build_graph(equipments, connections)

    success_count = 0
    for conn_idx, conn in enumerate(connections):
        length, path = trace_pipe(conn, conn_idx, equipments, graphs_by_radius)
        conn['length'] = length
        conn['path'] = path
        if path is not None:
            success_count += 1

    logger.info(f"trace_all_pipes: {success_count}/{len(connections)} успешно")
    return graphs_by_radius


# ══════════════════════════════════════════════════════════════════════
# ФИТНЕС-ФУНКЦИЯ
# ══════════════════════════════════════════════════════════════════════

def get_total_scheme_volume(equipments):
    if not equipments:
        return 0.0

    xmin = ymin = zmin = float('inf')
    xmax = ymax = zmax = float('-inf')

    for eq in equipments:
        aabb = get_equipment_aabb(eq)
        xmin = min(xmin, aabb[0])
        xmax = max(xmax, aabb[3])
        ymin = min(ymin, aabb[1])
        ymax = max(ymax, aabb[4])
        zmin = min(zmin, aabb[2])
        zmax = max(zmax, aabb[5])

    return max(0.0, xmax - xmin) * max(0.0, ymax - ymin) * max(0.0, zmax - zmin)


def calculate_fitness(equipments, connections):
    """
    Вычисляет фитнес-функцию с учётом коллизий труб и оборудования.
    """
    # Проверка коллизий между оборудованием
    collisions = check_equipment_collisions(equipments)
    if collisions:
        logger.debug(f"Коллизии между аппаратами: {len(collisions)} пар")
        return 10e9, {'error': f'Equipment collisions: {len(collisions)}'}

    # Проверка границ
    out_of_bounds = check_bounds(equipments)
    if out_of_bounds:
        logger.debug(f"Аппараты за границами: {len(out_of_bounds)}")
        return 10e8, {'error': f'Out of bounds: {len(out_of_bounds)}'}

    # Трассировка труб
    trace_all_pipes(equipments, connections)

    # Проверка, все ли трубы построены
    failed_connections = [
        i for i, conn in enumerate(connections)
        if conn.get('path') is None
    ]

    if failed_connections:
        logger.debug(f"Не удалось построить трубы: {len(failed_connections)} соединений")
        return 10e7, {'error': f'Failed connections: {len(failed_connections)}'}

    # Проверка коллизий труб с оборудованием
    pipe_collisions = 0
    for conn_idx, conn in enumerate(connections):
        path = conn.get('path', [])
        if path:
            # Исключаем начальное и конечное оборудование
            exclude = [conn['start_eq_idx'], conn['end_eq_idx']]
            collisions = check_pipe_equipment_collisions(path, equipments, exclude)
            pipe_collisions += len(collisions)

    # Вычисление компонентов фитнеса
    total_pipe_length = sum(conn.get('length', 0) for conn in connections)

    total_pipe_bends = sum(
        max(0, len(conn.get('path', [])) - 2)
        for conn in connections
    )

    scheme_volume = get_total_scheme_volume(equipments)

    # Штраф за удаление от центра
    center_distance = sum(
        eq['x'] ** 2 + eq['z'] ** 2
        for eq in equipments
    ) ** 0.5
    if equipments:
        center_distance /= len(equipments)

    # Штраф за коллизии труб (очень большой)
    pipe_collision_penalty = pipe_collisions * 10000

    # Штраф за не ортогональные пути
    non_orthogonal_penalty = 0
    for conn in connections:
        path = conn.get('path', [])
        if path and not _is_path_orthogonal(path):
            non_orthogonal_penalty += len(path) * 1000

    # Взвешенная сумма
    fitness = (
            FITNESS_WEIGHTS['pipe_length'] * total_pipe_length +
            FITNESS_WEIGHTS['scheme_volume'] * scheme_volume +
            FITNESS_WEIGHTS['pipe_bends'] * total_pipe_bends +
            FITNESS_WEIGHTS['center_distance'] * center_distance +
            pipe_collision_penalty +
            non_orthogonal_penalty
    )

    details = {
        'pipe_length': total_pipe_length,
        'scheme_volume': scheme_volume,
        'pipe_bends': total_pipe_bends,
        'center_distance': center_distance,
        'pipe_collisions': pipe_collisions,
        'non_orthogonal': non_orthogonal_penalty > 0,
        'fitness': fitness
    }

    return fitness, details


def calculate_fitness_from_chromosome(chromosome, template_equipments, connections_data):
    """Обёртка для оптимизатора - возвращает только фитнес."""
    equipments = decode(chromosome, template_equipments)
    fitness, _ = calculate_fitness(equipments, connections_data)
    return fitness


def calculate_fitness_from_chromosome_with_details(chromosome, template_equipments, connections_data):
    """Обёртка для оптимизатора с отладкой - возвращает фитнес и детали."""
    equipments = decode(chromosome, template_equipments)
    return calculate_fitness(equipments, connections_data)


def encode(equipments):
    """Преобразует список аппаратов в хромосому [x1, z1, rot1, x2, z2, rot2, ...]"""
    chromo = []
    for eq in equipments:
        chromo.extend([eq['x'], eq['z'], eq['rotate_y']])
    return chromo


def decode(chromosome, template_equipments):
    """Преобразует хромосому в список аппаратов с центрированием по горизонтальным осям."""
    equipments = []
    n = len(template_equipments)

    for i in range(n):
        eq = template_equipments[i].copy()
        eq['x'] = chromosome[i * 3]
        eq['z'] = chromosome[i * 3 + 1]
        rot = chromosome[i * 3 + 2]
        eq['rotate_y'] = round(rot / 90.0) * 90.0
        equipments.append(eq)

    # Центрирование схемы по X и Z
    if equipments:
        center_x = sum(eq['x'] for eq in equipments) / len(equipments)
        center_z = sum(eq['z'] for eq in equipments) / len(equipments)

        for eq in equipments:
            eq['x'] -= center_x
            eq['z'] -= center_z

    return equipments


def generate_initial_positions(equipments, connections, num_variants=20):
    """
    Генерирует начальные варианты расстановки оборудования.
    Использует эвристики для создания осмысленных начальных позиций.
    """
    n = len(equipments)
    variants = []

    # Вариант 1: Равномерное распределение по окружности
    for _ in range(max(1, num_variants // 4)):
        chromosome = []
        radius = 2000.0
        for i in range(n):
            angle = (2 * np.pi * i / n) + np.random.uniform(-0.5, 0.5)
            x = radius * np.cos(angle) + np.random.uniform(-500, 500)
            z = radius * np.sin(angle) + np.random.uniform(-500, 500)
            rot = np.random.choice([0, 90, 180, 270])
            chromosome.extend([x, z, rot])
        variants.append(chromosome)

    # Вариант 2: Сетка с случайными смещениями
    for _ in range(max(1, num_variants // 4)):
        chromosome = []
        cols = int(np.ceil(np.sqrt(n)))
        spacing = 3000.0
        for i in range(n):
            row = i // cols
            col = i % cols
            x = col * spacing + np.random.uniform(-800, 800)
            z = row * spacing + np.random.uniform(-800, 800)
            rot = np.random.choice([0, 90, 180, 270])
            chromosome.extend([x, z, rot])
        variants.append(chromosome)

    # Вариант 3: Линия с поворотами для минимизации пересечений
    for _ in range(max(1, num_variants // 4)):
        chromosome = []
        for i in range(n):
            x = i * 2500.0 - (n * 1250.0) + np.random.uniform(-500, 500)
            z = np.random.uniform(-1000, 1000)
            # Поворачиваем так, чтобы отверстия смотрели примерно друг на друга
            rot = np.random.choice([0, 90, 180, 270])
            chromosome.extend([x, z, rot])
        variants.append(chromosome)

    # Вариант 4: Компактная группа с учётом связей
    for _ in range(max(1, num_variants // 4)):
        # Строим граф связей
        graph = defaultdict(list)
        for conn in connections:
            graph[conn['start_eq_idx']].append(conn['end_eq_idx'])
            graph[conn['end_eq_idx']].append(conn['start_eq_idx'])

        # Находим компоненты связности и располагаем их близко
        visited = set()
        components = []

        def dfs(node, comp):
            visited.add(node)
            comp.append(node)
            for neighbor in graph[node]:
                if neighbor not in visited:
                    dfs(neighbor, comp)

        for i in range(n):
            if i not in visited:
                comp = []
                dfs(i, comp)
                components.append(comp)

        # Размещаем компоненты
        chromosome = [0] * (n * 3)
        offset_x = 0

        for comp in components:
            comp_size = len(comp)
            for j, eq_idx in enumerate(comp):
                angle = (2 * np.pi * j / max(1, comp_size))
                x = offset_x + 1500 * np.cos(angle) + np.random.uniform(-300, 300)
                z = 1500 * np.sin(angle) + np.random.uniform(-300, 300)
                rot = np.random.choice([0, 90, 180, 270])
                chromosome[eq_idx * 3] = x
                chromosome[eq_idx * 3 + 1] = z
                chromosome[eq_idx * 3 + 2] = rot
            offset_x += 4000

        variants.append(chromosome)

    return variants[:num_variants]


def optimize(equipments, connections):
    """Запуск оптимизации с улучшенными параметрами и инициализацией."""
    n = len(equipments)

    # Создаём целевую функцию с логированием
    iteration_count = [0]
    best_fitness = [float('inf')]
    no_improvement_count = [0]

    def objective_function(x):
        iteration_count[0] += 1
        fitness, details = calculate_fitness_from_chromosome_with_details(x, equipments, connections)

        # Отслеживаем улучшения
        if fitness < best_fitness[0]:
            best_fitness[0] = fitness
            no_improvement_count[0] = 0
        else:
            no_improvement_count[0] += 1

        if iteration_count[0] % 20 == 0:
            if isinstance(details, dict) and 'error' in details:
                logger.info(f"Итерация {iteration_count[0]}, ошибка: {details['error']}, штраф: {fitness:.0f}")
            else:
                logger.info(f"Итерация {iteration_count[0]}, лучший фитнес: {best_fitness[0]:.1f}, "
                            f"текущий: {fitness:.1f}, длина труб: {details.get('pipe_length', 0):.0f}")

        # Ранняя остановка, если долго нет улучшений
        if no_improvement_count[0] > 200:
            logger.info(f"Нет улучшений {no_improvement_count[0]} итераций, принудительная остановка")

        return fitness

    # Генерируем начальные позиции
    initial_population = generate_initial_positions(equipments, connections, num_variants=30)

    # Границы для параметров
    bounds_map = {
        'coord': {
            'min': SPACE_BOUNDS['min'],
            'max': SPACE_BOUNDS['max'],
            'genes': GA_PARAMS['coord_precision']
        },
        'angle': {
            'min': 0.0,
            'max': 360.0,
            'genes': GA_PARAMS['angle_precision']
        }
    }

    x_min = []
    x_max = []
    genes_precision = []

    for _ in range(n):
        x_min.extend([bounds_map['coord']['min'], bounds_map['coord']['min'], bounds_map['angle']['min']])
        x_max.extend([bounds_map['coord']['max'], bounds_map['coord']['max'], bounds_map['angle']['max']])
        genes_precision.extend([
            bounds_map['coord']['genes'],
            bounds_map['coord']['genes'],
            bounds_map['angle']['genes']
        ])

    logger.info(f"Запуск оптимизации: {n} аппаратов, популяция {GA_PARAMS['population_size']}")
    logger.info(f"Сгенерировано {len(initial_population)} начальных вариантов")

    # Оцениваем начальные варианты и выбираем лучшие
    initial_scores = []
    for chrom in initial_population:
        fitness = objective_function(chrom)
        initial_scores.append((fitness, chrom))

    initial_scores.sort(key=lambda x: x[0])
    logger.info(f"Лучший начальный фитнес: {initial_scores[0][0]:.1f}")

    ca = CountriesAlgorithm(
        f=objective_function,
        N=GA_PARAMS['population_size'],
        M=GA_PARAMS['imperialists'],
        n=GA_PARAMS['colonies_range'],
        m=GA_PARAMS['imperialists_range'],
        k=GA_PARAMS['assimilation_rate'],
        l=GA_PARAMS['revolution_rate'],
        ep=GA_PARAMS['exploitation'],
        p=GA_PARAMS['exploration'],
        max_mutation=GA_PARAMS['max_mutation'],
        tmax=GA_PARAMS['max_iterations'],
        genes=genes_precision,
        x_min=x_min,
        x_max=x_max,
        printing=True
    )

    result = ca.start()

    logger.info(f"Оптимизация завершена. Всего итераций: {iteration_count[0]}")
    logger.info(f"Лучший фитнес: {result[1]}")

    return result[0]


def local_refinement(equipments, connections, iterations=100):
    """
    Локальное улучшение с проверкой всех типов коллизий.
    """
    logger.info("Запуск локального улучшения...")

    best_equipments = [eq.copy() for eq in equipments]
    best_fitness, best_details = calculate_fitness(best_equipments, connections)

    improved = True
    iteration = 0
    stuck_count = 0

    while improved and iteration < iterations:
        improved = False
        iteration += 1

        # Если застряли, увеличиваем шаг
        if stuck_count > 10:
            step_multiplier = 3
            stuck_count = 0
        else:
            step_multiplier = 1

        for i in range(len(equipments)):
            if improved:
                break

            # Пробуем сдвиги разного размера
            base_steps = [50, 100, 200, 500]

            for base_step in base_steps:
                if improved:
                    break

                step = base_step * step_multiplier

                for dx, dz in [(step, 0), (-step, 0), (0, step), (0, -step)]:
                    test_equipments = [eq.copy() for eq in best_equipments]
                    test_equipments[i]['x'] += dx
                    test_equipments[i]['z'] += dz

                    fitness, details = calculate_fitness(test_equipments, connections)

                    if fitness < best_fitness:
                        logger.debug(f"Улучшение: +{dx:+d}, +{dz:+d}, фитнес: {best_fitness:.1f} -> {fitness:.1f}")
                        best_fitness = fitness
                        best_details = details
                        best_equipments = test_equipments
                        improved = True
                        stuck_count = 0
                        break

            if improved:
                break

            # Пробуем поворот
            if not improved:
                for rot in [0, 90, 180, 270]:
                    if rot != best_equipments[i]['rotate_y']:
                        test_equipments = [eq.copy() for eq in best_equipments]
                        test_equipments[i]['rotate_y'] = rot

                        fitness, details = calculate_fitness(test_equipments, connections)

                        if fitness < best_fitness:
                            logger.debug(f"Улучшение поворотом: {rot}°, фитнес: {best_fitness:.1f} -> {fitness:.1f}")
                            best_fitness = fitness
                            best_details = details
                            best_equipments = test_equipments
                            improved = True
                            stuck_count = 0
                            break

        if not improved:
            stuck_count += 1

        if iteration % 20 == 0:
            logger.info(f"Локальное улучшение: итерация {iteration}, фитнес: {best_fitness:.1f}, "
                        f"длина труб: {best_details.get('pipe_length', 0):.0f}")

    logger.info(f"Локальное улучшение завершено за {iteration} итераций")
    logger.info(f"Финальный фитнес: {best_fitness:.1f}, длина труб: {best_details.get('pipe_length', 0):.0f}")

    return best_equipments


def load_initial_data(result_id):
    result = Result.objects.prefetch_related(
        Prefetch('result_equipments', queryset=ResultEquipment.objects.prefetch_related('schemes_result_holes'))
    ).get(pk=result_id)

    equipments = []
    equip_id_to_idx = {}
    for eq in result.result_equipments.all():
        holes = list(eq.schemes_result_holes.all())

        equipments.append({
            'id': eq.id,
            'x': eq.x,
            'y': eq.y,
            'z': eq.z,
            'rotate_y': eq.rotate_y,
            'width': eq.width,
            'height': eq.height,
            'depth': eq.depth,
            'holes': [{
                'id': h.id,
                'normal': (h.normal_x, h.normal_y, h.normal_z),
                'offset': (h.offset_x, h.offset_y, h.offset_z),
            } for h in holes]
        })
        equip_id_to_idx[eq.id] = len(equipments) - 1

    connections = []
    for conn in ResultConnection.objects.filter(
            result_equipment_hole_start__result_equipment__result=result
    ).select_related('result_equipment_hole_start', 'result_equipment_hole_end'):
        start_hole_id = conn.result_equipment_hole_start_id
        end_hole_id = conn.result_equipment_hole_end_id
        start_eq_id = conn.result_equipment_hole_start.result_equipment_id
        end_eq_id = conn.result_equipment_hole_end.result_equipment_id
        connections.append({
            'id': conn.id,
            'start_eq_idx': equip_id_to_idx[start_eq_id],
            'start_hole_idx': next(
                i for i, h in enumerate(equipments[equip_id_to_idx[start_eq_id]]['holes']) if h['id'] == start_hole_id),
            'end_eq_idx': equip_id_to_idx[end_eq_id],
            'end_hole_idx': next(
                i for i, h in enumerate(equipments[equip_id_to_idx[end_eq_id]]['holes']) if h['id'] == end_hole_id),
            'r': conn.r,
        })

    return equipments, connections


@transaction.atomic
def save_optimization_result(result_id, best_individual, equipments_data, connections_data):
    result = Result.objects.get(pk=result_id)

    # 1. Применяем хромосому к equipments_data
    for i, eq_data in enumerate(equipments_data):
        eq_data['x'] = best_individual[i * 3]
        eq_data['z'] = best_individual[i * 3 + 1]
        eq_data['rotate_y'] = round(best_individual[i * 3 + 2] / 90.0) * 90.0

    # 2. Центрируем схему
    if equipments_data:
        center_x = sum(eq['x'] for eq in equipments_data) / len(equipments_data)
        center_z = sum(eq['z'] for eq in equipments_data) / len(equipments_data)

        for eq_data in equipments_data:
            eq_data['x'] -= center_x
            eq_data['z'] -= center_z

    # 3. Сохраняем в БД
    for i, eq_data in enumerate(equipments_data):
        eq = ResultEquipment.objects.get(pk=eq_data['id'])
        eq.x = eq_data['x']
        eq.z = eq_data['z']
        eq.rotate_y = eq_data['rotate_y']
        eq.save(update_fields=['x', 'z', 'rotate_y'])

    # 4. Удаляем старые точки соединений
    ResultConnectionPoint.objects.filter(
        connection__result_equipment_hole_start__result_equipment__result=result
    ).delete()

    # 5. Трассируем соединения
    trace_all_pipes(equipments_data, connections_data)

    # Статистика
    total_length = 0
    total_points = 0
    success_count = 0

    for conn_data in connections_data:
        conn = ResultConnection.objects.get(pk=conn_data['id'])
        path = conn_data.get('path', None)

        if not path:
            logger.warning(f"Соединение {conn.id}: путь не найден, используем прямую линию")
            start_eq = equipments_data[conn_data['start_eq_idx']]
            end_eq = equipments_data[conn_data['end_eq_idx']]
            start_hole = start_eq['holes'][conn_data['start_hole_idx']]
            end_hole = end_eq['holes'][conn_data['end_hole_idx']]
            start_pos = get_hole_world_position(start_eq, start_hole)
            end_pos = get_hole_world_position(end_eq, end_hole)
            path = [start_pos, end_pos]
        else:
            success_count += 1

        # Сохраняем точки пути
        for idx, point in enumerate(path):
            ResultConnectionPoint.objects.create(
                connection=conn,
                index=idx,
                x=point[0],
                y=point[1],
                z=point[2]
            )

        # Собираем статистику
        length = conn_data.get('length', 0)
        total_length += length
        total_points += len(path)

    # Логируем итоги
    logger.info("=" * 60)
    logger.info(f"РЕЗУЛЬТАТЫ ОПТИМИЗАЦИИ ДЛЯ result_id={result_id}")
    logger.info(f"Всего соединений: {len(connections_data)}")
    logger.info(f"Успешно построено: {success_count}")
    logger.info(f"Общая длина труб: {total_length:.1f} мм")
    logger.info(f"Средняя длина: {total_length / len(connections_data):.1f} мм" if connections_data else "N/A")
    logger.info(f"Всего точек в путях: {total_points}")
    logger.info(
        f"Среднее точек на соединение: {total_points / len(connections_data):.1f}" if connections_data else "N/A")
    logger.info("=" * 60)

    # Генерируем и логируем отчёт
    report = generate_report(equipments_data, connections_data)
    logger.info("\n" + report)


def quick_validate(equipments, connections):
    """
    Быстрая проверка исходных данных перед оптимизацией.
    """
    logger.info("=" * 60)
    logger.info("ПРОВЕРКА ИСХОДНЫХ ДАННЫХ")
    logger.info(f"Количество оборудования: {len(equipments)}")
    logger.info(f"Количество соединений: {len(connections)}")

    # Проверяем, что все индексы корректны
    max_eq_idx = len(equipments) - 1

    for i, conn in enumerate(connections):
        errors = []

        if conn['start_eq_idx'] > max_eq_idx:
            errors.append(f"start_eq_idx={conn['start_eq_idx']} вне диапазона")
        if conn['end_eq_idx'] > max_eq_idx:
            errors.append(f"end_eq_idx={conn['end_eq_idx']} вне диапазона")

        if errors:
            logger.error(f"Соединение {i}: {', '.join(errors)}")
            continue

        start_eq = equipments[conn['start_eq_idx']]
        end_eq = equipments[conn['end_eq_idx']]

        if conn['start_hole_idx'] >= len(start_eq['holes']):
            logger.error(f"Соединение {i}: start_hole_idx={conn['start_hole_idx']} вне диапазона")

        if conn['end_hole_idx'] >= len(end_eq['holes']):
            logger.error(f"Соединение {i}: end_hole_idx={conn['end_hole_idx']} вне диапазона")

    # Проверяем размеры
    total_volume = sum(
        eq['width'] * eq['height'] * eq['depth']
        for eq in equipments
    )
    logger.info(f"Суммарный объём оборудования: {total_volume:.0f} мм³")

    # Проверяем радиусы труб
    radii = set(conn.get('r', DEFAULT_PIPE_RADIUS) for conn in connections)
    logger.info(f"Используемые радиусы труб: {radii}")

    # Оцениваем сложность
    total_holes = sum(len(eq['holes']) for eq in equipments)
    logger.info(f"Всего отверстий: {total_holes}")
    logger.info(f"Среднее отверстий на аппарат: {total_holes / len(equipments):.1f}" if equipments else "N/A")

    logger.info("=" * 60)


def generate_report(equipments, connections):
    """
    Генерирует подробный отчёт о текущем решении.
    """
    report = []
    report.append("=" * 70)
    report.append("ОТЧЁТ О РАЗМЕЩЕНИИ ОБОРУДОВАНИЯ И ТРАССИРОВКЕ ТРУБ")
    report.append("=" * 70)

    # Общая статистика
    report.append(f"\nВсего оборудования: {len(equipments)}")
    report.append(f"Всего соединений: {len(connections)}")

    # Коллизии
    collisions = check_equipment_collisions(equipments)
    report.append(f"Коллизий между оборудованием: {len(collisions)}")
    if collisions:
        for i, j in collisions:
            report.append(f"  - Аппараты {i} и {j}")

    # Статистика по оборудованию
    report.append("\n" + "-" * 50)
    report.append("ОБОРУДОВАНИЕ:")
    report.append("-" * 50)
    for i, eq in enumerate(equipments):
        report.append(f"Аппарат {i}: X={eq['x']:.0f}, Z={eq['z']:.0f}, "
                      f"поворот={eq['rotate_y']}°, "
                      f"размер={eq['width']:.0f}x{eq['depth']:.0f}x{eq['height']:.0f}")

    # Статистика по соединениям
    report.append("\n" + "-" * 50)
    report.append("СОЕДИНЕНИЯ:")
    report.append("-" * 50)

    total_length = 0
    total_bends = 0
    pipe_collisions_total = 0

    for i, conn in enumerate(connections):
        path = conn.get('path', [])
        length = conn.get('length', 0)
        bends = max(0, len(path) - 2)
        is_orthogonal = _is_path_orthogonal(path) if path else False

        # Проверка коллизий трубы
        exclude = [conn['start_eq_idx'], conn['end_eq_idx']]
        pipe_coll = check_pipe_equipment_collisions(path, equipments, exclude) if path else []

        total_length += length
        total_bends += bends
        pipe_collisions_total += len(pipe_coll)

        status = "OK"
        issues = []
        if not path:
            status = "ОШИБКА"
            issues.append("путь не построен")
        if not is_orthogonal:
            issues.append("не ортогонален")
            status = "ПРЕДУПРЕЖДЕНИЕ"
        if pipe_coll:
            issues.append(f"пересекает {len(pipe_coll)} аппаратов")
            status = "ПРЕДУПРЕЖДЕНИЕ"

        report.append(f"Соединение {i}: {status}")
        report.append(f"  Длина: {length:.0f} мм, изгибов: {bends}, точек: {len(path)}")
        if issues:
            report.append(f"  Проблемы: {', '.join(issues)}")

    report.append("\n" + "-" * 50)
    report.append("ИТОГО:")
    report.append(f"Общая длина труб: {total_length:.0f} мм")
    report.append(f"Средняя длина: {total_length / len(connections):.0f} мм" if connections else "N/A")
    report.append(f"Всего изгибов: {total_bends}")
    report.append(f"Коллизий труб: {pipe_collisions_total}")

    # Объём
    volume = get_total_scheme_volume(equipments)
    report.append(f"Объём схемы: {volume:.0f} мм³")

    report.append("=" * 70)

    return "\n".join(report)


def _perform_optimization(result):
    """Основная функция запуска оптимизации с улучшениями."""
    logger.info(f"Начало оптимизации для result_id={result.pk}")

    # Загружаем данные
    equipments_data, connections_data = load_initial_data(result.pk)

    # Быстрая проверка
    quick_validate(equipments_data, connections_data)

    # Запускаем оптимизацию
    start_time = time.time()
    best_chromosome = optimize(equipments_data, connections_data)
    optimization_time = time.time() - start_time
    logger.info(f"Основная оптимизация заняла {optimization_time:.1f} сек")

    # Применяем хромосому
    best_equipments = decode(best_chromosome, equipments_data)

    # Локальное улучшение
    refined_equipments = local_refinement(best_equipments, connections_data, iterations=50)

    # Кодируем обратно в хромосому
    refined_chromosome = encode(refined_equipments)

    # Сохраняем результат
    save_optimization_result(result.pk, refined_chromosome, equipments_data, connections_data)

    # Финальная статистика
    final_fitness, final_details = calculate_fitness(refined_equipments, connections_data)
    logger.info("=" * 60)
    logger.info("ФИНАЛЬНЫЕ РЕЗУЛЬТАТЫ")
    logger.info(f"Фитнес: {final_fitness:.1f}")
    if isinstance(final_details, dict):
        logger.info(f"Длина труб: {final_details.get('pipe_length', 0):.0f} мм")
        logger.info(f"Объём схемы: {final_details.get('scheme_volume', 0):.0f} мм³")
        logger.info(f"Количество изгибов: {final_details.get('pipe_bends', 0)}")
    logger.info(f"Общее время: {time.time() - start_time + optimization_time:.1f} сек")
    logger.info("=" * 60)

    logger.info("Оптимизация завершена успешно!")


def validate_solution(equipments, connections):
    """
    Проверяет корректность решения и выводит статистику.
    Полезно для отладки.
    """
    print("=" * 60)
    print("ВАЛИДАЦИЯ РЕШЕНИЯ")
    print("=" * 60)

    # Проверка коллизий
    collisions = check_equipment_collisions(equipments)
    print(f"Коллизии между оборудованием: {len(collisions)}")

    # Проверка границ
    out_of_bounds = check_bounds(equipments)
    print(f"Аппараты за границами: {len(out_of_bounds)}")

    # Трассировка
    trace_all_pipes(equipments, connections)

    # Статистика по соединениям
    total_length = 0
    total_bends = 0
    failed = 0

    for i, conn in enumerate(connections):
        if conn.get('path') is None:
            failed += 1
            print(f"  Соединение {i}: НЕ ПОСТРОЕНО")
        else:
            length = conn.get('length', 0)
            bends = max(0, len(conn['path']) - 2)
            total_length += length
            total_bends += bends
            print(f"  Соединение {i}: длина={length:.1f}мм, изгибов={bends}")

    print(f"\nВсего соединений: {len(connections)}")
    print(f"Успешно построено: {len(connections) - failed}")
    print(f"Общая длина труб: {total_length:.1f} мм")
    print(f"Общее количество изгибов: {total_bends}")

    # Объём схемы
    volume = get_total_scheme_volume(equipments)
    print(f"Объём схемы: {volume:.1f} мм³")

    print("=" * 60)

    return {
        'collisions': len(collisions),
        'out_of_bounds': len(out_of_bounds),
        'failed_connections': failed,
        'total_length': total_length,
        'total_bends': total_bends,
        'volume': volume
    }
