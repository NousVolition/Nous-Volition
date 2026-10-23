# Movement can restructure expressed history

The previous model kept the spatial calculations fixed while its clay shape moved. This revision uses the physical deformation in both the field's diffusion and the gradient that produces mechanical force. It preserves the event record and all accumulated inputs. The change can be small at small strains; its size is an outcome, not a target to tune.

## Equations supplied by the user

The corrected corpus DOCX has SHA-256 `01f9ab0942f9c88982863e2ffc1e3c495786b5e6b67a26ae77d18235e7058acf`, verified again for this revision. Contents 10, System 2 gives

    partial_t S + u · grad(S) = D laplacian(S) + K_h J
    A' = gamma_source (U - U_baseline), J = kappa A.

Contents 5 and System 3 give the fixed-direction response

    b = -sigma a(|grad(S)| - Gamma) e_x.

We retain the previously selected smooth exact-off law: a(z)=0 for z<=0, and z exp[-(epsilon/z)^2] otherwise. The sharp and signed-tanh alternatives are not combined with this law. Relevant read Miro frames remain [13, proposed shared field/velocity coupling](https://miro.com/app/board/uXjVEXBJz3k=/?moveToWidget=3458764687916065203), [16, persistent accumulation](https://miro.com/app/board/uXjVEXBJz3k=/?moveToWidget=3458764687918055185), and [20, activation alternatives](https://miro.com/app/board/uXjVEXBJz3k=/?moveToWidget=3458764687918055189). The DOCX and board are not modified.

The previous [bounded-expression study](../hug-memory-continuity/METHODS.md) explicitly added capped sources, expression relaxation and upper-only pair exchange at the user's request for a limit. Those extensions remain unchanged:

    j_r = j_max tanh(kappa A_r / j_max)
    source = sum_r w_r K_r j_r
    expression terms = source - lambda S + I_pair.

A is accumulated input, not a complete representation of memory. The separate event catalog preserves origins and routes even if signed inputs cancel in A. All scenarios in this revision retain both. S is a synthetic expressed context field, not a measured neurological quantity or a mass of human memory.

## Movement-to-field feedback: derivation and scope

The existing clay shear map is retained, without an added restructuring gain:

    x = X + gamma(t) Y, y = Y, gamma = d/L
    F = [[1,gamma],[0,1]], det(F)=1
    u = (gamma_dot Y,0), div(u)=0.

Here d is actual mechanical displacement, not the display's magnified displacement. In material coordinates the chain rule gives

    dS_material/dt = partial_t S_spatial + u · grad(S_spatial).

Thus following material points already includes advection. Adding another u·grad(S) to that material derivative would count it twice. What was absent in the previous model was the deformation of the gradient and diffusion operators. For isotropic diffusion D in current spatial coordinates, their pullbacks are

    grad_x S = F^(-T) Grad_X S
    diffusion_material = D Div_X(F^(-1) F^(-T) Grad_X S),

because det(F)=1. This frame choice follows the corpus's spatial diffusion equation. It does not establish a measured diffusion mechanism in clay. [Voges, Duvigneau and Juhre (2022)](https://link.springer.com/article/10.1007/s00161-022-01092-w) explain why reference-frame and current-frame isotropy are distinct assumptions; see also the [COMSOL diffusion-frame documentation](https://doc.comsol.com/6.3/doc/com.comsol.help.sme/sme_ug_theory.06.172.html).

**Explicit reduction:** keep the earlier angular field on a reference ring of radius R=.05 m and its uniform reference-volume quadrature. Only its tangential variation is resolved. Write t0=(-sin(theta),cos(theta)), s0=R theta and Grad_X S approximately t0 S_s0. Project the pullback's diffusion flux onto this angular subspace. The coefficient is

    g(theta,gamma) = t0 · F^(-1) F^(-T) t0
                   = 1 + gamma sin(2 theta) + gamma^2 sin(theta)^2 > 0.
    S_t = D partial_s0(g partial_s0 S) + source - lambda S + I_pair
    |grad_x S| = sqrt(g) |partial_s0 S|.

This is a declared angular projection of the material equation, not a complete two-dimensional Navier–Stokes/clay calculation. Radial redistribution, resolved contact, fracture, hydration and moving sources relative to the clay are absent. The affine shear velocity is supplied by the mechanical mode rather than independently solving the corpus's pressure and momentum field. The reference-ring quadrature is part of the retained reduced model. This limitation cannot be removed by a prettier shape animation.

The unchanged mode's virtual-work force uses the new physical gradient:

    F_memory = -sigma V mean[(Y/L) a(sqrt(g)|S_s0| - Gamma)].

Now d changes g, which changes the distribution of S and its force, which in turn changes d. Sources remain attached to their material labels. Upper-only mirroring remains attached to paired labels; since y=Y, upper and lower physical regions do not swap. Direct pair terms are still exactly zero below the centreline for arbitrary finite local states. Diffusion can still transport influence there.

## What is conserved, and what is allowed to change

The event record is unchanged. For every route, A'=input, with no reset or decay. New events continue to accumulate. Geometric diffusion is a conservative shared-face flux: its contributions sum to zero across the ring. Symmetric paired exchange also sums to zero. Consequently the field's mean still obeys

    mean(S)' = sum_r w_r j_r - lambda mean(S).

Equal source histories therefore give equal means in the updated and previous models, even when their spatial patterns differ. The field mean is not generally constant because sources and the earlier expression-relaxation term remain present. We test persistence of A and conservation by redistribution, not universal conservation of all S values.

Positive g preserves the discrete maximum-principle argument. With the existing incoming weight budget, zero initial S and lambda>0,

    |S| <= (j_max max(K) + |k_pair| s_pair)/lambda.

This is an amplitude bound, not a resolution-independent gradient bound or a proof of human memory capacity. No field clipping is applied.

## Clay and experiment

The inherited baseline is preserved byte for byte as baseline.py, with its hash pinned in protocol.json. Its Burgers strains, inertia, spring, powered feedback, orbit waveform and force scale are unchanged. The five scenarios are:

1. Full movement feedback in diffusion and source-force gradient.
2. Previous fixed spatial calculations, the matched control.
3. Moving diffusion only, an ablation.
4. Moving source-force gradient only, an ablation.
5. Full feedback without the braking intervention.

The two ablations deliberately remove one connection; they are diagnostic controls rather than fully consistent transformations of the spatial equation. Each scenario runs with no orbit, circular forcing and eccentric forcing e=.212, from two mechanical starts: 30 main trajectories. All receive identical fictional source histories. The two starts change displacement only; they are not different family histories. Biological ancestry and adoption statistics do not set any coefficients here.

The active drive is switched off and braking applied at 480–720 s in the first four scenarios. The orbit continues. There are no resets. A separate neighbor account arrives at 950–970 s. Horizon is 1800 s; all switch/event boundaries are integrated explicitly. Period is 5.7 s with matched 6 micronewton RMS, using the previous signed sin(2 true-anomaly)/(r/a)^3 waveform. These are synthetic comparisons, not actual lunar loading.

Main 32-cell paths are repeated at 64 cells and at tighter time tolerances on 32 cells. Both full and fixed calculations, all three conditions and both starts, are checked at 128 cells (12 paths). Spatial convergence of the *paired change* is reported separately from absolute field discretization error, because a small physical effect must not be confused with a coarse-grid error.

Amplitude and mechanical-repeat diagnostics retain the preceding study's definitions: half-range over 57 s; baseline median at 350–450 s; recovery at 80% sustained through 949.5 s. The first eligible amplitude confirmation is 57 s after release. Orbital repetition uses exact orbit checkpoints, one-orbit lag, ten comparisons and scaled tolerance .01. No-orbit movement has no orbital synchronization label. These do not establish asymptotic limit cycles or prove recovery in people.

Mechanical energy is audited against active work, orbital work, current memory-force work, brake loss and Burgers dissipation. The source force can supply or remove mechanical energy; it is not assumed to be damping. A complete thermodynamic model of the abstract field is not claimed.

## Reproduce

Install requirements.txt. Run `python -m unittest -v`. In a new cache root, run `python run.py --kind main --cache CACHE`, then repeat with fine, timefine and spatial. Run `python analyze.py --cache CACHE` and `python render.py`. Saved-result verification is `python verify_saved.py`; player logic checks are `node check_player.cjs`. Run directories refuse overwriting.

The local cache contains full double-precision states for every run. The published data retain full-resolution mechanics/work and selected full-resolution field histories for the primary comparison, with display-field precision explicitly recorded. Refinement summaries identify the checked subsets. No source screenshots, DOCX files, board exports or private family information are published. The GitHub update is a repository update, not website deployment.
