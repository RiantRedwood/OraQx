import pandas as pd
import re
from collections import Counter
import logging
from typing import Dict, List, Tuple, Any, Set, Optional
from functools import lru_cache
import argparse
import sqlglot
from sqlglot import exp, parse_one
from sqlglot.errors import ParseError
from pyparsing import ParseResults, ParserElement, Word, alphas, alphanums, delimitedList, Optional, Keyword, Forward, Group, Suppress, Regex, ParseSyntaxException

# Set DEBUG to True for verbose logging, False otherwise
DEBUG = False

# Configure logging
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# File paths & Constants
FILE_PATH = r"C:\Users\joshm\source\repos\PolyQx\data_raw\data.xlsx"
SHEET_NAME = "Table Sample"
OUTPUT_FILE = "oracle_sql_parsing_results.xlsx"
TOP_N = 10

# Pre-compile regex patterns
COMMENT_HEADER_REGEX = re.compile(r"(?s)/\*.*?\*/|--.*?\n")
CTE_REGEX = re.compile(r"WITH\s+([a-zA-Z0-9_]+)\s+AS\s*\((.*?)\)(?=\s*[,)]|$)", re.IGNORECASE | re.DOTALL)
TABLE_REGEX = re.compile(r"([a-zA-Z0-9_]+(\.[a-zA-Z0-9_]+)?)", re.IGNORECASE)
ALIAS_REGEX = re.compile(r'\b(?:as\s+)?([a-zA-Z0-9_]+)\b', re.IGNORECASE)
COLUMN_REGEX = re.compile(r'\b([a-zA-Z0-9_]+)\b', re.IGNORECASE)
HINT_REGEX = re.compile(r"/\*\+\s*(.*?)\s*\*/", re.DOTALL)
SPACE_REGEX = re.compile(r"\s+")
SELECT_STATEMENT_TYPE = 'SELECT'
FROM_KEYWORD = "FROM"
WHERE_KEYWORD = "WHERE"
GROUP_BY_KEYWORD = "GROUP BY"


def normalize_and_strip_comments(query: str) -> str:
    """Standardize query format and strip all comments."""
    query = query.replace("_x000D_", "\n").strip()
    query = re.sub(COMMENT_HEADER_REGEX, "", query)
    return re.sub(SPACE_REGEX, " ", query)

@lru_cache(maxsize=None)
def parse_sql(query: str) -> Optional[sqlglot.Expression]:
    """Parse SQL query using sqlglot and cache results."""
    try:
        return parse_one(query)
    except ParseError as e:
       logging.error(f"sqlglot parse error: {e}, query={query}")
       return None


def extract_ctes(query: str) -> Dict[str, str]:
    """Extract CTE names and bodies from the query."""
    logging.debug(f"extract_ctes: query={query}")
    ctes = {}
    for match in re.finditer(CTE_REGEX, query):
        cte_name = match.group(1).strip()
        cte_body = match.group(2).strip()
        ctes[cte_name] = cte_body
    logging.debug(f"extract_ctes: ctes={ctes}")
    return ctes

def _extract_alias(token_str: str) -> Optional[str]:
    """Extract alias from a token string using regex."""
    match = re.search(ALIAS_REGEX, token_str)
    return match.group(1).strip() if match else None

def _process_expression(expression: Any, tables: List[str], joins: List[str], aliases: Dict[str, str], columns: List[str], processor_type: str, query:str, depth:int = 0) -> None:
    """Process SQL expressions for table, column, and join extraction recursively."""
    if depth > 10:
        logging.debug(f"_process_expression: Max depth reached, stopping recursion")
        return

    if isinstance(expression, exp.Table):
        table_name = expression.name
        table_alias = _extract_alias(str(expression))
        if processor_type == "table":
            if table_name:
                 tables.append(table_name)
            if table_alias:
                  aliases[table_alias] = table_name
    elif isinstance(expression, exp.Column):
        column_name = expression.name
        if processor_type == "column" and column_name:
            columns.append(column_name)
    elif isinstance(expression, exp.Join):
        if processor_type == "table":
            joins.append(str(expression.kind) + " " + str(expression.this) + " ON " + str(expression.expression))

    elif isinstance(expression, exp.Alias):
         alias = str(expression.alias)
         aliased_name = str(expression.this)
         if alias and aliased_name and processor_type == "table":
             aliases[alias] = aliased_name
         _process_expression(expression.this,tables, joins, aliases, columns, processor_type, query, depth + 1)

    elif isinstance(expression, exp.Identifier):
        if processor_type == "column":
            columns.append(str(expression.this))
    elif isinstance(expression, exp.Func):
        if processor_type == "column":
             for arg in expression.args:
                  if isinstance(arg, exp.Identifier):
                      columns.append(str(arg.name))

    elif isinstance(expression, exp.Expression):
        for child in expression.args.values():
                if isinstance(child, list):
                  for c in child:
                    _process_expression(c, tables, joins, aliases, columns, processor_type, query, depth + 1)
                else:
                  _process_expression(child, tables, joins, aliases, columns, processor_type, query, depth + 1)


