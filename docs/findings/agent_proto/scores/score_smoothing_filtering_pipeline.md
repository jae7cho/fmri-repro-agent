# Smoothing and filtering: stored records vs the author's labels (diagnostic)

Records: `results/corpus_full_v2_labelled19`, read with the current code. Labels: `ground_truth/smoothing_filtering_labels_v1.xlsx`. Counts only; no rates.

## Smoothing

| class | paper | applies_to | label state | record state | state | values |
|---|---|---|---|---|---|---|
| co-adjudicated | agtzidis_2020 | all | reported | reported | agree | width: agree; kernel: agree |
| co-adjudicated | binder_1999 | all | not_reported | reported | disagree | width: not labelled; kernel: not labelled |
| co-adjudicated | braun_2015 | all | deferred | not_reported | disagree | width: not labelled; kernel: not labelled |
| co-adjudicated | chen_2015 | ALFF and fALFF | reported | stream not separable | | |
| co-adjudicated | chen_2015 | ReHo and surface-based graphs | stated_not_performed | stream not separable | | |
| co-adjudicated | ciric_2017 | ICA-AROMA models (input) | reported | stream not separable | | |
| co-adjudicated | ciric_2017 | other compared models | not_reported | stream not separable | | |
| co-adjudicated | cole_2013 | all | reported | reported | agree | width: agree; kernel: not labelled |
| co-adjudicated | derosa_2025 | all | reported | reported | agree | width: agree; kernel: agree |
| co-adjudicated | gordon_2014 | all | reported | reported | agree | width: agree; kernel: agree |
| co-adjudicated | liu_2013 | all | reported | reported | agree | width: agree; kernel: agree |
| co-adjudicated | mueller_2021 | all | reported | reported | agree | width: agree; kernel: agree |
| co-adjudicated | oconnor_2017 | all | not_reported | not_reported | agree | width: not labelled; kernel: not labelled |
| co-adjudicated | poldrack_2015 | all | reported | reported | agree | width: record has no value (label sigma); kernel: agree |
| co-adjudicated | power_2014 | all (Parts I–III) | reported | reported | agree | width: agree; kernel: agree |
| co-adjudicated | tang_2025 | (withheld) | reported | stream not separable | | |
| co-adjudicated | tang_2025 | (withheld) | not_reported | stream not separable | | |
| co-adjudicated | vanderwal_2016 | all | stated_not_performed | stated_not_performed | agree | width: not labelled; kernel: not labelled |
| co-adjudicated | viduarre_2017 | all | deferred | not_reported | disagree | width: not labelled; kernel: not labelled |
| co-adjudicated | weber_2024 | all | reported | reported | agree | width: agree; kernel: agree |
| author-ruled, assistant exposure | liu_2005 | (withheld) | stated_not_performed | stated_not_performed | agree | width: no match; kernel: no match |
| author alone | wheaton_2004 | (withheld) | reported | reported | agree | width: match; kernel: match |

Papers scored on Smoothing: 16

Counts by class and label state (rows):

| class | label state | state agrees | state disagrees | stream not separable | no record |
|---|---|---|---|---|---|
| co-adjudicated | reported | 9 | 0 | 3 | 0 |
| co-adjudicated | not_reported | 1 | 1 | 2 | 0 |
| co-adjudicated | stated_not_performed | 1 | 0 | 1 | 0 |
| co-adjudicated | deferred | 0 | 2 | 0 | 0 |
| author-ruled, assistant exposure | stated_not_performed | 1 | 0 | 0 | 0 |
| author alone | reported | 1 | 0 | 0 | 0 |

## Filtering

| class | paper | applies_to | label state | record state | state | values |
|---|---|---|---|---|---|---|
| co-adjudicated | agtzidis_2020 | all | not_reported | not_reported | agree | band: not labelled; pass_type: not labelled |
| co-adjudicated | binder_1999 | all | not_reported | not_reported | agree | band: not labelled; pass_type: not labelled |
| co-adjudicated | braun_2015 | all | deferred | not_reported | disagree | band: not labelled; pass_type: not labelled |
| co-adjudicated | chen_2015 | ReHo and surface-based graphs | reported | stream not separable | | |
| co-adjudicated | chen_2015 | ALFF and fALFF | not_reported | stream not separable | | |
| co-adjudicated | ciric_2017 | all | partially_reported | reported | disagree | band: not labelled; pass_type: agree |
| co-adjudicated | cole_2013 | all | partially_reported | stated_not_performed | disagree | band: not labelled; pass_type: label not comparable as stated |
| co-adjudicated | derosa_2025 | all | reported | reported | agree | band: record has no value (label in s); pass_type: agree |
| co-adjudicated | gordon_2014 | all | reported | reported | agree | band: agree; pass_type: agree |
| co-adjudicated | liu_2013 | all | reported | reported | agree | band: agree; pass_type: agree |
| co-adjudicated | mueller_2021 | all | reported | reported | agree | band: agree; pass_type: label not comparable as stated |
| co-adjudicated | oconnor_2017 | all | not_reported | not_reported | agree | band: not labelled; pass_type: not labelled |
| co-adjudicated | poldrack_2015 | all | reported | reported | agree | band: agree; pass_type: agree |
| co-adjudicated | power_2014 | Parts I–II | reported | stream not separable | | |
| co-adjudicated | power_2014 | Part III | reported | stream not separable | | |
| co-adjudicated | tang_2025 | (withheld) | reported | stream not separable | | |
| co-adjudicated | tang_2025 | (withheld) | reported | stream not separable | | |
| co-adjudicated | vanderwal_2016 | all | reported | reported | agree | band: agree; pass_type: agree |
| co-adjudicated | viduarre_2017 | all | deferred | not_reported | disagree | band: not labelled; pass_type: not labelled |
| co-adjudicated | weber_2024 | all | reported | reported | agree | band: agree; pass_type: agree |
| author-ruled, assistant exposure | liu_2005 | (withheld) | reported | unverifiable | disagree | band: no match; pass_type: no match |
| author alone | wheaton_2004 | (withheld) | reported | reported | agree | band: no match; pass_type: match |

Papers scored on Filtering: 16

Counts by class and label state (rows):

| class | label state | state agrees | state disagrees | stream not separable | no record |
|---|---|---|---|---|---|
| co-adjudicated | reported | 7 | 0 | 5 | 0 |
| co-adjudicated | partially_reported | 0 | 2 | 0 | 0 |
| co-adjudicated | not_reported | 3 | 0 | 1 | 0 |
| co-adjudicated | deferred | 0 | 2 | 0 | 0 |
| author-ruled, assistant exposure | reported | 0 | 1 | 0 | 0 |
| author alone | reported | 1 | 0 | 0 | 0 |
