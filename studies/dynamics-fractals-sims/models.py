"""Small, explicit numerical models and finite fractal constructions."""
import cmath
import math
from itertools import product


def integrate(rhs, initial, duration, step, method='rk4'):
    if method not in ('euler', 'rk4') or step <= 0 or duration < 0:
        raise ValueError('Choose euler/rk4, a positive step, and nonnegative duration')
    count = round(duration / step)
    if not math.isclose(count * step, duration, abs_tol=1e-12):
        raise ValueError('Duration must be a whole number of steps')
    state = tuple(float(x) for x in initial)
    rows = [(0.0, *state)]
    for tick in range(count):
        t = tick * step
        k1 = rhs(t, state)
        if method == 'euler':
            state = tuple(x + step * k for x, k in zip(state, k1))
        else:
            k2 = rhs(t + step / 2, tuple(x + step * k / 2 for x, k in zip(state, k1)))
            k3 = rhs(t + step / 2, tuple(x + step * k / 2 for x, k in zip(state, k2)))
            k4 = rhs(t + step, tuple(x + step * k for x, k in zip(state, k3)))
            state = tuple(x + step * (a + 2*b + 2*c + d) / 6
                          for x, a, b, c, d in zip(state, k1, k2, k3, k4))
        if not all(math.isfinite(x) for x in state):
            raise ArithmeticError('Nonfinite trajectory; reduce the step or inspect the model')
        rows.append(((tick + 1) * step, *state))
    return rows


def logistic(t, state):
    x, = state
    return (x * (1 - x),)


def logistic_exact(t, x0):
    return x0 / (x0 + (1 - x0) * math.exp(-t))


def lorenz(t, state):
    x, y, z = state
    return (10 * (y-x), x * (28-z) - y, x*y - (8/3)*z)


def pendulum(t, state):
    angle, velocity = state
    return (velocity, -math.sin(angle) - 0.2 * velocity)


def spring(t, state):
    position, velocity = state
    return (velocity, -4 * velocity - position)


def spring_exact(t):
    # m=k=1, b=4, x(0)=1, v(0)=0: two negative real roots.
    slow, fast = -2 + math.sqrt(3), -2 - math.sqrt(3)
    a = -fast / (slow - fast)
    b = slow / (slow - fast)
    return a * math.exp(slow*t) + b * math.exp(fast*t)


def threshold(pump):
    # Chosen dimensionless saturated-growth model inspired by laser onset.
    return lambda t, state: ((pump - 1) * state[0] - state[0]**2,)


def threshold_exact(t, n0, pump):
    gain = pump - 1
    if gain == 0:
        return n0 / (1 + n0*t)
    decay = math.exp(-gain*t)
    return gain*n0 / (n0 + (gain-n0)*decay)


def menger_cells(level):
    if not isinstance(level, int) or not 0 <= level <= 4:
        raise ValueError('Use integer Menger levels 0 through 4')
    cells = [(0, 0, 0)]
    offsets = [p for p in product(range(3), repeat=3) if p.count(1) <= 1]
    for _ in range(level):
        cells = [(3*x+a, 3*y+b, 3*z+c) for x, y, z in cells for a, b, c in offsets]
    return sorted(cells)


def menger_graph(level):
    cells = menger_cells(level)
    index = {point: i for i, point in enumerate(cells)}
    graph = []
    for point in cells:
        neighbors = []
        for axis in range(3):
            for direction in (-1, 1):
                nxt = list(point)
                nxt[axis] += direction
                if tuple(nxt) in index:
                    neighbors.append(index[tuple(nxt)])
        graph.append(tuple(sorted(neighbors)))
    return tuple(graph)


def menger_metrics(level):
    graph = menger_graph(level)
    side = 3**level
    exposed_faces = sum(6-len(row) for row in graph)
    return {'level': level, 'cubes': len(graph), 'volume': len(graph)/side**3,
            'surface_area': exposed_faces/side**2,
            'edges': sum(map(len, graph))//2,
            'dimension_limit': math.log(20)/math.log(3)}


def koch_vertices(level):
    if not isinstance(level, int) or not 0 <= level <= 7:
        raise ValueError('Use integer Koch levels 0 through 7')
    # Counterclockwise unit equilateral triangle; bumps point outward (right).
    vertices = [0j, 1+0j, 0.5 + math.sqrt(3)/2*1j]
    turn = cmath.exp(-1j*math.pi/3)
    for _ in range(level):
        expanded = []
        for a, b in zip(vertices, vertices[1:]+vertices[:1]):
            d = (b-a)/3
            expanded.extend((a, a+d, a+d+d*turn, a+2*d))
        vertices = expanded
    return vertices


def koch_metrics(level):
    vertices = koch_vertices(level)
    pairs = list(zip(vertices, vertices[1:]+vertices[:1]))
    area = abs(sum(a.real*b.imag-b.real*a.imag for a, b in pairs))/2
    return {'level': level, 'segments': len(vertices),
            'perimeter': sum(abs(b-a) for a, b in pairs), 'area': area,
            'dimension_limit': math.log(4)/math.log(3)}


def ring_graph(size):
    if size < 3:
        raise ValueError('A ring needs at least three SIMS')
    return tuple(((i-1) % size, (i+1) % size) for i in range(size))


def koch_graph(level):
    # Contacts follow boundary segments; Euclidean proximity adds no shortcut.
    return ring_graph(len(koch_vertices(level)))