def extract_tables_and_joins(parsed_statement: sqlglot.Expression, query: str) -> Dict[str, Any]:
    """Extract tables and join conditions using sqlglot."""
    logging.debug(f"extract_tables_and_joins: parsed_statement={parsed_statement}")
    tables = []
    joins = []
    aliases = {}

    if parsed_statement:
      for expression in parsed_statement.find_all(exp.From):
         for table in expression.args.values():
             _process_expression(table, tables, joins, aliases, [],"table", query)
    logging.debug(f"extract_tables_and_joins: returning tables={tables}, joins={joins}, aliases={aliases}")
    return {"Base Tables": tables, "Joins": joins, "Aliases": aliases}

def extract_where_columns(parsed_statement: sqlglot.Expression, query:str) -> List[str]:
    """Extract columns from WHERE clause using sqlglot."""
    logging.debug(f"extract_where_columns: parsed_statement={parsed_statement}")
    columns = []

    if parsed_statement:
      for expression in parsed_statement.find_all(exp.Where):
          for clause in expression.args.values():
             _process_expression(clause, [], [], {}, columns,"column", query)


    logging.debug(f"extract_where_columns: returning columns={columns}")
    return columns

def extract_group_by_columns(parsed_statement: sqlglot.Expression, query:str) -> List[str]:
    """Extract columns from GROUP BY clause using sqlglot."""
    logging.debug(f"extract_group_by_columns: parsed_statement={parsed_statement}")
    columns = []

    if parsed_statement:
        for expression in parsed_statement.find_all(exp.Group):
            for group in expression.args.values():
                _process_expression(group, [], [], {}, columns,"column", query)

    logging.debug(f"extract_group_by_columns: returning columns={columns}")
    return columns

def extract_sub_queries(parsed_statement: sqlglot.Expression, depth: int = 0) -> List[str]:
    """Extract sub-queries using sqlglot."""
    logging.debug(f"extract_sub_queries: parsed_statement={parsed_statement}, depth={depth}")
    if depth > 10:
        logging.debug("extract_sub_queries: max depth reached, stopping recursion")
        return []
    sub_queries = []

    if parsed_statement:
       for expression in parsed_statement.find_all(exp.Subquery):
         sub_queries.append(str(expression))
       for expression in parsed_statement.find_all(exp.Select):
         if isinstance(expression.parent, exp.Subquery) is False and isinstance(expression.parent, exp.CTE) is False:
           sub_queries.append(str(expression))
    logging.debug(f"extract_sub_queries: returning sub_queries={sub_queries}")
    return sub_queries


def map_aliases_to_columns(parsed_statement: sqlglot.Expression, query: str, depth: int = 0) -> Dict[str, str]:
    """Parse final SELECT and map aliases to base columns using sqlglot."""
    logging.debug(f"map_aliases_to_columns: parsed_statement={parsed_statement}, depth={depth}")
    if depth > 10:
       logging.debug("map_aliases_to_columns: max depth reached, stopping recursion")
       return {}
    aliases = {}

    if parsed_statement:
       for expression in parsed_statement.find_all(exp.Select):
           for select_exp in expression.expressions:
               if isinstance(select_exp, exp.Alias):
                  alias = str(select_exp.alias)
                  aliased_name = str(select_exp.this)
                  if alias and aliased_name:
                        aliases[alias] = aliased_name
    logging.debug(f"map_aliases_to_columns: returning aliases={aliases}")
    return aliases


