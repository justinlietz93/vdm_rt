# Accumulated-word 2048 index full-run analysis

Scope: 16 runs, 556 witness events. Each query uses the tick-by-tick accumulated intent word over the complete inter-witness interval, including the current witness trigger.

## Overall top families

| family       |   count |
|:-------------|--------:|
| familiarity  |     198 |
| readiness    |     145 |
| recognition  |      77 |
| commitment   |      38 |
| comparison   |      27 |
| restraint    |      23 |
| novelty      |      17 |
| repair       |      14 |
| separation   |       7 |
| connection   |       5 |
| hesitation   |       3 |
| rejection    |       1 |
| confirmation |       1 |


## Family matrix by branch

| branch                  |   commitment |   comparison |   confirmation |   connection |   familiarity |   hesitation |   novelty |   readiness |   recognition |   rejection |   repair |   restraint |   separation |
|:------------------------|-------------:|-------------:|---------------:|-------------:|--------------:|-------------:|----------:|------------:|--------------:|------------:|---------:|------------:|-------------:|
| category_formation      |           10 |            6 |              0 |            2 |            69 |            0 |        11 |          48 |            61 |           1 |        3 |          11 |            2 |
| cross_domain_mapping    |            0 |            3 |              0 |            2 |            56 |            3 |         4 |          17 |             2 |           0 |        4 |           8 |            0 |
| hierarchy_ordering      |           16 |            0 |              1 |            0 |            27 |            0 |         0 |          21 |             7 |           0 |        7 |           2 |            5 |
| missing_closure_analogy |           12 |           18 |              0 |            1 |            46 |            0 |         2 |          59 |             7 |           0 |        0 |           2 |            0 |


## Margin / coherence notes

|                           |   count |         mean |         std |        min |          5% |         10% |          25% |          50% |          75% |         90% |          95% |           max |
|:--------------------------|--------:|-------------:|------------:|-----------:|------------:|------------:|-------------:|-------------:|-------------:|------------:|-------------:|--------------:|
| rank_margin               |     556 |  0.000891881 |  0.00116873 | 0          | 0.000163913 | 0.000187188 |  0.000230595 |  0.000439763 |  0.000945844 |  0.00237942 |   0.00321613 |    0.00937748 |
| family_margin             |      58 |  0.00457629  |  0.00332915 | 5.0962e-05 | 0.000462696 | 0.00101106  |  0.00229847  |  0.00372365  |  0.00627914  |  0.00881253 |   0.0100029  |    0.0160542  |
| top1_family_count_in_top8 |     556 |  7.67266     |  1.05559    | 1          | 4           | 7           |  8           |  8           |  8           |  8          |   8          |    8          |
| unique_families_top8      |     556 |  1.10791     |  0.321946   | 1          | 1           | 1           |  1           |  1           |  1           |  2          |   2          |    3          |
| rows                      |     556 | 45.2068      | 86.7051     | 1          | 8           | 8           | 10           | 17           | 43.25        | 99          | 171.25       | 1051          |
| score                     |     556 |  0.609524    |  0.106093   | 0.410179   | 0.473627    | 0.492209    |  0.530356    |  0.589263    |  0.670036    |  0.765645   |   0.819469   |    0.922956   |
| cosine                    |     556 |  0.608605    |  0.105901   | 0.410179   | 0.472864    | 0.491801    |  0.530027    |  0.587709    |  0.66959     |  0.761952   |   0.819469   |    0.922956   |


## W4_0088

Output: **I sense I have met this before.**  
Family: `recognition` leaf: `faint_recognition` rows: `28` score: `0.6694` cosine: `0.6694` exact-rank-margin: `0.003258` family-margin: `nan`

Top-k:

|   rank | utterance                               | family      | leaf              |    score |   cosine |   distance |
|-------:|:----------------------------------------|:------------|:------------------|---------:|---------:|-----------:|
|      1 | I sense I have met this before.         | recognition | faint_recognition | 0.669427 | 0.669427 |   0.330573 |
|      2 | I feel this is familiar.                | recognition | faint_recognition | 0.666169 | 0.666169 |   0.333831 |
|      3 | I feel a weak match forming.            | recognition | faint_recognition | 0.665978 | 0.665978 |   0.334022 |
|      4 | I recognize a faint shape here.         | recognition | faint_recognition | 0.665662 | 0.665662 |   0.334338 |
|      5 | I think I sense I have met this before. | recognition | faint_recognition | 0.664858 | 0.664858 |   0.335142 |
|      6 | I think I feel this is familiar.        | recognition | faint_recognition | 0.661656 | 0.661656 |   0.338344 |
|      7 | I think I feel a weak match forming.    | recognition | faint_recognition | 0.661382 | 0.661382 |   0.338618 |
|      8 | I think I recognize a faint shape here. | recognition | faint_recognition | 0.661059 | 0.661059 |   0.338941 |


## Interpretation warning
Exact phrase margins are expected to be small because the index intentionally contains many near-neighbor variants. Family-level margin and top-k family coherence are more useful than raw rank-1 margin.
