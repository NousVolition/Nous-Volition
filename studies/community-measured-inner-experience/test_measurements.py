import csv,json,unittest
from pathlib import Path
from analyze import paired,holm
P=Path(__file__).resolve().parent

class Measurements(unittest.TestCase):
    def test_missing_is_not_zero(self):
        data=[{'VISQ_Dialogic_RUM':r,'VISQ_Dialogic_DIS':d} for r,d in [(4,2),(6,3),(3,2),(None,12)]]
        out=paired(data,'Dialogic');self.assertEqual(out['n_pairs'],3);self.assertEqual(out['mean_difference'],2)
        self.assertEqual(out['positive'],3)

    def test_condition_reversal_changes_sign(self):
        pairs=[(4,2),(6,3),(3,2)]
        a=paired([{'VISQ_Dialogic_RUM':x,'VISQ_Dialogic_DIS':y} for x,y in pairs],'Dialogic')
        b=paired([{'VISQ_Dialogic_RUM':y,'VISQ_Dialogic_DIS':x} for x,y in pairs],'Dialogic')
        self.assertEqual(a['mean_difference'],-b['mean_difference'])
        self.assertAlmostEqual(a['p_paired_t'],b['p_paired_t'])

    def test_holm_known_family(self):
        rows=[{'p_paired_t':p} for p in [.04,.001,.03]];holm(rows)
        self.assertEqual([r['p_holm_five'] for r in rows],[.06,.003,.06])

    def test_sample_join_and_denominators(self):
        a=json.loads((P/'results/measurement_audit.json').read_text())
        c=a['labrie'];self.assertEqual(c['participants']+c['nonparticipant_rows'],c['subject_rows'])
        self.assertEqual(c['joined_response_rows']+c['unmatched_response_rows'],c['responses'])
        self.assertEqual(c['joined_valid_responses'],3108);self.assertEqual(c['unmatched_valid_rows'],0)
        self.assertEqual(c['duplicate_order_keys'],0);self.assertEqual(c['item_timestamp_columns'],[])
        self.assertEqual(c['state_mean_recalculation_max_error'],0)
        self.assertEqual(a['moffatt']['fractional_sum_flagged_people'],1)

    def test_saved_comparison_accounting(self):
        with (P/'results/paired_visq.csv').open(encoding='utf-8') as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),10)
        for r in rows:
            self.assertEqual(sum(int(r[k]) for k in ['positive','tied','negative']),int(r['n_pairs']))
            self.assertAlmostEqual(float(r['rumination_mean'])-float(r['distraction_mean']),float(r['mean_difference']),places=12)
            self.assertGreaterEqual(float(r['p_holm_five']),float(r['p_paired_t']))

    def test_no_substitute_model_claim(self):
        r=json.loads((P/'results/run_status.json').read_text())
        for k in ['full_field_empirical_runs','simpler_predictive_models_fitted','synthetic_field_runs','imputed_by_this_analysis','individual_histories_fabricated']:self.assertEqual(r[k],0)
        self.assertIn('Not run',r['full_model_status'])
        m=json.loads((P/'measurement_map.json').read_text(encoding='utf-8'))
        self.assertEqual(len(m),12);self.assertTrue(all(x['needed'] for x in m))

if __name__=='__main__':unittest.main()
