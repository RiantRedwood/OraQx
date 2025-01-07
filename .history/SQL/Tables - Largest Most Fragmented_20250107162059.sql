-- Purpose: Provides a detailed breakdown of table size and fragmentation, critical for storage prioritization.
SELECT
    t.OWNER,
    t.TABLE_NAME,
    t.BLOCKS * ts.BLOCK_SIZE AS TABLE_SIZE_BYTES,
    ts.TABLESPACE_NAME,
    p.PARTITION_NAME,
    p.HIGH_VALUE,
    SUM(seg.BYTES) AS TOTAL_SEGMENT_SIZE,
    (SUM(seg.BYTES) - t.BLOCKS * ts.BLOCK_SIZE) AS FRAGMENTATION_BYTES
FROM
    DBA_TABLES t
JOIN
    DBA_TAB_PARTITIONS p ON t.TABLE_NAME = p.TABLE_NAME AND t.OWNER = p.TABLE_OWNER
JOIN
    DBA_SEGMENTS seg ON t.TABLE_NAME = seg.SEGMENT_NAME AND t.OWNER = seg.OWNER
JOIN
    DBA_TABLESPACES ts ON t.TABLESPACE_NAME = ts.TABLESPACE_NAME
WHERE
    t.OWNER NOT IN ('SYS', 'SYSTEM')
GROUP BY
    t.OWNER, t.TABLE_NAME, t.BLOCKS, ts.BLOCK_SIZE, ts.TABLESPACE_NAME, p.PARTITION_NAME, p.HIGH_VALUE
ORDER BY
    TABLE_SIZE_BYTES DESC, FRAGMENTATION_BYTES DESC;
