"""Check the requested mirror, connection, timing, and smooth release."""
import math

from hug_envelope import state_at


def test_arms_remain_spatial_mirrors_through_cycle():
    for i in range(81):
        frame = state_at(i/10)
        for left, right in zip(frame['Norm'], frame['Entropy']):
            assert left[0] == -right[0]
            assert left[1] == right[1]


def test_straight_arms_connect_then_disengage_on_schedule():
    for t in (0, 1, 7, 8):
        frame = state_at(t)
        assert len({p[0] for p in frame['Norm']}) == 1
        assert not frame['connected']
    for t in (3, 4, 5):
        frame = state_at(t)
        assert frame['connected']
        assert frame['Norm'][0] == frame['Entropy'][0]
        assert frame['Norm'][-1] == frame['Entropy'][-1]
    assert not state_at(5.01)['connected']
    closing = [state_at(1+i/10)['endpoint_gap'] for i in range(21)]
    opening = [state_at(5+i/10)['endpoint_gap'] for i in range(21)]
    assert all(a >= b for a,b in zip(closing, closing[1:]))
    assert all(a <= b for a,b in zip(opening, opening[1:]))


def test_connected_stretch_preserves_ellipse_area_and_eigendirections():
    for t in (3, 3.25, 3.5, 4, 4.5, 4.75, 5):
        frame = state_at(t)
        sx, sy = frame['eigenvalues']
        assert math.isclose(sx*sy, 1.0, abs_tol=1e-15)
        for half in ('Norm', 'Entropy'):
            for x,y in frame[half]:
                assert math.isclose((x/sx)**2+(y/sy)**2, 1.0, abs_tol=1e-14)
        for vector, value in zip(frame['eigenvectors'], frame['eigenvalues']):
            mapped = [sum(a*b for a,b in zip(row, vector)) for row in frame['stretch_matrix']]
            assert mapped == [value*x for x in vector]
    assert state_at(4)['eigenvalues'][0] > 1.0
    assert state_at(4)['eigenvalues'][1] < 1.0


def test_phase_changes_have_no_position_or_velocity_jump():
    # Endpoint and interior-arm finite differences at all four joins.
    for t in (1, 3, 5, 7):
        h = 1e-4
        before, at, after = [state_at(t+dt)['Norm'] for dt in (-h,0,h)]
        for i in (0, 16, 32, 48, 64):
            for axis in (0,1):
                left = (at[i][axis]-before[i][axis])/h
                right = (after[i][axis]-at[i][axis])/h
                assert abs(left) < 1e-6
                assert abs(right) < 1e-6
