# Using the topology slides to test SIMS

The slides are used as specifications for executable checks and model controls. The package contains the resulting code, measurements, and original figures.

Run `python -m unittest -v`, then `python topology.py --check`. The latter reproduces the algebraic checks and 2,560 additional SIMS runs. Remove `--check` to regenerate `topology_results.json`. `python build_report.py` includes two new scientific figures in the local report. Core calculations use the Python standard library; figure dependencies remain in `requirements.txt`.

## Three behavioral tests

**Aggregation can hide disagreement and alter the apparent dynamics.** Divide a six-vertex path into consecutive blocks of three. The block map onto a two-vertex path is a connected epimorphism. Compare states `001001` and `010010`, where 1 is orange. Each has one orange SIM per block and therefore the same block-majority colors `00`. Neither full state is unanimous. Conditional on one active seat being chosen uniformly, copying a uniformly chosen neighbor with refusal probability 0.15, the expected changes in the blocks' orange counts are respectively `(-17/240, 0)` and `(17/240, 17/240)`. The exact rational calculation is checked independently by enumerating update outcomes. Equal block counts therefore do not suffice to determine the next-step law. A coarse group model needs additional state or a justified closure rule. This one-update diagnostic is distinguished from the full round's shuffled asynchronous schedule.

**Filling faces is behaviorally invisible to the current pairwise rule.** The nine-SIM construction uses triangles `(0,1,2)`, `(2,3,4)`, `(4,5,6)`, and `(6,7,8)`. One complex has only their edges; the other includes their filled faces. Both yield the same nine-vertex, twelve-edge contact graph. Over Z₂, their first Betti numbers are 4 and 0. Despite that topological difference, every recorded SIMS outcome is identical in all 320 matched pairs. This is a control that tests which information the behavioral rule reads. It does not establish that group interactions never matter; a group-sensitive rule has not been specified here.

**Adding contacts can help ordinary coordination and strengthen disruption.** Taking the transitive closure of the connected 20-vertex Menger contact relation yields a complete graph: links increase from 24 to 190. This deliberate contact intervention raises ordinary first agreement from 72.66% to 92.97% in the main sample. When the corner seat opposes its neighbors' majority, first agreement falls from 39.84% to 3.13%; unanimity at 120 seconds is 1.17% versus 0%. These are consequences of the copying/opposition rules under changed contacts. The closure operation does not construct the Menger prespace.

## SIMS experiment settings

There are eight scenarios: Menger and complete contacts each with ordinary behavior, corner opposition, and edge opposition; plus wireframe and filled-triangle complexes with ordinary behavior. Each scenario has 256 main rounds and 64 rounds with spontaneous initiative probability 0.02, totaling 2,560 runs. Seed: `20261010`. All rounds last 120 seconds. Activation probability is 0.25 per SIM per second; refusal probability for a differing copy proposal is 0.15. Self-loops used in the topology definitions are removed from SIMS contacts.

Within population size, conditions share randomized starting colors, randomized identity labels, and the existing fixed-draw opportunity schedule. Condition order is randomized within each block. Opponent positions are seat 0 (a Menger corner) and seat 1 (a Menger edge); the complete-graph comparisons use those same indices. Complete-graph seats all have degree 19, so “corner” and “edge” there identify the matched indices, not distinct structural roles. Ordinary identities remain behaviorally homogeneous; renaming identities preserves the seat-level outcome exactly.

Saved outcomes include first agreement, endpoint agreement, capped time, switches, refusals, agreement breaks, and direct copying credits by position. The run continues after first agreement. Wilson intervals describe finite simulation sampling. Paired comparisons subtract Menger from complete outcomes, or wireframe from filled outcomes, using matching blocks; normal intervals are approximate and can be poor for rare events in the 64-block sensitivity sample. The total number of runs includes both members of the exact-equality control; they are not independent observations. Nine-SIM and twenty-SIM rates are not treated as a controlled cross-size comparison.

This is a new sample, not a replacement for the earlier 10,240 runs. The report contains 12,800 total SIMS runs across the two experiments. Small differences between complete-graph seat indices reflect sampling, not identity or positional leadership. Direct copying credits measure local copying, not authority or persistence of a social hierarchy.

An exact symmetry check tests every permutation of the three cube axes and every combination of axis reflections: 48 coordinate symmetries preserve the Menger face-contact graph. Their position orbits are the eight degree-3 corners and twelve degree-2 edge seats. Degrees prevent any graph automorphism from mixing these types. Thus this finite model has two structural position types even though identity labels do not affect decisions. Infinite-space homogeneity does not imply that this finite contact graph has interchangeable positions.

## Source distinctions

