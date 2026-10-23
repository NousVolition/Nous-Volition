"""Amplitude interventions around pinned, unchanged memory-feedback equations."""
import copy,json
from pathlib import Path
from feedback import Hug,metric,simulate
ROOT=Path(__file__).resolve().parent
def protocol():return json.loads((ROOT/'protocol.json').read_text())
def configured(scale,orbit_policy='scaled'):
    p=copy.deepcopy(protocol())
    if scale<=0 or orbit_policy not in ('scaled','fixed'):raise ValueError('Invalid experiment setting')
    p['mechanics']['active_saturation_N_s_m3']/=scale**2
    p['initial_displacements_scaled']=[scale*x for x in p['initial_displacements_scaled']]
    if orbit_policy=='scaled':p['orbital_force_rms_N']*=scale
    return p
