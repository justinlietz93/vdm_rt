# Selector trace probe schedule

Seed: 424242

Ticks 0-999: base_stable only.
Ticks 1000-1399: weighted probe mixture:

- base_repeat 40%
- paraphrase_same 15%
- symbolic_inversion 15%
- concrete_unrelated 15%
- social_affective 15%

The model receives only the `text` field. `kind`, `phase`, and `input_id` are outside-model logging metadata.
