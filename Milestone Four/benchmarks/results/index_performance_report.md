# MongoDB Index Performance Comparison

Source report captured: 2026-10-22T18:55:45.439107+00:00
Database: `aac.animals`  
Collection size at capture: 10,001 documents

## Index inventory

Before: `_id_`  
After: `_id_`, `idx_animal_id_page`, `idx_breed_sort`, `idx_name_sort`, `idx_rescue_type_sex_age`  
Newly added: `idx_animal_id_page`, `idx_breed_sort`, `idx_name_sort`, `idx_rescue_type_sex_age`

## Query execution statistics

| Query | Time before (ms) | Time after (ms) | Docs examined before | Docs examined after | Keys examined before | Keys examined after | Plan before → after |
|---|---:|---:|---:|---:|---:|---:|---|
| default_animal_page | 9 | 23 | 10,001 | 8 | 0 | 8 | Collection scan → Index: idx_animal_id_page |
| name_sorted_page | 13 | 13 | 10,001 | 8 | 0 | 8 | Collection scan → Index: idx_name_sort |
| breed_sorted_page | 13 | 19 | 10,001 | 8 | 0 | 8 | Collection scan → Index: idx_breed_sort |
| rescue_type_sex_age | 31 | 35 | 10,001 | 200 | 0 | 200 | Collection scan → Index: idx_rescue_type_sex_age |
| water_rescue_page | 34 | 13 | 10,001 | 200 | 0 | 200 | Collection scan → Index: idx_rescue_type_sex_age |
| breed_contains_page | 40 | 0 | 10,001 | 26 | 0 | 26 | Collection scan → Index: idx_animal_id_page |

## Relative changes by query

Positive reductions below indicate fewer documents examined or lower reported execution time.

| Query | Execution-time change | Documents-examined change |
|---|---|---|
| default_animal_page | 155.6% increase | +99.9% reduction |
| name_sorted_page | +0.0% reduction | +99.9% reduction |
| breed_sorted_page | 46.2% increase | +99.9% reduction |
| rescue_type_sex_age | 12.9% increase | +98.0% reduction |
| water_rescue_page | +61.8% reduction | +98.0% reduction |
| breed_contains_page | +100.0% reduction | +99.7% reduction |

## Limitations and interpretation

- These figures come from MongoDB `explain()` execution statistics; each query was sampled once per condition.
- Millisecond timings are coarse and vary with server load, cache state, and network conditions. A `0 ms` reading does not prove a query is instantaneous.
- `totalDocsExamined` and `totalKeysExamined` show work performed, not proof that a particular index was helpful.
- A compound index can improve sorting or narrow a query while other query shapes see no benefit.
- Case-insensitive substring searches such as `contains Labrador` may not use the planned B-tree indexes efficiently.
- Do not claim a before-and-after speedup if the 'before' snapshot was captured after the indexes already existed.

## Capstone documentation

Use the measured counts and query-plan differences above in the Milestone Four narrative. Explain whether each proposed index improved, worsened, or did not measurably change the observed query, and discuss index maintenance costs.
