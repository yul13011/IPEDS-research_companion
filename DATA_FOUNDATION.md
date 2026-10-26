# IPEDS data foundation

October 19 update: a derived [analytical catalog layer](ANALYTICAL_CATALOG.md) now links this foundation to field/table semantics, observed keys, directory joins and cross-year evidence. The historical foundation account below remains the source-conversion record.

Completed scope: faithful annual SQLite copies and a comprehensive searchable source-metadata catalog. Original Access databases, codebooks and release notes remain unchanged. Measure harmonization, analytical benchmark questions and the conversational agent are deferred until the project owner supplies validated results.

## Where the files are

All generated files are under this document’s neighboring `data/` folder:

```text
agent-redesign/
    data/
        annual/
            IPEDS_2015-16_Final/IPEDS201516.sqlite
            IPEDS_2016-17_Final/IPEDS201617.sqlite
            ...
            IPEDS_2024-25_Provisional/IPEDS202425.sqlite
        metadata_catalog.sqlite
        foundation_verification.json
        metadata_source_verification.json
        catalog_verification.json
    ingestion/
        README.md
        ... repeatable import, verification and search scripts ...
```

The new 2015–16 copy is independently generated from the designated source root; the earlier SQLite file beside the originals is not modified or relied upon.

## Annual copies

| Release | User tables | Rows, including metadata tables |
| --- | ---: | ---: |
| IPEDS_2015-16_Final | 52 | 3,299,056 |
| IPEDS_2016-17_Final | 55 | 3,386,220 |
| IPEDS_2017-18_Final | 54 | 3,333,620 |
| IPEDS_2018-19_Final | 55 | 3,279,594 |
| IPEDS_2019-20_Final | 55 | 3,140,338 |
| IPEDS_2020-21_Final | 56 | 3,394,088 |
| IPEDS_2021-22_Final | 56 | 3,314,879 |
| IPEDS_2022-23_Final | 58 | 3,474,592 |
| IPEDS_2023-24_Final | 57 | 3,363,672 |
| IPEDS_2024-25_Provisional | 56 | 3,498,252 |

Total: **554 tables and 33,484,311 rows** across ten independent annual copies.

Each annual folder includes a source/output hash manifest, table-level verification hashes, physical column/type/null-count inventory, and conversion log. Annual data are not unioned or harmonized. Original table names, fields and values are retained. Exact decimal fields are represented as decimal text where needed to avoid precision loss; source types are preserved in the schema catalog.

## What is in the catalog

| Content | Imported count |
| --- | ---: |
| Annual releases | 10 |
| Original source files registered | 30 |
| Codebook sheets | 58 |
| Original nonempty workbook rows | 150,605 |
| Table-definition entries | 506 |
| Variable-definition entries | 23,990 |
| Categorical-code entries | 124,493 |
| Release-note paragraphs | 181 |
| Physical tables | 554 |
| Physical columns | 25,245 |

Counts are source entries, including repeated documentation/code entries when present. They do not mean that there are that many distinct cross-year concepts. The catalog contains every sheet, including supplemental change sheets, introductions and metadata definitions. Source references retain release, file hash, sheet and row/paragraph.

Keyword and phrase search is implemented through SQLite FTS5. A small read-only search utility is available at `ingestion/search_catalog.py`; usage and schema documentation are in `ingestion/README.md`. This is a searchable foundation, not yet an LLM agent.

## Documentation issues are separate from source definitions

Observed mismatches are stored in the catalog’s `issues` table, with candidate physical locations where available. Source metadata is preserved; candidates are not automatically approved mappings.

| Issue type | Count |
| --- | ---: |
| documented_column_absent | 346 |
| documented_table_absent | 1 |
| physical_column_not_in_dictionary | 901 |

The known 2023–24 SFA placement conflicts are visible to search users as warnings, along with source row references. Shared UNITID fields omitted from dictionaries are informational, not treated as data corruption.

## Verification completed

- Original Access source hashes match before/after conversion and during final reconciliation.
- Every copied table matches its source row count.
- Every copied cell was checked through canonical row-value hashes before insertion and after SQLite read-back; null counts also match column by column.
- Each annual SQLite database passed integrity_check.
- Independent checks confirmed all output file hashes, table inventories, row counts and catalog physical schemas.
- Every imported nonempty workbook row/cell and release-note paragraph was independently compared with its original source.
- Catalog foreign keys, integrity, search-index coverage and keyword searches passed.

These checks establish faithful storage and metadata retrieval. They do not establish that every measure is longitudinally comparable or certify any analytical answer. No validated question-bank statistics were tested in this stage.

## Next step when the project owner is ready

Receive the test questions, exact populations/periods and independently validated results. Then develop reviewed annual measure mappings, answer those questions from the annual copies, and compare results against the supplied benchmarks before integrating the agent.
