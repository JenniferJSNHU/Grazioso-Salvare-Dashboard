# MongoDB Current Index vs. Collection Scan Comparison

Captured (UTC): 2026-10-22T18:10:30.777770+00:00
Database: `aac.animals`  
Documents: 10,001.00  
Explain trials per condition: 3

## Methodology

The same queries were tested on the current database in two ways: (1) using MongoDB's normal query planner, which may select an index, and (2) using a `$natural` hint to force a collection scan. These measurements do **not** represent historical performance before indexes were created.

## Results

| Query | Normal plan | Forced scan plan | Normal time (ms) | Scan time (ms) | Normal docs examined | Scan docs examined | Docs reduction |
|---|---|---|---:|---:|---:|---:|---:|
| default_animal_page | Collection scan | Collection scan | 10.00 | 10.00 | 10,001.00 | 10,001.00 | +0.0% |
| name_sorted_page | Collection scan | Collection scan | 10.00 | 10.00 | 10,001.00 | 10,001.00 | +0.0% |
| breed_sorted_page | Collection scan | Collection scan | 10.00 | 10.00 | 10,001.00 | 10,001.00 | +0.0% |
| rescue_type_sex_age | Collection scan | Collection scan | 11.00 | 11.00 | 10,001.00 | 10,001.00 | +0.0% |
| water_rescue_page | Collection scan | Collection scan | 9.00 | 10.00 | 10,001.00 | 10,001.00 | +0.0% |
| breed_contains_page | Collection scan | Collection scan | 13.00 | 12.00 | 10,001.00 | 10,001.00 | +0.0% |

## Interpretation and limitations

- A normal query plan is not guaranteed to use an index; inspect the plan name in the table.
- A forced scan provides a controlled non-indexed comparison on the current database, **not** an original before-indexing measurement.
- `executionTimeMillis` is coarse; cache effects and server activity may affect timings. Documents and keys examined can be more informative.
- If `nReturned` is zero, the query did not match any records in that sample; interpret its timing cautiously.
- Case-insensitive substring searches may be unable to use ordinary B-tree indexes efficiently.
- Indexes add storage and incur maintenance work when documents are inserted or updated.
- The original Step 3 `index_comparison.json` is still required to claim a historical before-and-after result. It is not recreated by this script.

## Capstone documentation

Describe these findings as a controlled comparison of current query plans against forced collection scans. Do not describe the scan times as measurements captured before the indexes were installed.
