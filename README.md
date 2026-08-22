# Tenant Renewal Prediction

Predicting whether an apartment tenant renews their lease, from a real (anonymized) mid-size
property's leasing data — and, more importantly, a record of everything that went wrong on the way
to a trustworthy answer: an overfit model, two separate data-leakage bugs, and a name-matching bug
that silently undercounted a specific group of tenants.

**[Try the live widget](widget/renewal_widget.html)** — open it directly in a browser, no server or
install needed. Enter a hypothetical tenant's lease, unit, payment, and maintenance details and see
the predicted renewal probability update live.

## What this actually found

After four rounds of finding and fixing real problems (see the notebook for the full story), two
signals survive every check:

- **Seasonality is the strongest, most reliable driver.** Leases starting in late spring through
  early fall renew noticeably more often than winter starts (~13pt swing) — this held up unchanged
  through every correction made along the way.
- **Unit size is the second-strongest, and the most trustworthy in a different way**: it's joined
  by unit number rather than tenant name, so unlike almost every other field in this dataset, it's
  100% observed with no missing-data caveats. Bigger units renew more.
- Rent, lease term, and unit floor have real but modest effects — and rent's effect **reversed
  direction entirely** once a data artifact was found and fixed (see below). Treat these as
  directional hints, not levers to act on with confidence.
- Screening results, satisfaction surveys, and maintenance history individually move the estimate
  only a few points — not because they don't matter, but because roughly a third to two-thirds of
  the training data doesn't have them (a real data-coverage limit, not a modeling failure).

The cross-validated model (Gradient Boosting, regularized) reaches a ROC AUC of ~0.66 — real,
useful discrimination, but nowhere near "confident individual prediction" territory. The [companion
notebook](notebook/renewal_prediction.ipynb) is honest about that limit throughout.

## Why this repo is also about what went wrong

A model that "just works" on the first try over ~500 rows of real-world property data should be
treated with suspicion. This project went through four rounds of correction, each of which changed
what looked like the answer:

1. **Overfitting.** The first version of the model looked great (97% training accuracy) but only
   scored 72% on data it hadn't seen — a 25-point gap. It had memorized noise: nudging one input
   (maintenance request count) up and down produced a prediction that bounced erratically instead
   of moving smoothly. Fixed by regularizing the model (shallower trees, minimum leaf size, row
   subsampling) — accuracy on unseen data barely changed, but the erratic behavior disappeared.
2. **A leaky feature, twice over.** Two columns (`Previous Rent` and `Tenant Transfer`) turned out
   to be populated *as a consequence of* a renewal happening, not observable beforehand — including
   them inflates apparent accuracy without being usable for real prediction. A second, sneakier
   version of the same problem: 32 leases had a rent of exactly `$0`, which looked like real data
   but turned out to be a placeholder written whenever a tenant transferred units and the new rent
   was never entered. Both had to be found and excluded (see notebook section 4).
3. **Measuring "what matters" wrong.** An early approach measured each field's effect by varying it
   for one hypothetical "typical tenant." That method was misleading — combined with the zero-rent
   bug above, it made rent look like the single biggest driver of *lower* renewal. Averaging the
   effect across every real lease in the data instead (section 6b) reversed that finding entirely.
4. **A name-matching bug.** Some source files write names as `"First Last"` with no comma; others
   use `"Last, First"`. A naive parser for the no-comma format silently mangled compound (multi-word)
   surnames, undercounting data coverage for exactly the tenants who have them — not a random bug,
   one with a real, unequal impact. Fixed in section 1b by cross-referencing surname formats across
   files instead of assuming the last word is always the surname.

The lesson underneath all four: when a real-world dataset produces a suspiciously strong or a
suspiciously clean-looking result, that's the moment to dig in, not move on.

## Repository structure

```
data/                    Anonymized source CSVs -- see data/README.md for the full column
                         reference and exactly how the anonymization works.
notebook/
  renewal_prediction.ipynb   The whole analysis, start to finish: anonymized-name joins, the
                             overfitting/leakage findings above, model training, and the final
                             feature-effect analysis. Runs top to bottom with no manual steps.
output/
  renewal_features_anonymized.csv   The joined, feature-complete dataset the notebook produces.
model/
  renewal_model.json       The trained model, exported as plain JSON (tree structure +
                            preprocessing stats) so it can be scored without Python or a server.
scripts/
  export_model.py          Regenerates model/renewal_model.json from output/*.csv.
widget/
  renewal_widget_template.html   The widget's source (has a %%MODEL_JSON%% placeholder).
  build_widget.py                Injects model/renewal_model.json into the template.
  renewal_widget.html            The built, ready-to-open widget (already included).
```

## Reproducing this

```bash
pip install -r requirements.txt
jupyter nbconvert --to notebook --execute --inplace notebook/renewal_prediction.ipynb
python scripts/export_model.py
python widget/build_widget.py
```

The notebook is deterministic (fixed random seeds throughout), so re-running it end to end
reproduces the same dataset, the same model, and the same numbers reported in its own markdown
cells. If you retrain with different features or hyperparameters, re-run the last two steps to
refresh the model file and the widget.

## Anonymization

No file in this repository — input, output, or the widget — contains a real tenant name, staff
name, vendor name, email, phone number, address, or anything that identifies the property. See
[`data/README.md`](data/README.md) for exactly what was removed from each source file and how
names were consistently pseudonymized across files (which matters, since several of this project's
findings are specifically about *joining* those files together correctly).

## License

No license file is included yet — add one (e.g. MIT) before treating this as open for reuse.
