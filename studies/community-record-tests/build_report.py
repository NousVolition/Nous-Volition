"""Render the completed public-record study from its saved, inspectable results."""
from pathlib import Path
import csv, html, json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).parent
RES = ROOT / 'results'
FIG = ROOT / 'figures'
FIG.mkdir(exist_ok=True)
w = json.loads((RES / 'wording_results.json').read_text())
h = json.loads((RES / 'history_results.json').read_text())
selection = json.loads((RES / 'wording_selection.json').read_text())
audit = json.loads((RES / 'semantic_audit.json').read_text())
statuses = {r['pair_hash']: r for r in csv.DictReader((RES / 'audited_status_pairs.csv').read_text().splitlines())}
groups = w['groups']
plt.rcParams.update({'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False,
                     'savefig.facecolor': '#faf9f5', 'figure.facecolor': '#faf9f5', 'axes.facecolor': '#faf9f5'})

fig, axs = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)
axs[0].bar(['Preserved', 'Changed', 'Uncertain'], [8, 21, 11], color=['#287d8e', '#d78243', '#8d9498'])
axs[0].set(ylabel='Pairs reviewed', ylim=(0, 24), title='Meaning review, with statuses hidden')
for i, v in enumerate([8, 21, 11]): axs[0].text(i, v+.5, str(v), ha='center')
names = ['pass_lexical', 'pass_typography', 'exact_all']
labels = ['Different words\n(n=5)', 'Typography only\n(n=3)', 'Identical text control\n(n=353)']
values = [groups[k]['status_pairs'] for k in names]
fractions = [100*v['discordant_fraction'] for v in values]
axs[1].bar(labels, fractions, color=['#287d8e', '#65a8ad', '#aab0b0'])
for i, (v, y) in enumerate(zip(values, fractions)):
    axs[1].text(i, y+2, f"{v['discordant']}/{v['n']}", ha='center')
axs[1].set(ylim=(0, 70), ylabel='Pairs with different recorded statuses (%)', title='Decision differences also occur without edits')
fig.suptitle('Selected repeated posts: descriptive comparisons, not a causal wording effect', fontsize=13)
fig.savefig(FIG / 'wording.png', dpi=160); plt.close(fig)

fig, axs = plt.subplots(1, 2, figsize=(11, 4.6), constrained_layout=True)
keys = ['all', 'same_reason', 'same_moderator', 'both_controls']
labels = ['All finite pairs', 'Same reason', 'Same moderator', 'Both controls']
for i, (key, label) in enumerate(zip(keys, labels)):
    r = h['analysis']['180d_' + key]
    left = 0
    for col, color in [('longer', '#287d8e'), ('equal', '#aab0b0'), ('shorter', '#d78243')]:
        width = 100 * r[col] / r['n']
        axs[0].barh(i, width, left=left, color=color, label=col.capitalize() if i == 0 else None)
        left += width
    axs[0].text(101, i, f"{r['longer']:,}/{r['n']:,}", va='center', fontsize=10)
    ci = 2**np.asarray(r['median_log2_ratio_ci95']); center = r['median_ratio']
    axs[1].errorbar(center, i, xerr=np.array([[center-ci[0]], [ci[1]-center]]), fmt='o', color='#287d8e', capsize=4)
    axs[1].text(4.55, i, f'{center:.2g}× [{ci[0]:.2g}, {ci[1]:.2g}]', va='center', fontsize=10)
axs[0].set(yticks=range(4), yticklabels=labels, xlim=(0, 131), xticks=range(0, 101, 20), xlabel='Accounts (%) — comparison of assigned durations', title='Longer second penalties'); axs[0].invert_yaxis()
axs[0].legend(loc='lower left', bbox_to_anchor=(0, -.28), ncol=3, fontsize=9)
axs[1].set(yticks=range(4), yticklabels=[], xlim=(0.5, 6.7), xlabel='Median paired duration ratio (second / first)', title='Paired bootstrap 95% intervals'); axs[1].invert_yaxis()
axs[1].axvline(1, color='#888', linestyle='--', linewidth=1)
fig.suptitle('Wikipedia: assigned block lengths; matching reasons do not establish identical conduct', fontsize=13)
fig.savefig(FIG / 'penalties.png', dpi=160); plt.close(fig)

