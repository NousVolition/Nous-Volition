"""Recheck the interpretation of the peroxide audit; do not refit the rate.

The conditional restart uses a value read from the same figure as its initial
condition. It is a diagnostic, not independent validation or a new kinetic law.
"""
from pathlib import Path
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parent
k = 0.009  # min^-1, aqueous pH 3 row, Akhtar et al. Table 1
table_from_zero = {str(t): 100 * (-math.expm1(-k*t)) for t in (5, 30)}
restart_at_5 = 100 * (1 - (1 - 0.45)*math.exp(-k*(30-5)))
assert abs(table_from_zero['5'] - 4.4002518166900035) < 1e-12
assert abs(table_from_zero['30'] - 23.662050566314676) < 1e-12
result = {
    'review_date': '2026-10-15',
    'source': 'https://jcsp.org.pk/ArticleUpload/4144-20045-1-CE.pdf',
    'location': 'printed page 265, Table 1 and Figure 4; conditions on page 264',
    'rate_per_minute': k,
    'original_figure_readings_percent': {'5': 45, '30': 55},
    'reading_tolerance_percentage_points': 5,
    'reading_tolerance_is_measurement_uncertainty': False,
    'standard_first_order_from_time_zero_percent': table_from_zero,
    'diagnostic_restart': {
        'initial_time_min': 5,
        'initial_decomposition_percent_from_figure': 45,
        'predicted_decomposition_percent_at_30_min': restart_at_5,
        'within_original_30_min_reading_band': abs(restart_at_5-55) <= 5,
        'rate_changed': False,
        'independent_validation': False,
        'meaning': 'A rapid early stage followed by slower loss is one possible explanation. '
                   'This calculation does not establish that mechanism; its starting value '
                   'comes from the same figure. Raw data and the authors\' fit interval are needed.'
    },
    'conclusion': 'The tabulated rate alone does not reproduce Figure 4 when applied '
                  'as a single first-order decay starting with zero decomposition at time zero. '
                  'The cause of that mismatch is unresolved; it is not proof that the paper is wrong.',
    'historical_numerical_results_changed': False,
    'source_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
}
(ROOT/'results/peroxide_recheck.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result, indent=2))
