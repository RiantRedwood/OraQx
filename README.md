## Oracle SQL Specific Features / Caveats

**Purpose:**  Parses Oracle SQL queries for structural analysis. Extracts tables, joins, and CTEs. Cleans and normalizes queries. Identifies Oracle-specific features.

**Components:**

- **Regex (`COMMENT_REGEX`, `CTE_REGEX`, `TABLE_REGEX`, `HINT_REGEX`):** Defines patterns for identifying comments, Common Table Expressions, table names (including schema), and Oracle hints.

- **`norm_strip(sql)`:**  Removes comments and normalizes whitespace from SQL strings.

- **`extract_tables(stmt)`:**  Extracts table identifiers from a `sqlparse` statement.

- **`extract_joins(stmt)`:** Extracts join conditions from a `sqlparse` statement.

- **`extract_ctes(sql)`:** Extracts CTE names using regex.

- **`parse_oracle_sql(sql)`:** Orchestrates parsing. Normalizes, parses with `sqlparse`, extracts tables, joins, and CTEs. Returns a dictionary.

- **`clean_query(sql)`:** Removes comments, normalizes whitespace, and formats for readability (keywords on newlines).

**Oracle-Specific Feature Detection Logic (Implicit):**

While the script primarily focuses on structural parsing, it can indirectly highlight Oracle-specific syntax through successful parsing of constructs like:

- **Oracle Hints:**  `HINT_REGEX` identifies optimizer hints (`/*+ HINT */`).
- **Date Functions:**  Parsing `TO_DATE`, `SYSDATE`, `LAST_DAY`, `ADD_MONTHS`, `TRUNC`.
- **Schema References:** `TABLE_REGEX` handles `schema.table` format.
- **String Concatenation:**  Presence of `||`.
- **Analytic Functions:**  Parsing `OVER (PARTITION BY ...)`.

**Usage:**

1. **Import:** `import re, sqlparse, pandas as pd`.
2. **Define Regex:** Ensure regex patterns match intended Oracle SQL constructs.
3. **Apply Parsing:** Use `df['parsed_query'] = df['table_query'].astype(str).apply(parse_oracle_sql)` to parse a DataFrame column.
4. **Apply Cleaning:** Use `df['cleaned_query'] = df['table_query'].astype(str).apply(clean_query)` to clean queries.

**Dependencies:**

- `re`: Python's built-in regular expression library.
- `sqlparse`:  SQL parsing library (`pip install sqlparse`).
- `pandas`: Data analysis library (`pip install pandas`).

**Output:**

- `parse_oracle_sql`:  Returns a dictionary per query: `{'tables': [list of tables], 'joins': [list of join conditions], 'ctes': [list of CTE names]}`. Successful parsing implies recognition of Oracle syntax.
- `clean_query`: Returns a cleaned and formatted SQL string.

**Logic:**

- **Parsing:** Employs regex for preliminary structure identification and `sqlparse` for detailed SQL token analysis. Successfully parsing Oracle-specific constructs indicates their presence.
- **Cleaning:**  Prioritizes comment removal and whitespace normalization for streamlined analysis. Keyword formatting enhances readability.

**Oracle-Specific Findings (Examples):**

- **Query Hints:** `/*+ PARALLEL(8) MATERIALIZE */` (Query 10).
- **Date Functions:** `TO_DATE('2023-01-01', 'YYYY-MM-DD')`, `SYSDATE`, `LAST_DAY(ADD_MONTHS(SYSDATE, - 1))` (Query 10), `TRUNC(date_column)` (Query 25, 33).
- **Schema References:** `CC_ANALYTICS.ED_HOURLY_CENSUS` (Query 15).
- **String Concatenation:** `|| ', '` (inferred from context).
- **Analytic Functions:** `ROW_NUMBER() OVER(PARTITION BY ...)` (Query 33).
- **NVL Function:** `NVL(column, default_value)` (Query 10).
- **Common Table Expressions (CTEs):** Use of `WITH` clause (Query 10, 25, 33).

**Limitations:**

- Syntax validation is not performed. Focuses on structural element extraction.
- Complex or dynamically generated SQL might require adjustments to regex patterns.
- Explicit identification of all Oracle-specific features requires extending the parsing logic or using dedicated Oracle SQL parsing libraries. The current script infers Oracle usage through the successful parsing of common Oracle constructs.