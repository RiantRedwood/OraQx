-- Purpose: Combines frequency of use, execution complexity, and I/O intensity to provide a 360-degree view of table importance.
SELECT
    t.OWNER,
    t.TABLE_NAME,
    COUNT(DISTINCT sql.SQL_ID) AS QUERY_COUNT,
    COUNT(DISTINCT plan.PLAN_HASH_VALUE) AS EXEC_PLAN_VARIANTS,
    SUM(plan.OPTIMIZER_COST) AS TOTAL_COST,
    AVG(plan.OPTIMIZER_COST) AS AVG_COST,
    MAX(plan.OPTIMIZER_COST) AS MAX_COST,
    MAX(io.BLOCKS_READ) AS MAX_IO_READ,
    COUNT(CASE WHEN sql.SQL_TEXT LIKE '%JOIN%' THEN 1 END) AS JOIN_OCCURRENCES,
    RANK() OVER (ORDER BY COUNT(DISTINCT sql.SQL_ID) DESC, TOTAL_COST DESC, MAX_IO_READ DESC) AS PRIORITY_RANK
FROM
    DBA_HIST_SQLTEXT sql
JOIN
    DBA_HIST_SQL_PLAN plan ON sql.SQL_ID = plan.SQL_ID
JOIN
    V$SQL_PLAN_STATISTICS io ON plan.SQL_ID = io.SQL_ID AND plan.PLAN_HASH_VALUE = io.PLAN_HASH_VALUE
JOIN
    DBA_TABLES t ON plan.OBJECT_NAME = t.TABLE_NAME AND plan.OBJECT_OWNER = t.OWNER
WHERE
    t.OWNER NOT IN ('SYS', 'SYSTEM')
GROUP BY
    t.OWNER, t.TABLE_NAME
ORDER BY
    PRIORITY_RANK ASC;
