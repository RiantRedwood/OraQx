-- Purpose: Evaluates columns critical to filtering, grouping, or joining to highlight the most impactful columns.
--
SELECT
    c.OWNER,
    c.TABLE_NAME,
    c.COLUMN_NAME,
    COUNT(DISTINCT sql.SQL_ID) AS QUERY_COUNT,
    COUNT(CASE WHEN sql.SQL_TEXT LIKE '%' || c.COLUMN_NAME || '%' THEN 1 END) AS DIRECT_REFERENCES,
    COUNT(CASE WHEN plan.FILTER_PREDICATES LIKE '%' || c.COLUMN_NAME || '%' THEN 1 END) AS FILTER_USAGE,
    COUNT(CASE WHEN plan.ACCESS_PREDICATES LIKE '%' || c.COLUMN_NAME || '%' THEN 1 END) AS ACCESS_USAGE,
    COUNT(CASE WHEN sql.SQL_TEXT LIKE '%GROUP BY%' AND sql.SQL_TEXT LIKE '%' || c.COLUMN_NAME || '%' THEN 1 END) AS GROUP_BY_USAGE,
    RANK() OVER (PARTITION BY c.TABLE_NAME ORDER BY QUERY_COUNT DESC, DIRECT_REFERENCES DESC) AS COLUMN_PRIORITY_RANK
FROM
    DBA_HIST_SQLTEXT sql
JOIN
    DBA_HIST_SQL_PLAN plan ON sql.SQL_ID = plan.SQL_ID
JOIN
    DBA_TAB_COLUMNS c ON plan.OBJECT_NAME = c.TABLE_NAME AND plan.OBJECT_OWNER = c.OWNER
WHERE
    c.OWNER NOT IN ('SYS', 'SYSTEM')
GROUP BY
    c.OWNER, c.TABLE_NAME, c.COLUMN_NAME
ORDER BY
    QUERY_COUNT DESC, COLUMN_PRIORITY_RANK ASC;