def table(headers, rows):
    return '<div class="scroll"><table><thead><tr>' + ''.join('<th>'+html.escape(str(v))+'</th>' for v in headers) + '</tr></thead><tbody>' + ''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in row)+'</tr>' for row in rows) + '</tbody></table></div>'

status_labels = {'pass': 'Preserved meaning (all)', 'pass_lexical': 'Preserved: different words', 'pass_typography': 'Preserved: typography', 'fail': 'Changed meaning', 'uncertain': 'Uncertain meaning', 'exact_all': 'All identical-text controls', 'exact_sample': '40-control hash sample'}
status_rows = []
for key, label in status_labels.items():
    r = groups[key]['status_pairs']
    status_rows.append([label, r['n'], r['online_online'], r['online_deleted'], r['deleted_online'], r['deleted_deleted'], f"{r['discordant']}/{r['n']}"])
history_rows = []
for key, label in zip(keys, labels):
    r = h['analysis']['180d_' + key]; ci = 2**np.asarray(r['median_log2_ratio_ci95'])
    history_rows.append([label, r['n'], f"{r['longer']}/{r['n']} ({100*r['longer']/r['n']:.1f}%)", r['equal'], r['shorter'], f"{r['first_median_hours']:g} → {r['second_median_hours']:g}", f"{r['median_ratio']:.2g} [{ci[0]:.2g}, {ci[1]:.2g}]"])
sensitivity_rows = []
for days in (30, 90, 180):
    r = h['analysis'][f'{days}d_both_controls']
    sensitivity_rows.append([f'{days} days', r['n'], f"{r['longer']}/{r['n']} ({100*r['longer']/r['n']:.1f}%)", f"{r['median_ratio']:.2g}×"])
audit_rows = [[d['pair_hash'][:12], d['verdict'], d['change_type'].replace('_', ' '), statuses[d['pair_hash']]['earlier_status']+' / '+statuses[d['pair_hash']]['later_status'], f"{60*float(statuses[d['pair_hash']]['gap_hours']):.2f}", d['reason']] for d in audit]
claim_rows = [
    ['Meaning → expression', 'Eight pairs judged equivalent before outcomes; five changed words.', 'Single assistant review; independent German-speaking reviewers and fuller conversational context.'],
    ['Expression → treatment', 'Three of eight equivalent pairs differ in status; two of five lexical pairs.', 'A wording-caused effect is not identified. Exact duplicates also differ; decision reasons and timing are absent.'],
    ['Context → treatment', 'Author, article and parent matched; 24-hour window tightened in sensitivity checks.', 'Moderator, reports, duplication policy and full intervening conversation are not held fixed.'],
    ['Treatment → later treatment', '517/591 second penalties longer with identical reason strings and same moderator.', 'Prior punishment causing later severity remains unproven; current conduct and selection can differ.'],
    ['Memory in the community model', 'Escalation is a real sequence-level pattern compatible with institutional history.', 'No fitted social-memory update, visibility intervention or causal memory estimate. Water/Fog/Smoke/Clay remain situational metaphors.']]

