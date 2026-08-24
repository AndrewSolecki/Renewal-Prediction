# Data

Six CSVs from a mid-size apartment property's leasing system, trimmed to only the columns the
analysis notebook (`../notebook/renewal_prediction.ipynb`) actually reads, and fully anonymized
before being committed here. This file documents both.

## Anonymization

Every file in this folder has been through the same process, applied consistently across all six
files so the same real person keeps the same fake identity everywhere they appear (which matters,
since the notebook's whole point in section 1-2 is joining these files together by name):

1. **Every tenant, applicant, staff member, and vendor name was replaced with a placeholder
   identity** drawn from a fixed pool of common English first/last names, assigned by a
   deterministic mapping keyed off the real name (never off anything guessable from the data
   itself). The mapping exists only in a private, one-time build script that is **not** included
   in this repository, there's no way to reverse it from anything published here.
2. **Business and institutional tenants** (e.g. a ground-floor retail lease, a union, a
   utility company) were replaced with a sequential `Business Tenant N` label rather than a fake
   human name.
3. **Tenants with a compound (multi-word) surname keep a compound fake surname**, and the fake
   surname pool was applied broadly enough that the resulting name-formatting patterns (comma vs.
   no-comma, single-word vs. multi-word) match the original data's structure. This matters because
   the notebook is partly a demonstration of a real name-matching bug tied to multi-word surnames
   (section 1b), flattening every fake name to a single word would have quietly erased the exact
   problem the notebook exists to show.
4. **Unit type / floorplan names were replaced with generic labels** (`Unit Type 1` ... `Unit Type
   17`, numbered by increasing square footage) so no marketing-facing floorplan name is exposed.
5. **The property name, address, and any staff/vendor-identifying columns were removed outright**
   rather than pseudonymized, see the per-file column lists below for exactly what was dropped.
   Free-text fields (maintenance instructions, survey comments, override notes) were dropped
   entirely rather than scrubbed, since free text is where incidental PII is most likely to hide.

**What this means practically:** the notebook's own results (match rates, model accuracy, feature
effects) come out very close to, but not bit-for-bit identical to, the original private analysis.
The anonymization process incidentally fixed a couple of minor, pre-existing quirks in how the
original analysis detected compound surnames (a business name or two had been miscategorized as a
person's surname), rather than deliberately reintroduce those quirks to chase an exact numeric
match, this repository reports whatever numbers its own, included code actually produces. The
qualitative findings (which factors matter, in which direction, and by roughly how much) are
unaffected either way.

## Files

### `renewal_summary_cleaned.csv`
One row per lease term (545 rows, 258 unique tenants).

| Column | Meaning |
|---|---|
| `Unit Name` | Unit number. |
| `Tenant Name` | `Last, First Middle.` (reconstructed from the columns below). |
| `Lease Start` / `Lease End` | This lease term's dates. |
| `Previous Lease Start` / `Previous Lease End` | The tenant's prior term's dates, if one exists. |
| `Previous Rent` | Rent under the prior term. **Excluded from modeling**, see note below. |
| `Rent` | Rent under this term. 32 rows show `0`, which is a data-entry artifact, not a real $0 rent (see notebook section 4). |
| `Percent Difference` / `Dollar Difference` | Change from `Previous Rent` to `Rent`. Same exclusion as `Previous Rent`. |
| `Status` | Outcome: `Renewed`, `Did Not Renew`, `Month To Month`, or `Pending`. |
| `Term` | Lease term as originally recorded (free text, e.g. "12 month"). |
| `Tenant Transfer` | Whether the tenant moved units as part of this term. **Excluded from modeling**, only ever `Yes` on `Renewed` rows, since transferring is itself a form of renewing. |
| `Term_Days` | Lease term length in days. |
| `Is_Month_To_Month` | Whether this specific term is month-to-month. |
| `Last` / `First` / `Middle` | Anonymized name, split into parts. |

### `rent_roll.csv`
A present-day snapshot (139 rows), only covers tenants still active on the property today.

| Column | Meaning |
|---|---|
| `Unit` | Unit number. |
| `Unit Type` | Generic floorplan label (`Unit Type 1`-`17`). |
| `BD/BA` | Bedroom/bathroom count, raw format `"1/1.00"`. |
| `Tenant` | Anonymized name, `"First M. Last"` (no comma, see notebook section 1b for why this format matters). |
| `Past Due` | Current past-due balance. Can be negative (a credit on the account). |
| `Late Count` | Current late-payment count. |

Dropped: `Lease To`, `Computed Market Rent`, `Rent`, `Recurring Charges` (unused), `Property` (address).

### `screening_assessments.csv`
1,043 rows, applicant screening results at move-in.

| Column | Meaning |
|---|---|
| `Applicant Name` | Anonymized name, `"First M. Last"` (no comma), sometimes with a `(Co-signer for X)` suffix. |
| `Calculated Assessment` | e.g. `"Criteria Met"`, `"Conditions Apply"`. |
| `Overridden At` | Timestamp if a human overrode the calculated result; blank otherwise. |

Dropped: `Screen Ran At` (unused), `Final Assessment` (unused), `Override Reasons` / `Override
Comment` (free text), `Overridden By` (staff name), `Property` (address).

### `survey_responses.csv`
325 rows, post-maintenance satisfaction surveys.

| Column | Meaning |
|---|---|
| `Respondent` | Anonymized name, `"Last, First M."`. |
| `How satisfied...?` | 1-5 rating. |
| `Has the issue been resolved completely?` / `Was the work completed in a timely manner?` | Yes/No. |
| `Date Received` | Used to only count surveys that happened *before* the lease term being evaluated. |

Dropped: `Property` (address), `Any additional feedback?` (free text), `Date Sent` (unused), `Work
Order Number` (unused), `Job Description` (free text), `Assigned User` / `Vendor Name` (staff/vendor).

### `work_order.csv`
6,544 rows, maintenance request history.

| Column | Meaning |
|---|---|
| `Work Order Number` | Used only as a count key. |
| `Primary Resident` | Anonymized name, `"Last, First M."`. |
| `Created At` | Used to only count work orders that happened *before* the lease term being evaluated. |
| `Amount` | Dollar amount charged, if any (usually `0`). |
| `Resident Requested` | Whether the resident (vs. staff) initiated the request. |

Dropped: everything else, including **`Primary Resident Email` and `Primary Resident Phone
Number`** (direct PII), `Unit Address`, `Instructions` / `Service Request Description` / `Status
Notes` (free text), `Created By` / `Assigned User` / `Vendor` (staff/vendor names), `Property`.

### `occupancy_summary.csv`
17 rows, one per unit type, average square footage.

| Column | Meaning |
|---|---|
| `Unit Type` | Generic floorplan label, matching `rent_roll.csv`. |
| `Average Sq Ft` | Average square footage for that floorplan. |

Dropped: `Property` (address) and unused occupancy-rate columns.