def analyze_query(query: str, idx: int) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Analyze a single SQL query."""
    try:
        logging.info(f"Processing Query Index: {idx}")
        query = normalize_and_strip_comments(query)
        parsed_statement = parse_sql(query)

        # Extract metadata
        logging.debug(f"Main loop: Before extract_tables_and_joins")
        tables_joins = extract_tables_and_joins(parsed_statement, query)
        tables = tables_joins["Base Tables"]
        joins = tables_joins["Joins"]
        aliases = tables_joins["Aliases"]
        logging.debug(f"Main loop: Before extract_group_by_columns")
        group_by = extract_group_by_columns(parsed_statement, query)
        logging.debug(f"Main loop: Before extract_where_columns")
        where_columns = extract_where_columns(parsed_statement, query)
        logging.debug(f"Main loop: Before extract_ctes")
        ctes = extract_ctes(query)

        # Extract sub-queries
        logging.debug(f"Main loop: Before extract_sub_queries")
        sub_queries = extract_sub_queries(parsed_statement)

        # Analyze sub-queries
        sub_query_metadata = []
        for sub_idx, sub_query in enumerate(sub_queries, start=1):
            sub_parser = parse_sql(sub_query)
            sub_tables = []
            sub_columns = []
            sub_ctes = extract_ctes(sub_query)
            if sub_parser:
              _process_expression(sub_parser, sub_tables, [], {}, sub_columns, "table", sub_query)

            sub_query_metadata.append({
                "Sub-Query Index": sub_idx,
                "Tables": sub_tables,
                "Columns": sub_columns,
                "CTEs": sub_ctes,
                "Sub-Query": sub_query
            })
            table_counter.update(sub_tables)
            column_counter.update(sub_columns)
            cte_counter.update(sub_ctes)


        # Map aliases in main query
        logging.debug(f"Main loop: Before map_aliases_to_columns")
        select_aliases = map_aliases_to_columns(parsed_statement, query)

        # Merge aliases dictionaries. Select aliases will take preference
        merged_aliases = aliases.copy()
        merged_aliases.update(select_aliases)

        # Store main query and sub-query results
        query_result = {
            "Query Index": idx,
            "Tables": tables,
            "Joins": joins,
            "Group By": group_by,
            "Where Columns": where_columns,
            "CTEs": ctes,
            "Aliases": merged_aliases,
            "Sub-Queries": sub_query_metadata,
            "Query": query
        }
        table_counter.update(tables)
        column_counter.update(group_by + where_columns)
        cte_counter.update(ctes)
        return query_result, []

    except Exception as e:
        logging.error(f"Error processing query {idx}: {e}, query='{query}'")
        return {}, [{"Query Index": idx, "Error": str(e), "Query": query}]

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Analyze SQL queries from an Excel file.")
    parser.add_argument("--file_path", type=str, required=True, help="Path to the Excel file.")
    parser.add_argument("--sheet_name", type=str, required=True, help="Name of the sheet containing SQL queries.")
    parser.add_argument("--output_file", type=str, default=OUTPUT_FILE, help="Output file name (default: oracle_sql_parsing_results.xlsx).")

    args = parser.parse_args()
    FILE_PATH = args.file_path
    SHEET_NAME = args.sheet_name
    OUTPUT_FILE = args.output_file

    # Load SQL queries from Excel file
    data = pd.ExcelFile(FILE_PATH)
    df = data.parse(SHEET_NAME)
    sql_queries = df['table_query']

    # Initialize counters and storage
    table_counter = Counter()
    column_counter = Counter()
    cte_counter = Counter()
    detailed_results = []
    error_logs = []

    # Analyze each query
    for idx, query in enumerate(sql_queries, start=1):
        query_result, query_error_logs = analyze_query(query, idx)
        if query_result:
            detailed_results.append(query_result)
        if query_error_logs:
           error_logs.extend(query_error_logs)

    # Convert results to DataFrames
    detailed_df = pd.DataFrame(detailed_results)
    error_df = pd.DataFrame(error_logs)

    # Aggregate critical elements
    critical_tables = pd.DataFrame(table_counter.items(), columns=["Table", "Frequency"]).sort_values(by="Frequency", ascending=False).head(TOP_N)
    critical_columns = pd.DataFrame(column_counter.items(), columns=["Column", "Frequency"]).sort_values(by="Frequency", ascending=False).head(TOP_N)
    critical_ctes = pd.DataFrame(cte_counter.items(), columns=["CTE", "Frequency"]).sort_values(by="Frequency", ascending=False).head(TOP_N)

    # Save results to Excel
    with pd.ExcelWriter(OUTPUT_FILE) as writer:
        detailed_df.to_excel(writer, sheet_name="Detailed Results", index=False)
        critical_tables.to_excel(writer, sheet_name="Critical Tables", index=False)
        critical_columns.to_excel(writer, sheet_name="Critical Columns", index=False)
        critical_ctes.to_excel(writer, sheet_name="Critical CTEs", index=False)
        if not error_df.empty:
            error_df.to_excel(writer, sheet_name="Problematic Queries", index=False)

        # Add a query level analysis sheet. This adds a few columns to the details sheet to make it more searchable
        if not detailed_df.empty:
            query_level_df = detailed_df.copy()
            query_level_df['Has_Subqueries'] = detailed_df['Sub-Queries'].apply(lambda x: len(x) > 0)
            query_level_df['Has_Where_Clause'] = detailed_df['Where Columns'].apply(lambda x: len(x) > 0)
            query_level_df['Has_GroupBy'] = detailed_df['Group By'].apply(lambda x: len(x) > 0)
            query_level_df['Has_CTEs'] = detailed_df['CTEs'].apply(lambda x: len(x) > 0)
            query_level_df.to_excel(writer, sheet_name="Query-Level Analysis", index=False)

    print(f"Comprehensive parsing results saved to {OUTPUT_FILE}")
