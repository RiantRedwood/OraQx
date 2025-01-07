import re, sqlparse
from collections import Counter
import pandas as pd
import logging

# Oracle SQL Parsing Approach

COMMENT_REGEX = re.compile(r"(?s)/\*.*?\*/|--.*?\n")
CTE_REGEX = re.compile(r"WITH\s+([\w]+)\s+AS\s*\((.*?)\)", re.I | re.DOTALL)
TABLE_REGEX = re.compile(r"(?<![\.\w])([\w]+(?:\.[\w]+)?)", re.I)
HINT_REGEX = re.compile(r"/\*\+\s*(.*?)\s*\*/", re.DOTALL)

def norm_strip(sql):
    return re.sub(r"\s+", " ", re.sub(COMMENT_REGEX, "", sql)).strip()

def extract_tables(stmt):
    return [t.get_real_name() for t in stmt.flatten() if isinstance(t, sqlparse.sql.Identifier)]

def extract_joins(stmt):
    return [str(t) for t in stmt.flatten() if isinstance(t, sqlparse.sql.Comparison)]

def extract_ctes(sql):
    return [match.group(1) for match in CTE_REGEX.finditer(sql)]

def parse_oracle_sql(sql):
    sql = norm_strip(sql)
    parsed = sqlparse.parse(sql)[0]
    tables = extract_tables(parsed)
    joins = extract_joins(parsed)
    ctes = extract_ctes(sql)
    return {"tables": tables, "joins": joins, "ctes": ctes}

# Example Usage (assuming 'df' with 'table_query' column exists)
# df['parsed_query'] = df['table_query'].astype(str).apply(parse_oracle_sql)

def clean_query(sql):
    sql = re.sub(COMMENT_REGEX, "", sql)
    sql = re.sub(r"\s+", " ", sql).strip()
    keywords = ["SELECT", "FROM", "WHERE", "GROUP BY", "ORDER BY", "HAVING", "JOIN", "ON"]
    for kw in keywords:
        sql = re.sub(fr"\b{kw}\b", f"\n{kw}", sql, flags=re.I)
    return sql

# Example cleaning application
# df['cleaned_query'] = df['table_query'].astype(str).apply(clean_query)