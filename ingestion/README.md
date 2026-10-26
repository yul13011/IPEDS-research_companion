# Annual copies and source metadata catalog

This stage builds faithful queryable copies and comprehensive searchable metadata. It does not implement an agent, approve measure mappings, harmonize statistics, or run question-bank accuracy tests.

## Storage

Originals remain under the project folder `IPEDS Data/` and are opened read-only. Generated data live separately:

```text
agent-redesign/data/
    annual/
        IPEDS_2015-16_Final/
            IPEDS201516.sqlite
            verification.json
            columns.csv
            table_checks.csv
            conversion.log
        ... one folder per supplied annual release ...
        import_status.json
    metadata_catalog.sqlite
    catalog_verification.json
```

The previous 2015 SQLite copy in the source folder is not used or overwritten. The new annual copy is independently rebuilt from the current Access source.

## Faithful conversion

`ConvertAnnual.java` uses Jackcess to read Access and Xerial SQLite JDBC to write SQLite, bypassing the installed Access engine. `import_annual.py` orchestrates two local conversion processes, checks original-source SHA-256 before and after, and publishes each completed SQLite copy only after verification. It refuses to overwrite an existing unverified or changed output. Existing verified outputs can be reused only when source, converter, and output hashes match.

The converter preserves table/column names, row ordering, values, and nulls. INTEGER and REAL storage are selected from Access types; exact decimal NUMERIC/MONEY fields become decimal TEXT to preserve precision. Actual supplied schemas use LONG, INT, DOUBLE, NUMERIC, TEXT and MEMO. Other supported scalar types are explicit in the converter; unsupported types fail rather than being guessed. Downstream analytics must explicitly interpret decimal TEXT; do not silently sum or compare it lexically. No rates, category crosswalks, or population adjustments are introduced.

Verification for every table compares engine source row count to inserted/read-back count, every column's null count, and SHA-256 over every canonically typed row value before insertion and after read-back. Whole-database integrity_check must pass. The hash represents faithfully converted values rather than Access's binary storage encoding; original-file hashes separately prove unchanged sources. Signed floating-point zero is normalized for numeric equality. Null and empty string remain distinct. UNITID lookup indexes are added; Access forms, relationships, queries and original indexes are not migrated as executable objects.

## Catalog contents

`build_catalog.py` imports every nonempty row of every codebook sheet and every nonempty release-note paragraph. `sheet_rows` preserves original cell values/formula strings as JSON with row numbers. Searchable records also provide whitespace-cleaned text. Original files are never rewritten.

| Catalog table | Purpose |
| --- | --- |
| `releases`, `source_files` | Collection cycles, release labels, source paths and file hashes. Labels follow source folders/ReadMe headings; table-level release details remain separate. |
| `sheets`, `sheet_rows` | All sheets and nonempty rows, including supplemental change sheets, introductions and metadata definitions. |
| `records`, `search_index` | Searchable source documentation with workbook sheet/row or Word paragraph references. FTS5 provides keyword/phrase search, not semantic equivalence. |
| `table_docs` | Original annual table descriptions, survey names, reporting periods, release details. |
| `variable_docs` | Original variable labels/definitions, types, formats, imputation references and groupings. |
| `code_values` | Original categorical codes/labels and source frequencies/percentages. Frequency differences are not definition changes. |
| `release_notes` | Original release-note paragraph text. |
| `physical_tables`, `physical_columns` | Verified queryable table locations, types, source/copy row counts and per-column null counts. |
| `issues` | Documentation/physical-location discrepancies and candidate locations, kept separate from source metadata. No automatic correction or measure approval. |

Each definition retains its release, source file hash/path, sheet and row. A matching field name at another table is a candidate location, not proof of semantic equivalence. In particular the observed 2023–24 SFA placement conflicts are retained as warnings, not silently repaired. The comprehensive catalog is separate from the illustrative measure-registry folder.

## Running

Use the bundled Python runtime reported by Codex's workspace dependency loader. The Java runtime is already installed on this computer. Local libraries are in `outputs/access_conversion/`: Jackcess 4.0.7, commons-lang3 3.18.0, commons-logging 1.3.5, SQLite JDBC 3.46.1.0, and slf4j-api/nop 1.7.36. The local ECJ compiler is 3.26.0. No original data is uploaded to an external service.

From the project root, compile the converter (PowerShell):

```powershell
java -jar outputs/access_conversion/compiler.jar -1.8 -cp 'outputs/access_conversion/jackcess.jar;outputs/access_conversion/commons-lang3.jar;outputs/access_conversion/commons-logging.jar;outputs/access_conversion/sqlite-jdbc.jar' agent-redesign/ingestion/ConvertAnnual.java
```

Run with the bundled Python executable:

```text
agent-redesign/ingestion/import_annual.py
agent-redesign/ingestion/build_catalog.py
agent-redesign/ingestion/build_catalog.py --reconcile
agent-redesign/ingestion/build_catalog.py --verify-only
agent-redesign/ingestion/verify_foundation.py --metadata-only
agent-redesign/ingestion/verify_foundation.py --annual-only
```

The initial catalog build runs once and refuses to overwrite an existing catalog. For a new source version, build in a new/versioned output location rather than overwriting the source or silently replacing history. Reconciliation updates only derived physical-schema and issue tables in one transaction, after annual imports finish.

Read-only metadata search examples (not analytical question tests):

```text
agent-redesign/ingestion/search_catalog.py "financial aid" --release 2024-25 --kind variable_definition --limit 5
agent-redesign/ingestion/search_catalog.py UAGRNTP --release 2023-24 --kind variable_definition
```

Search returns source references and associated discrepancy warnings. A direct search is not a validated analysis plan. The scripts are local foundation utilities, not the conversational agent.

The independent metadata verifier compares every imported nonempty workbook row/cell and release-note paragraph with a fresh read of the originals. The annual verifier independently checks output file hashes, table inventories, row counts and physical catalog schemas, in addition to the converter's full value checks. Both produce JSON verification reports in `data/`.

## Deferred by the project owner

Measure-mapping validation and question-answer evaluation await user-supplied questions and independently validated results. Agent orchestration, chart generation, exports, and application deployment are not part of this stage.
