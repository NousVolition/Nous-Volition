"""Outcome-independent retrieval and conservative record comparison helpers."""
import hashlib, html, re
from difflib import SequenceMatcher
import numpy as np


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def normalize(text):
    return ' '.join(html.unescape(text or '').split())


def reason_key(text):
    return normalize(text).casefold()


def words(text):
    return re.findall(r'\w+', text.casefold())


def candidate(a, b):
    """No status, target or moderator arguments are accepted."""
    if min(len(a), len(b)) < 30 or min(len(words(a)), len(words(b))) < 5:
        return None
    if a == b:
        return {'kind': 'exact', 'similarity': 1., 'jaccard': 1.}
    if min(len(a), len(b)) / max(len(a), len(b)) < .70:
        return None
    ta, tb = set(words(a)), set(words(b))
    jac = len(ta & tb) / len(ta | tb)
    if jac < .75:
        return None
    matcher = SequenceMatcher(None, a.casefold(), b.casefold(), autojunk=False)
    if matcher.quick_ratio() < .85:
        return None
    ratio = matcher.ratio()
    return {'kind': 'changed', 'similarity': ratio, 'jaccard': jac} if ratio >= .85 else None


def nonoverlap(pairs):
    used = set()
    selected = []
    for pair in sorted(pairs, key=lambda p: (-p['similarity'], p['earlier'], p['later'])):
        if pair['earlier'] in used or pair['later'] in used:
            continue
        used.update((pair['earlier'], pair['later']))
        selected.append(pair)
    return selected


def confusion(pairs):
    counts = {a + '_' + b: 0 for a in ('online', 'deleted') for b in ('online', 'deleted')}
    for p in pairs:
        key = p['earlier_status'] + '_' + p['later_status']
        if key not in counts:
            raise ValueError('Unexpected moderation status')
        counts[key] += 1
    n = len(pairs)
    discordant = counts['online_deleted'] + counts['deleted_online']
    return {'n': n, **counts, 'discordant': discordant,
            'discordant_fraction': discordant / n if n else None}


def window_pairs(pairs, hours):
    return [p for p in pairs if 0 <= p['gap_hours'] <= hours]


def require_audit(pairs, decisions):
    if {p['pair_hash'] for p in pairs} != {d['pair_hash'] for d in decisions}:
        raise ValueError('Audit IDs differ from frozen sample')
    if len(decisions) != len({d['pair_hash'] for d in decisions}):
        raise ValueError('Duplicate semantic judgment')
    for d in decisions:
        if d['verdict'] not in ('pass', 'fail', 'uncertain') or not d['reason']:
            raise ValueError('Invalid semantic judgment')
