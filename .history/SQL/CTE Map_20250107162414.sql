--Purpose: Tracks CTE definitions and their contributions to dependent queries, ensuring no logical flow is missed.
--
WITH RECURSIVE CTE_MAP AS (
    SELECT
        sql.SQL_ID,
        REGEXP_SUBSTR(sql.SQL_TEXT, 'WITH(.*?)SELECT', 1, 1, 'i') AS CTE_DEFINITION,
        REGEXP_SUBSTR(sql.SQL_TEXT, 'SELECT(.*?)(FROM)', 1, 1, 'i') AS SELECT_FIELDS,
        REGEXP_SUBSTR(plan.OPERATION, 'TABLE ACCESS|INDEX SCAN', 1, 1, 'i') AS ACCESS_METHOD,
        plan.OBJECT_NAME,
        plan.OBJECT_ALIAS
    FROM
        DBA_HIST_SQLTEXT sql
    JOIN
        DBA_HIST_SQL_PLAN plan ON sql.SQL_ID = plan.SQL_ID
    WHERE
        sql.SQL_TEXT LIKE 'WITH%' -- Extracts CTEs
)
SELECT
    cte.SQL_ID,
    cte.CTE_DEFINITION,
    cte.SELECT_FIELDS,
    LISTAGG(cte.OBJECT_NAME || ' (' || cte.ACCESS_METHOD || ')', ', ') WITHIN GROUP (ORDER BY cte.OBJECT_NAME) AS ACCESS_PATTERNS,
    COUNT(DISTINCT cte.OBJECT_NAME) AS DEPENDENCY_COUNT
FROM
    CTE_MAP cte
GROUP BY
    cte.SQL_ID, cte.CTE_DEFINITION, cte.SELECT_FIELDS;