[Panagiotopoulos and Solecki, *A combinatorial model for the Menger curve*, version 3](https://arxiv.org/html/1803.02516v3) defines reflexive symmetric graphs and uses connected epimorphisms: edges and vertices are covered, and inverse images of connected sets are connected. The prespace is an infinite generic inverse limit; its transitive relation yields the Menger curve as a quotient. Its lifting statement requires the specified locally non-separating, saturated subset. Finite tests do not certify these infinite hypotheses. “Connected” for its topological graphs is graph-relative, not ordinary connectedness of their underlying zero-dimensional spaces.

[Friedman, *An elementary illustrated introduction to simplicial sets*, version 8](https://arxiv.org/abs/0809.4221v8) provides the simplicial and geometric-realization background. Our examples below are explicitly chosen finite representations and coordinate checks. We use the nerve and cubical relations displayed in the supplied slides; the maximum connection is selected by the slide's zero-insertion identity. The final geometric picture has no vertex/face table, so our triangle complex is a reproducible test example, not an asserted reconstruction of that picture.

## What is actually checked

| Construction | Executable check | Deliberate failure/control |
| --- | --- | --- |
| Graph projection | Edge preservation; surjectivity on vertices and edges; connected fibers | A path mapped onto a triangle covers vertices but misses an edge; a folded path has a disconnected fiber |
| Menger parent maps | Integer-coordinate division maps levels 2→1→0; every level-1 fiber has 20 connected vertices | Adjacency at level 1 has a nontransitive triple |
| Finite inverse prefix | All 400 finest-stage vertices give compatible three-stage tuples | No claim of genericity or universality from three levels |
| Lifting square | Pullback projections commute and are connected epimorphisms | A smaller source cannot lift surjectively; a compatible prescribed value can obstruct a finite lift |
| Simplicial identities | All five identity families in the standard 2-simplex, input degrees 0–6 | Degree bounds are stated; finite enumeration is not a general theorem proof |
| Gluing/collapse | Exact rational barycentric evaluations agree across a face insertion or merged repeated vertex | Invalid weights or indices are rejected |
| Category nerve | Chain faces compose adjacent arrows; degeneracies insert identity; all simplicial identities through degree 5 | Endpoint faces drop the endpoint arrow rather than composing a nonexistent pair |
| Cubical maps | Insert a 0/1, delete a coordinate, or take max of adjacent coordinates; supplied identities on a rational grid through input dimension 4 | Minimum fails the supplied zero-insertion identity |
| Homology | Boundary squared is zero; Z₂ ranks recover known triangle and tetrahedron examples | Same graph, different filled faces yields different homology but unchanged pairwise behavior |

The finite graph lift uses `A=P₂`, `B=P₃`, `C=P₃`, with `g=(0,0,1)` and `f=(0,1,1)`. Compatible pairs `(b,c)` form the four-vertex refinement `D`. Its projections are `pB=(0,1,2,2)` and `pC=(0,0,1,2)`, and `g∘pB=f∘pC`. There is no connected-epimorphism lift directly from C, but D permits the displayed lift with its two endpoint values fixed. Fixing `h(1)=0` instead is compatible with the projected value and still prevents a finite lift. These examples distinguish finite extension searches from the stronger theorem for the generic limit.

Forcing transitivity of the connected finite Menger relation yields a complete relation. Quotienting it gives one equivalence class, not a finite reconstruction of the intended Menger quotient. The saved nontransitive triple and this one-class outcome make that failure explicit.

For the standard simplicial set Δ², an n-simplex is a weakly increasing sequence of n+1 entries from `{0,1,2}`. Deleting an entry gives a face; repeating an entry gives a degeneracy. All five identity families are enumerated, giving 7,932 equalities. Barycentric face insertion adds a zero coordinate; collapse adds two adjacent weights. For example, `(0,0.4,0.6)` in a triangle agrees with `(0.4,0.6)` on its face, while repeating vertex 1 with weights `(0.2,0.3,0.5)` collapses to weights `(0.2,0.8)` on an edge. Fractions make these equality tests exact.

The nerve example is a one-object category whose three morphisms compose by addition modulo 3, with identity 0. Its k-simplices are k-arrow chains. Internal face maps add two adjacent entries modulo 3; endpoint faces remove the first or last arrow. Degeneracy inserts 0. There are 24,600 checked simplicial equalities through degree 5. A further test verifies that doubling morphism labels modulo 3 commutes with faces and degeneracies. The category is defined independently of the SIMS contact graphs.

Cubical coordinate tests use `δᵃᵢ` to insert a coordinate `a∈{0,1}`, `sᵢ` to delete one coordinate, and `γᵢ` to replace adjacent coordinates by their maximum. The relations in the slide, plus associativity and insertion/projection cancellation, pass 6,524 checks on the exact grid `{0,1/3,1}` through input dimension 4. Zero-based code indices replace the slide's one-based coordinate labels consistently. Cubical coordinate deletion differs from simplicial barycentric merging; the two operations are tested separately. These coordinate maps induce contravariant operations on cubical-set data.

In total, 39,056 bounded algebraic equalities are checked, alongside graph, homology, and behavioral tests. The full package now has 83 unit tests. The tests provide concrete evidence about these implementations and selected constructions. They do not establish the infinite extension, homogeneity, or universality claims by numerical sampling.
