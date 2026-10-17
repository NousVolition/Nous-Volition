"""Water hydrogen-bond topology, in angstroms; no molecular dynamics solver.

Definition: Jedlovszky, Dellago & Sega (2025), doi:10.1063/5.0272802,
Methods, using the descriptor introduced by Foffi & Sciortino.
psi_i is the minimum O--O distance to any molecule whose SHORTEST
hydrogen-bond path from i has exactly four edges. Graphs are undirected.
"""
from collections import deque
from pathlib import Path
import argparse
import json
import numpy as np


def coordinates(value, shape_tail):
    a = np.asarray(value, dtype=float)
    if a.ndim != 1 + len(shape_tail) or a.shape[1:] != shape_tail:
        raise ValueError(f"Expected N x {shape_tail} coordinates")
    if not len(a) or not np.isfinite(a).all():
        raise ValueError("Coordinates must be nonempty and finite")
    return a


def boundary(box_A=None, pbc=(False, False, False)):
    flags = np.asarray(pbc)
    if flags.shape != (3,) or flags.dtype != np.dtype(bool):
        raise ValueError("pbc must contain three booleans")
    if box_A is None:
        if flags.any():
            raise ValueError("Periodic directions need orthorhombic box lengths")
        return np.ones(3), flags
    box = np.asarray(box_A, dtype=float)
    if box.shape != (3,) or not np.isfinite(box).all() or (box <= 0).any():
        raise ValueError("box_A must be three positive lengths; triclinic boxes unsupported")
    return box, flags


def minimum_image(delta, box_A=None, pbc=(False, False, False)):
    box, flags = boundary(box_A, pbc)
    d = np.asarray(delta, dtype=float).copy()
    d[..., flags] -= box[flags] * np.rint(d[..., flags] / box[flags])
    return d


def hydrogen_bonds(oxygen_A, hydrogen_A, box_A=None,
                   pbc=(False, False, False), oo_cutoff_A=3.5, oh_cutoff_A=2.5):
    """Undirected pairs; accept O--O <3.5 AND donor-H--acceptor-O <2.5 A.

    Either donor direction suffices. No angular criterion is added. Explicit
    molecular membership is required: hydrogen_A[i] holds water i's two Hs.
    O(N^2) distance work; intended for reference/small snapshot analysis.
    """
    o = coordinates(oxygen_A, (3,))
    h = coordinates(hydrogen_A, (2, 3))
    if len(o) != len(h):
        raise ValueError("Every oxygen needs its own pair of hydrogens")
    for cutoff in (oo_cutoff_A, oh_cutoff_A):
        if not np.isfinite(cutoff) or cutoff <= 0:
            raise ValueError("Cutoffs must be finite and positive")
    box, flags = boundary(box_A, pbc)
    if flags.any() and (box[flags] <= 2 * oo_cutoff_A).any():
        raise ValueError("Periodic box lengths must exceed twice the O--O cutoff")
    edges = set()
    for donor in range(len(o)):
        do = minimum_image(o - o[donor], box, flags)
        candidates = np.flatnonzero(np.sum(do * do, axis=1) < oo_cutoff_A ** 2)
        candidates = candidates[candidates != donor]
        dh = minimum_image(o[candidates, None, :] - h[donor], box, flags)
        bonded = np.any(np.sum(dh * dh, axis=2) < oh_cutoff_A ** 2, axis=1)
        for acceptor in candidates[bonded]:
            edges.add(tuple(sorted((donor, int(acceptor)))))
    return sorted(edges)


def adjacency(n, edges):
    graph = [set() for _ in range(n)]
    for edge in edges:
        if len(edge) != 2:
            raise ValueError("Each edge must contain two molecule indices")
        i, j = edge
        if any(isinstance(k, (bool, np.bool_)) or not isinstance(k, (int, np.integer))
               or k < 0 or k >= n for k in (i, j)) or i == j:
            raise ValueError("Edges need distinct in-range integer indices")
        graph[i].add(j)
        graph[j].add(i)
    return graph


def fourth_shell(graph, start):
    """BFS = unweighted shortest paths, not a four-step walk enumeration."""
    distances = {start: 0}
    queue = deque([start])
    while queue:
        i = queue.popleft()
        if distances[i] == 4:
            continue
        for j in graph[i]:
            if j not in distances:
                distances[j] = distances[i] + 1
                queue.append(j)
    return sorted(j for j, distance in distances.items() if distance == 4)


def classify(oxygen_A, edges, box_A=None, pbc=(False, False, False), threshold_A=5.0):
    o = coordinates(oxygen_A, (3,))
    boundary(box_A, pbc)
    if not np.isfinite(threshold_A) or threshold_A <= 0:
        raise ValueError("Threshold must be finite and positive")
    graph = adjacency(len(o), edges)
    records = []
    for i in range(len(o)):
        shell = fourth_shell(graph, i)
        psi, neighbor = None, None
        if shell:
            d = minimum_image(o[shell] - o[i], box_A, pbc)
            distances = np.linalg.norm(d, axis=1)
            winner = int(np.argmin(distances))
            psi, neighbor = float(distances[winner]), shell[winner]
        label = "unclassified" if psi is None else ("HDL-like" if psi < threshold_A else "LDL-like")
        records.append(dict(molecule=i, psi_A=psi, label=label,
                            fourth_shell_count=len(shell), closest_fourth_neighbor=neighbor))
    return records


def layer_summary(records, layers=None):
    if layers is None:
        layers = ["all"] * len(records)
    if len(layers) != len(records) or any(not isinstance(x, str) or not x for x in layers):
        raise ValueError("layers must supply one nonempty string per molecule")
    result = {}
    for layer in sorted(set(layers)):
        rows = [r for r, name in zip(records, layers) if name == layer]
        n = len(rows)
        nh = sum(r["label"] == "HDL-like" for r in rows)
        nl = sum(r["label"] == "LDL-like" for r in rows)
        nc = nh + nl
        result[layer] = dict(molecules=n, classified=nc, unclassified=n-nc,
                             coverage=nc/n, HDL_like=nh, LDL_like=nl,
                             HDL_fraction_of_classified=nh/nc if nc else None)
    return result


def analyze_snapshot(data):
    if data.get("units") != "angstrom":
        raise ValueError("Declare units='angstrom'; convert nm to A explicitly")
    box, pbc = data.get("box_A"), data.get("pbc", [False]*3)
    settings = data.get("settings", {})
    allowed = {"oo_cutoff_A", "oh_cutoff_A", "threshold_A"}
    if set(settings) - allowed:
        raise ValueError("Unknown setting")
    oo, oh, threshold = (settings.get(k, default) for k, default in
                         (("oo_cutoff_A", 3.5), ("oh_cutoff_A", 2.5), ("threshold_A", 5.0)))
    edges = hydrogen_bonds(data["oxygen_A"], data["hydrogen_A"], box, pbc, oo, oh)
    records = classify(data["oxygen_A"], edges, box, pbc, threshold)
    return dict(method_doi="10.1063/5.0272802", units="angstrom",
                input_description=data.get("description", "user-supplied snapshot"),
                settings=dict(oo_cutoff_A=oo, oh_cutoff_A=oh, threshold_A=threshold),
                box_A=box, pbc=pbc, hydrogen_bonds=edges, molecules=records,
                layers=layer_summary(records, data.get("layers")),
                layer_note="External labels only; graph constructed before layer aggregation. ITIM not implemented.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = analyze_snapshot(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Analyzed {len(result['molecules'])} molecules; {len(result['hydrogen_bonds'])} bonds")