body = '''<header><p class="eyebrow">STREAMS AND ROCKS · PUBLIC RECORDS · 22 OCTOBER 2026</p><h1>Meaning, moderation<br>and repeated penalties</h1><p class="lead">Real records show different decisions for some messages judged to preserve meaning, and longer penalties at later blocks. The comparisons also show why these patterns do not yet isolate the cause.</p></header>
<nav><a href="#wording">Wording</a><a href="#history">Penalties</a><a href="#audit">All 40 judgments</a><a href="#connections">Community connections</a><a href="README.md">Methods & reproduction</a></nav>
<div class="cards"><article><b>3 / 8</b><p>Meaning-preserving pairs with different recorded statuses</p></article><article><b>193 / 353</b><p>Identical-text pairs with different statuses</p></article><article><b>517 / 591</b><p>Longer second penalties with the same recorded reason and moderator</p></article></div>
<section id="wording"><h2>Which wording pairs keep the message?</h2><p>We screened 1,011,773 DER STANDARD forum posts in the OFAI One Million Posts Corpus. Repeated posts were paired only within the same author, article and parent, at most 24 hours apart; newspaper staff were excluded. Of 520 disjoint changed-text candidates, 40 were chosen by a fixed hash order without consulting moderation status.</p><p>A single assistant reviewed the German headline, body, article title and available parent. <strong>8 passed, 21 changed meaning, and 11 remained uncertain.</strong> Equivalence required preservation of the target, proposition, stance, negation, quantities, accusations and pragmatic force. Removing an insult or demand counted as a substantive change. Five passes changed words or syntax; three changed only typography.</p><p>The judgments were saved and hash-locked before reading statuses. This was outcome-blind review of the stored status fields; some texts themselves mention censorship or reposting. It is not independent human validation of meaning.</p><img src="figures/wording.png" alt="Forty reviewed pairs: eight preserved, twenty-one changed, eleven uncertain. Two of five lexical pairs and one of three typographic pairs differed in status; so did 193 of 353 identical-text controls.">
<h3>Recorded decisions</h3><p>Online/deleted are the corpus's actual recorded post statuses, not researcher offensiveness labels. Columns below follow <strong>earlier-created post / later-created post</strong>. They are two posts, not before-and-after statuses of one post.</p>'''
body += table(['Group', 'Pairs', 'Online / online', 'Online / deleted', 'Deleted / online', 'Deleted / deleted', 'Different'], status_rows)
body += '''<p>One lexical contrast added an indefinite article before an unpaid role: the earlier post was online and the later one deleted. Another exchanged two expressions of complete agreement while retaining the substantive argument: the earlier post was deleted and the later one online. These cases support a narrow observation of decision differences, conditional on the semantic review.</p><p><strong>The identical-text control prevents a wording-only explanation.</strong> Its 193 differences include 179 online/deleted and 14 deleted/online pairs. Duplicate-post moderation is one possible explanation, but the source does not record deletion reasons. Neither unequal outcomes nor this directional pattern alone establishes bias, injustice or a particular policy.</p><p>Tightening the creation-time gap retains 3 differences among 7 meaning-preserving pairs within one hour, and 2 among 4 within ten minutes. The corresponding exact controls are 146/253 and 91/152. The eight accepted pairs come from eight authors and eight articles. Both non-top-level accepted pairs have their parent available; all eight article records are available. The whole evolving conversation and moderator exposure are not fixed.</p></section>
<section id="history"><h2>Are later penalties more severe?</h2><p>The public Cornell Wikipedia block log yields 57,600 eligible accounts with a finite first observed block and complete 180-day follow-up. Of 18,784 distinct second blocks in that window, 10,097 initially assigned an indefinite duration; 8,687 finite pairs enter the duration comparison. These are initial assigned lengths, not time actually served. Modifications to an active block are not counted as separate encounters.</p><p>This extends the previously reported 8,687-pair analysis with exact nonempty reason-string matching. Normalization only decodes HTML, collapses whitespace and ignores case; dates, evidence, links and other content remain. The same-moderator comparison excludes missing moderator identities.</p><img src="figures/penalties.png" alt="Second assigned blocks are longer in most cases across all, same-reason, same-moderator and both-control groups. The both-control group has 517 of 591 longer and median ratio 3.5, with bootstrap interval 3 to 4.29.">'''
body += table(['180-day group', 'Pairs', 'Longer second', 'Equal', 'Shorter', 'Median hours: first → second', 'Median paired ratio [95% CI]'], history_rows)
body += '''<p>In the strictest group, <strong>87.5% had a longer second penalty</strong>, and the median account-level ratio was <strong>3.5× [3.0, 4.29]</strong>. Its separate first/second medians are 31 and 168 hours; their ratio is not the median paired ratio. An exact sign test excluding 37 ties gives p = 2.51 × 10<sup>−109</sup>. That tests directional symmetry in this selected cohort, not whether prior punishment caused escalation. First and second log-durations correlate (Spearman ρ = 0.573). Accounts contribute one pair; the bootstrap resamples whole accounts 2,000 times with a fixed seed. It does not model dependence through shared moderators.</p><h3>Shorter follow-up-gap checks</h3><p>All windows use the same complete-180-day-follow-up cohort. Below: same reason and same moderator.</p>'''
body += table(['Gap from end of first block', 'Finite pairs', 'Longer second', 'Median ratio'], sensitivity_rows)
body += '''<p><strong>Escalation is supported; a causal memory mechanism remains open.</strong> Equal reason text does not guarantee equal conduct or severity. These records condition on being blocked again, omit unpenalized encounters and do not manipulate whether history is visible. Current behavior, policy, reporting and selection can contribute. No social-memory parameter is fitted from this association.</p></section>
<section id="connections"><h2>What this adds to the community model</h2>'''
body += table(['Connection', 'Supported observation', 'Still needs testing'], claim_rows)
body += '''<p>People can be Water, Fog, Smoke or Clay in different situations, combine these descriptions or reject them. Preserve strong descriptions of force, resistance, exclusion and adaptation when they describe the observation or an attributed account. The public-record results add evidence about treatment; they do not turn these metaphors into fixed types of people.</p></section>
<section id="audit"><h2>The complete meaning audit</h2><p>Every verdict below was frozen before the recorded status fields were joined. Passes are provisional single-reviewer judgments. Full pair hashes and reasons are in <a href="results/semantic_audit.json">semantic_audit.json</a>; <a href="inspect_pair.py">inspect_pair.py</a> retrieves the original text from a local source download. We publish no account names, source post IDs or raw comment text.</p>'''
body += table(['Pair hash prefix', 'Verdict', 'Change type', 'Earlier / later status', 'Gap (minutes)', 'Reason'], audit_rows)
body += '''</section><section><h2>Reproduce and inspect</h2><p><a href="README.md">Full methods and commands</a> · <a href="PROTOCOL.md">Frozen exploratory protocol</a> · <a href="results/wording_results.json">Wording results</a> · <a href="results/history_results.json">Penalty results</a> · <a href="results/verification.json">189 result checks</a> · <a href="results/run_checks.json">Unit-test run</a> · <a href="DATA_LICENSE.md">Data provenance and reuse</a></p><p>Completed: 23 unit tests; all 12 paired-duration summaries and 24 status tables reproduced from published count data; outcome-independent retrieval rerun reproduced the identical frozen sample. The original Wikipedia log and OFAI SQLite database were hash-verified. The semantic judgment itself is a documented review, not an automatically validated measurement.</p><p>Protocol dates: 21 October local date; review completed 22 October. This was an exploratory extension, not an externally registered confirmatory study. Earlier results informed the questions. Exact-text controls were mechanically checked for text and context-key identity, rather than receiving a separate human referent review; this is a narrower implementation of the planned exact-control audit.</p><p>Sources: <a href="https://ofai.github.io/million-post-corpus/">Schabus, Skowron & Trapp, One Million Posts (SIGIR 2017)</a>; <a href="https://github.com/OFAI/million-post-corpus/blob/master/database_schema.md">source schema</a>; <a href="https://convokit.cornell.edu/datasets.html">Cornell ConvoKit datasets</a>; <a href="https://arxiv.org/abs/1902.08628">Chang & Danescu-Niculescu-Mizil, Trajectories of Blocked Community Members (2019)</a>. The analyses and limitations here are our own.</p></section>'''
style = '''body{margin:0;background:#faf9f5;color:#26343a;font:17px/1.6 system-ui,sans-serif}main{max-width:1120px;margin:auto;padding:48px 28px}header{max-width:900px}.eyebrow{font-size:13px;letter-spacing:.12em;color:#567079}h1{font-size:clamp(36px,5vw,64px);line-height:1.08;margin:18px 0 24px}h2{font-size:30px;line-height:1.2;margin:0 0 20px}h3{font-size:21px}.lead{font-size:21px}nav{display:flex;flex-wrap:wrap;gap:20px;border-top:1px solid #cad2cf;border-bottom:1px solid #cad2cf;padding:18px 0;margin:30px 0}a{color:#176476}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.cards article{background:#e8efed;padding:22px;border-radius:6px}.cards b{font-size:36px;color:#1d6677}.cards p{margin-bottom:0}section{margin-top:54px}img{width:100%;height:auto;margin:16px 0}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;font-size:14px;margin:20px 0}td,th{text-align:left;vertical-align:top;border-bottom:1px solid #cdd5d1;padding:11px}th{background:#e6eeeb}tbody tr:nth-child(even){background:#f0f2ed}#audit td:last-child{min-width:320px}#audit td:first-child{font-family:monospace}@media(max-width:650px){main{padding:24px 16px}.cards{grid-template-columns:1fr}h2{font-size:26px}}'''
(ROOT / 'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Meaning, moderation and repeated penalties — Streams and Rocks</title><style>'+style+'</style><main>'+body+'</main></html>', encoding='utf-8')
print('Built report.html and two scientific figures from saved results.')


# Preserve the source-chain audit when this historical report is rebuilt.
from audit_note import apply_notice
apply_notice(Path(__file__).resolve().parent)
