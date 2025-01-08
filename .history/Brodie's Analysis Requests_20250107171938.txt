### Initial Request

**Brodie Dore** initiated a request to **Michael** for an analysis of SQL queries on the Tableau server to assist with data migration, governance, and user profiling. The primary goal was to identify the most frequently used tables/CTEs across various Tableau project folders, aiming to optimize the D&A Snowflake build and enhance data governance.

Brodie’s **specific analysis requests** included:
1. **Columns** in final `SELECT` statements.
2. **Referenced columns** linked to tables or CTEs.
3. **Database tables** explicitly used.
4. **CTEs** count in each query.
5. **Database links** used, including their names.
6. Presence of `SELECT *` (asterisk usage).
7. Count of **parallel hints** for tuning.
8. Count of **materialized hints** for tuning.
9. Query **lines of code** for complexity evaluation.

Brodie noted additional analysis possibilities:
- **User activity** for popular workbooks.
- **Execution times** to identify long-running queries.
- Suggested **user personas** based on Tableau usage.
