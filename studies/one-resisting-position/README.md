# One position always fights back

This study explores human coordination through nine **SIMS**—the simulated participants in the model. What happens when one position in their group consistently resists, and how does that position shape everyone else's choices? In the Streams and Rocks metaphor, a fixed position acts like an obstacle around which others adapt.

## Run and reproduce

From the repository root, with Python 3.12 and no third-party dependencies:

```sh
python studies/one-resisting-position/experiment.py --check
```

This reruns all six scenarios, compares every aggregate and assumption with [results.json](results.json), and checks 100 ordinary-C trajectories against the original simulator. Omit `--check` to regenerate `results.json`. The computation may take a little time; each completed scenario prints a result.

## Two meanings of resistance

- **Hold:** the SIM in the chosen seat always keeps its initial color. Other SIMS can agree with it.
- **Oppose:** whenever active, the SIM in the chosen seat takes the opposite of its visible neighbors' majority, holding its current color on a tie. Even if everyone briefly agrees, its next active turn breaks that agreement.

The exception belongs to a seat, not a named individual. Seat numbers start at zero. On a ring every seat has two neighbors and equivalent structural status. In a star, seat 0 is the hub and seats 1–8 are leaves, each seeing only the hub.

## Results

Each scenario follows nine SIMS and uses the same 4,000 randomized starting color patterns. Seed: `20261008`. All rounds have a maximum duration of 120 simulated seconds, including initially unanimous states at time zero.

| Model scenario | Reached consensus at least once | Unanimous at 120 seconds | Mean capped time to first consensus |
| --- | ---: | ---: | ---: |
| Ring, ordinary C | 96.725% | Not measured | 34.338 s |
| Ring, seat 0 holds | 87.450% | Not measured | 48.373 s |
| Star, hub holds | 100.000% | Not measured | 9.479 s |
| Star, leaf holds | 93.625% | Not measured | 35.171 s |
| Ring, ordinary C, no initiative, continued | 97.275% | 97.275% | 33.639 s |
| Ring, one opponent, no other initiative, continued | 85.450% | 5.000% | 54.355 s |

The first four scenarios stop at first consensus. Their zero recorded breaks do **not** establish persistence. The last two continue for the full 120 seconds; 3,378 of the 4,000 opponent rounds included at least one break in unanimity. The 5% endpoint figure is a snapshot, not sustained agreement: unanimity is unstable under the opponent rule. Capped time assigns 120 seconds to non-consensus rounds and is not the mean among successes alone.

For exhaustive enumeration of all 512 binary starts, a frozen follower in hierarchy A reaches consensus in 256/512 starts when a different seat commands its own initial color. A **modified B** with one frozen seat reaches consensus in 110/512 starts by 120 seconds. This seat exception changes B; it is not the original deterministic condition.

## Behavioral assumptions

The Streams and Rocks analogy motivates the local coordination rules specified below.

Ordinary C uses a new random sequential seat order each second. Each SIM is active with probability 0.25. When active, it spontaneously flips with probability 0.02; otherwise it samples a visible neighbor uniformly, proposes copying that color, and refuses a differing proposal with probability 0.15. These probabilities are chosen model assumptions.

The SIM in the holding/opposing seat overrides the ordinary proposal on an active turn. A holding SIM therefore never changes color. Both continued scenarios disable spontaneous initiative for ordinary SIMS, isolating the effect of active opposition under that particular control. Comparing those rows to the first four also changes initiative and stopping rules.

All cases reuse the original main sample's starting states and seed derivation. State-dependent random draws can diverge between policies; shared seeds do not guarantee identical future random opportunities. The follow-up uses homogeneous identities, so permuting names alone cannot create an identity effect. The original schedule includes randomized A/B/C orders and identity mappings; this follow-up has no learning, fatigue, or order carryover and does not model these merely by reading that schedule.

## What it says about leadership

A frozen seat's color wins whenever consensus occurs by construction. That alone is not evidence of persuasion, authority, or leadership. The hub-versus-leaf comparison shows that position changes outcomes under these rules. The ring has no inherently privileged seat. Resistance may shape outcomes without helping the group reach or sustain agreement.

These six cases compare specific mechanisms. The broader study varies behavioral parameters and identity/position assignments. Testing how leadership follows personality, assigned role, network position, or their interaction calls for the volunteer extension below. Hierarchy persistence, copying credits, and individual refusal events would also need separate measurement. Results depend on the chosen activation, refusal, initiative, update timing, and 120-second horizon.

An optional volunteer extension should rotate the same people through the same positions, separately compare resistance assigned to a position with resistance assigned to a person, match starting colors, and randomize round order. Record both first agreement and its duration, along with switches, refusals, and who influences whom. Obtain informed voluntary consent, allow withdrawal without penalty, avoid coercing agreement or stigmatizing a resisting participant, use anonymous participant codes, and follow any applicable institutional review requirements. An assigned resistance role and spontaneous personal resistance answer different questions.

## Files and provenance

- [experiment.py](experiment.py): six follow-up scenarios and reproduction check.
- [base_simulation.py](base_simulation.py): preserved reference simulator for the baseline and deterministic rule.
- [results.json](results.json): saved numerical results and machine-readable assumptions.

Derived from the [decentralized coordination study](https://github.com/NousVolition/My-Sources-Project-ALL/tree/3884b82dac46f36db685a6fc0e363b7c79a9f315/models/decentralized_coordination), which includes the full three-condition design, sensitivity analyses, identity/position comparisons, tests, and volunteer protocol. This folder runs independently. The original stream-function PDF elsewhere in this repository remains a separate physical-model report.
