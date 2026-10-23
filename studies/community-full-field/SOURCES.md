# Sources and observation limits

* User corpus: *Plain Language Corpus with Mathematical and Logical Clarifications*, supplied as `Plain_Language_Corpus_Math_and_Logic_Corrected.docx`. SHA256 `01f9ab0942f9c88982863e2ffc1e3c495786b5e6b67a26ae77d18235e7058acf`. The unchanged [source metadata](../community-mimesis/corpus_source.json), [exact paragraph excerpts](../community-mimesis/corpus_extract.json), and [audit](../community-mimesis/CORPUS_AUDIT.md) preserve attribution. Paragraph numbers count zero-based body XML paragraphs, including empty paragraphs. We do not redistribute the full attachment.
* Karadzhov, Stafford & Vlachos (2023), *DeliData: A Dataset for Deliberation in Multi-Party Problem Solving*, PACMHCI 7(CSCW2), article 265, [DOI](https://doi.org/10.1145/3610056). [Author-hosted manuscript](https://api.repository.cam.ac.uk/server/api/core/bitstreams/6de14ac6-3604-4651-88d0-69311c9c6b1b/content).
* [Cornell ConvoKit DeliData documentation](https://convokit.cornell.edu/documentation/deli.html), checked 22 October 2026 local time, explicitly says all timestamps are null and the team-performance/state trackers are approximate. We use explicit submissions only. [Archive download](https://zissou.infosci.cornell.edu/convokit/datasets/deli-corpus/deli-corpus.zip), pinned SHA256 `ad24289c4d75593e22fb640fec55186dbb6a10b2cba61d7f854aba04df8c208d`. The original distribution's license applies. Download locally with the earlier study's [download script](../community-mimesis/download_data.py); no raw text, names or archive is included here.

The public derived sequences contain correctness values and hashed group/sequence keys only. Hashes support grouping and reproducibility, not a guarantee of anonymity. Reused animal aliases are scoped to their group. Unobserved initial responses, missing timing and missing intended meanings are not filled with invented data.

## Equation traceability and units

| Source | Implementation | Specification retained |
|---|---|---|
| P229, P549–550 | `Field.terms`, `Field.project` | u_t = -(u·grad)u - grad(p) + nu Lap(u) + f; div(u)=0; p=P/rho |
| P230, P548 | `activation`, `Field.terms` | f=-(sigma/rho)a(q)e; q=abs(grad S)-Gamma; fixed unit direction |
| P261–264 | `activation` | sharp, signed tanh, smooth exact-off are separate laws; no clipping of the tanh tail |
| P517 | `Field.terms` | S_t+u·grad(S)=D Lap(S)+K kappa A |
| P518–519 | `Field.step`, exact integral in `data_test.design` | A'=gamma(U-Ubaseline), A0=0, J=kappa A; no forgetting |
| P545–546 | `Field.diagnostics` | T=mu0(grad(u)+grad(u)^T), with explicitly chosen mu0=mu=rho*nu |

General dimensional bookkeeping: x has length L, t has time T, u has L/T, p has L²/T², nu and D have L²/T; Gamma and epsilon have units S/L. In two spatial dimensions K has L^-2, and kappa*A must have S*L²/T. (sigma/rho)*a(q) must have L/T². For this calculation L=one arbitrary domain length and T=one submission interval. U is the declared 0/1 correctness proxy; gamma fixes the accumulation units. These choices are not SI measurements of people.

The scalar observation M=integral(S) equals a dimensionless 0/1 response **only under the added mapping H** on a unit-area domain. Domain rescaling changes the mapping and coefficient units. A0=0 at the first observed submission is an initialization assumption, not proof of no prior history. The source point, kernel, texture, flow, boundary and stress parameters are declared computational choices. No pressure or velocity fit is attempted.

## Mathematical controls

The exact Taylor–Green benchmark used here follows by substitution: u=V(sin(kx)cos(ky),-cos(kx)sin(ky))*exp(-2*nu*k²*t), p=V²/4*(cos(2kx)+cos(2ky))*exp(-4*nu*k²*t), k=2*pi, with forcing off. The passive scalar check is S=exp(-D*k²*t)*sin(k*(x-c*t)) for uniform velocity (c,0). These are analytically derived verification fixtures, not measured social observations.

With periodic boundaries, integrating the scalar PDE gives M'=kappa*A exactly. Transport and diffusion integrate to zero. Consequently **nu, D, sigma, Gamma, epsilon, h, the force direction and the zero-mean initial texture cannot be estimated from M alone**, even with unlimited precision in M. Only kappa*gamma enters the total, so separating those two also needs additional information. The spatial simulations and their stress/energy/pressure diagnostics test implementation consistency; they do not supply those missing observations.

## Protocol clarification

The frozen protocol's term “Fourier Galerkin” means a spectrally truncated pseudospectral calculation. The 2/3 cutoff removes aliasing from the quadratic advection products; the non-polynomial norm/activation is evaluated on the grid and is **not exactly dealiased by that rule**. Its remaining resolution error is included in grid refinement. The smooth kernel is normalized in the discrete quadrature. It is not a Dirac delta. No equation, split, fitted parameter, primary outcome, or selected pilot was changed after viewing the data results.

After the fixed pilot rule selected two identical four-input histories, a **post-protocol numerical coverage supplement** was added: run every distinct four-input pattern available in eligible training sequences, one sequence per pattern in hash order. This uses no evaluation outcomes, changes no fit, and is reported separately. It tests more input variation; it is not a second held-out comparison.

Verification caught an integer-indexing error in the first grid-comparison helper (floating-point Fourier frequencies were truncated instead of rounded). That comparison was corrected and a regression test added. Integer mode masks were made explicit. Spatial calculations were rerun; reported refinement uses the corrected comparison including fine-only modes. This did not alter the observational fit or any data outcomes.
