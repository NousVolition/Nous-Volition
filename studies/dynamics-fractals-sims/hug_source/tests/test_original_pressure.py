"""Check pressure triggering, enclosure, retained shape, and mirror symmetry."""
from pressure_envelope import PressureEnvelope
import math


def test_holds_closed_below_pressure_limit_without_timer_release():
    model = PressureEnvelope(pressure_limit=2.)
    for pressure in (0., .5, 1., 1.999):
        state = model.step(pressure, 20.)
        assert state['connected']
        assert not state['opening_triggered']
        assert state['Norm'][0] == state['Entropy'][0]
        assert state['Norm'][-1] == state['Entropy'][-1]


def test_pressure_limit_triggers_opening_and_lower_pressure_does_not_reseal():
    model = PressureEnvelope()
    start = model.step(1., 0.)
    assert start['opening_triggered']
    midway = model.step(0., .4)
    final = model.step(0., .4)
    assert 0 < midway['endpoint_gap'] < final['endpoint_gap']
    assert not final['connected']
    assert final['bend'] == 0.
    assert not model.step(0., 20.)['connected']


def test_imprint_remains_after_unloading_and_can_keep_changing():
    model = PressureEnvelope()
    loaded = model.step(.8, 2.)
    released = model.step(0., .2)
    later = model.step(0., 6.)
    assert 0 < later['imprint'] < released['imprint'] < loaded['imprint']
    assert released['eigenvalues'][0] > 1.
    changed = model.step(.9, 1.)
    assert changed['imprint'] > later['imprint']
    assert not changed['opening_triggered']


def test_both_halves_remain_mirrored_through_pressure_and_opening():
    model = PressureEnvelope()
    for pressure, dt in ((.2,.5),(.7,1.),(0.,.5),(1.1,.2),(0.,.8)):
        state = model.step(pressure,dt)
        for left,right in zip(state['Norm'],state['Entropy']):
            assert left[0] == -right[0]
            assert left[1] == right[1]


def test_small_breathing_changes_keep_the_closed_area_constant():
    model = PressureEnvelope()
    widths = []
    for _ in range(90):
        state = model.step(.9,.1)
        sx,sy = state['eigenvalues']
        assert 1.0 <= sx <= 1.06
        assert math.isclose(sx*sy,1.0,abs_tol=1e-15)
        widths.append(sx)
    assert max(widths[-30:])-min(widths[-30:]) > .02
