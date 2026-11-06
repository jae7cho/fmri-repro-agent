# Smoothing and filtering: stored records vs the author's labels (diagnostic)

Records: `results/heldout_sf_v1`, read with the current code. Labels: `ground_truth/smoothing_filtering_labels_v1.xlsx`. Counts only; no rates.

## Smoothing

| class | paper | applies_to | label state | record state | state | values |
|---|---|---|---|---|---|---|
| co-adjudicated | agtzidis_2020 | all | reported | no record | | |
| co-adjudicated | binder_1999 | all | not_reported | no record | | |
| co-adjudicated | braun_2015 | all | deferred | no record | | |
| co-adjudicated | chen_2015 | ALFF and fALFF | reported | no record | | |
| co-adjudicated | chen_2015 | ReHo and surface-based graphs | stated_not_performed | no record | | |
| co-adjudicated | ciric_2017 | ICA-AROMA models (input) | reported | no record | | |
| co-adjudicated | ciric_2017 | other compared models | not_reported | no record | | |
| co-adjudicated | cole_2013 | all | reported | no record | | |
| co-adjudicated | derosa_2025 | all | reported | no record | | |
| co-adjudicated | gordon_2014 | all | reported | no record | | |
| co-adjudicated | liu_2013 | all | reported | no record | | |
| co-adjudicated | mueller_2021 | all | reported | no record | | |
| co-adjudicated | oconnor_2017 | all | not_reported | no record | | |
| co-adjudicated | poldrack_2015 | all | reported | no record | | |
| co-adjudicated | power_2014 | all (Parts I–III) | reported | no record | | |
| co-adjudicated | tang_2025 | (withheld) | reported | stream not separable | | |
| co-adjudicated | tang_2025 | (withheld) | not_reported | stream not separable | | |
| co-adjudicated | vanderwal_2016 | all | stated_not_performed | no record | | |
| co-adjudicated | viduarre_2017 | all | deferred | no record | | |
| co-adjudicated | weber_2024 | all | reported | no record | | |
| author-ruled, assistant exposure | liu_2005 | (withheld) | stated_not_performed | stated_not_performed | agree | width: no match; kernel: no match |
| author alone | wheaton_2004 | (withheld) | reported | reported | agree | width: match; kernel: match |

Papers scored on Smoothing: 2

Counts by class and label state (rows):

| class | label state | state agrees | state disagrees | stream not separable | no record |
|---|---|---|---|---|---|
| co-adjudicated | reported | 0 | 0 | 1 | 11 |
| co-adjudicated | not_reported | 0 | 0 | 1 | 3 |
| co-adjudicated | stated_not_performed | 0 | 0 | 0 | 2 |
| co-adjudicated | deferred | 0 | 0 | 0 | 2 |
| author-ruled, assistant exposure | stated_not_performed | 1 | 0 | 0 | 0 |
| author alone | reported | 1 | 0 | 0 | 0 |

## Filtering

| class | paper | applies_to | label state | record state | state | values |
|---|---|---|---|---|---|---|
| co-adjudicated | agtzidis_2020 | all | not_reported | no record | | |
| co-adjudicated | binder_1999 | all | not_reported | no record | | |
| co-adjudicated | braun_2015 | all | deferred | no record | | |
| co-adjudicated | chen_2015 | ReHo and surface-based graphs | reported | no record | | |
| co-adjudicated | chen_2015 | ALFF and fALFF | not_reported | no record | | |
| co-adjudicated | ciric_2017 | all | partially_reported | no record | | |
| co-adjudicated | cole_2013 | all | partially_reported | no record | | |
| co-adjudicated | derosa_2025 | all | reported | no record | | |
| co-adjudicated | gordon_2014 | all | reported | no record | | |
| co-adjudicated | liu_2013 | all | reported | no record | | |
| co-adjudicated | mueller_2021 | all | reported | no record | | |
| co-adjudicated | oconnor_2017 | all | not_reported | no record | | |
| co-adjudicated | poldrack_2015 | all | reported | no record | | |
| co-adjudicated | power_2014 | Parts I–II | reported | no record | | |
| co-adjudicated | power_2014 | Part III | reported | no record | | |
| co-adjudicated | tang_2025 | (withheld) | reported | stream not separable | | |
| co-adjudicated | tang_2025 | (withheld) | reported | stream not separable | | |
| co-adjudicated | vanderwal_2016 | all | reported | no record | | |
| co-adjudicated | viduarre_2017 | all | deferred | no record | | |
| co-adjudicated | weber_2024 | all | reported | no record | | |
| author-ruled, assistant exposure | liu_2005 | (withheld) | reported | unverifiable | disagree | band: no match; pass_type: no match |
| author alone | wheaton_2004 | (withheld) | reported | reported | agree | band: no match; pass_type: match |

Papers scored on Filtering: 2

Counts by class and label state (rows):

| class | label state | state agrees | state disagrees | stream not separable | no record |
|---|---|---|---|---|---|
| co-adjudicated | reported | 0 | 0 | 2 | 10 |
| co-adjudicated | partially_reported | 0 | 0 | 0 | 2 |
| co-adjudicated | not_reported | 0 | 0 | 0 | 4 |
| co-adjudicated | deferred | 0 | 0 | 0 | 2 |
| author-ruled, assistant exposure | reported | 0 | 1 | 0 | 0 |
| author alone | reported | 1 | 0 | 0 | 0 |
