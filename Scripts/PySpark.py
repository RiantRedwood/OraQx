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
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col, explode, lit, struct, map_from_entries
from pyspark.sql.types import ArrayType, StringType, StructType, StructField

# Set DEBUG to True for verbose logging, False otherwise
DEBUG = False

# Configure logging
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
FILE_PATH = r"C:\Users\joshm\source\repos\PolyQx\data_raw\data.xlsx"
SHEET_NAME = "Table Sample"
OUTPUT_FILE = "oracle_sql_parsing_results.xlsx"
TOP_N = 3 # Changed from 10 to 3

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
        return parse_one(query, dialect="oracle")
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
    elif isinstance(expression, exp.Window):
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

def extract_query_hints(query: str) -> str:
    """Extract hints from SQL queries using regex."""
    hints = re.findall(HINT_REGEX, query)
    return ' '.join(hints) if hints else None

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

def process_query(row):
    """Process a single SQL query."""
    query_id = row.get("Content ID") or row.get("Query ID") or "N/A"
    query = row.table_query
    try:
        logging.info(f"Processing Query ID: {query_id}")
        query = normalize_and_strip_comments(query)
        parsed_statement = parse_sql(query)
        query_hints = extract_query_hints(query)

        if parsed_statement:
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

          # Map aliases in main query
          logging.debug(f"Main loop: Before map_aliases_to_columns")
          select_aliases = map_aliases_to_columns(parsed_statement, query)

          # Merge aliases dictionaries. Select aliases will take preference
          merged_aliases = aliases.copy()
          merged_aliases.update(select_aliases)

          # Store main query and sub-query results
          query_result = {
              "Query ID": query_id,
              "Tables": tables,
              "Joins": joins,
              "Group By": group_by,
              "Where Columns": where_columns,
              "CTEs": ctes,
              "Aliases": merged_aliases,
              "Sub-Queries": sub_query_metadata,
              "Query": query,
               "Hints": query_hints
          }
          return query_result, None
        else:
          return None,  {"Query ID": query_id, "Error": f"Parsing error with sqlglot.", "Query": query}
    except Exception as e:
        logging.error(f"Error processing query {query_id}: {e}, query='{query}'")
        return None, {"Query ID": query_id, "Error": str(e), "Query": query}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Analyze SQL queries from an Excel file using PySpark.")
    parser.add_argument("--file_path", type=str, default = FILE_PATH, help="Path to the Excel file.")
    parser.add_argument("--sheet_name", type=str, default= SHEET_NAME, help="Name of the sheet containing SQL queries.")
    parser.add_argument("--output_file", type=str, default=OUTPUT_FILE, help="Output file name (default: oracle_sql_parsing_results.xlsx).")

    args = parser.parse_args()
    FILE_PATH = args.file_path
    SHEET_NAME = args.sheet_name
    OUTPUT_FILE = args.output_file

    # Initialize Spark session
    spark = SparkSession.builder.appName("SQLAnalyzer").getOrCreate()

    # Load SQL queries from Excel to pandas, then to Spark
    excel_data = pd.ExcelFile(FILE_PATH)
    df = excel_data.parse(SHEET_NAME)
    sql_queries_df = spark.createDataFrame(df)

    # Identify the Query ID/Content ID column
    id_column = "Content ID" if "Content ID" in df.columns else "Query ID" if "Query ID" in df.columns else None


    # Process each query
    process_query_udf = udf(process_query, StructType([
        StructField("query_result",  StructType([
            StructField("Query ID",StringType(),True),
            StructField("Tables", ArrayType(StringType()), True),
            StructField("Joins", ArrayType(StringType()), True),
            StructField("Group By", ArrayType(StringType()), True),
            StructField("Where Columns", ArrayType(StringType()), True),
            StructField("CTEs",  StringType(), True),
            StructField("Aliases", StringType(),True),
            StructField("Sub-Queries", ArrayType(StructType([
                StructField("Sub-Query Index", StringType(),True),
                StructField("Tables", ArrayType(StringType()), True),
                StructField("Columns", ArrayType(StringType()), True),
                StructField("CTEs",  StringType(), True),
                StructField("Sub-Query", StringType(),True)])),True),
            StructField("Query", StringType(),True),
             StructField("Hints", StringType(), True)
        ]),True),
         StructField("error_log",  StructType([
             StructField("Query ID", StringType(),True),
             StructField("Error", StringType(),True),
             StructField("Query", StringType(),True)]),True)
    ]))

    id_col = col(id_column) if id_column else lit("N/A").alias("Query ID")
    processed_df = sql_queries_df.withColumn("processed_data", process_query_udf(struct(id_col, col("table_query"))))

    # Split results into successful and failed queries
    results_df = processed_df.select("processed_data.query_result").where("processed_data.query_result is not null")
    error_df = processed_df.select("processed_data.error_log").where("processed_data.error_log is not null")

    # Flatten the results dataframe and prepare for pandas
    flattened_results_df = results_df.select("query_result.*").toPandas()

    #Collect and format error logs
    error_logs = error_df.select("error_log.*").toPandas() if not error_df.rdd.isEmpty() else pd.DataFrame()

    # Aggregate critical elements
    table_counts = results_df.select(explode("Tables").alias("Table")).groupBy("Table").count().orderBy("count", ascending=False).limit(TOP_N).toPandas()
    column_counts = results_df.select(explode("Where Columns").alias("Column")).groupBy("Column").count().orderBy("count", ascending=False).limit(TOP_N).toPandas()
    cte_counts = results_df.select(explode(map_from_entries("CTEs")).alias("CTE")).groupBy("CTE").count().orderBy("count", ascending=False).limit(TOP_N).toPandas()

    # Save results to Excel
    with pd.ExcelWriter(OUTPUT_FILE) as writer:
        flattened_results_df.to_excel(writer, sheet_name="Detailed Results", index=False)
        table_counts.to_excel(writer, sheet_name="Critical Tables", index=False)
        column_counts.to_excel(writer, sheet_name="Critical Columns", index=False)
        cte_counts.to_excel(writer, sheet_name="Critical CTEs", index=False)
        if not error_logs.empty:
            error_logs.to_excel(writer, sheet_name="Problematic Queries", index=False)

        # Add a query level analysis sheet. This adds a few columns to the details sheet to make it more searchable
        if not flattened_results_df.empty:
            query_level_df = flattened_results_df.copy()
            query_level_df['Has_Subqueries'] = flattened_results_df['Sub-Queries'].apply(lambda x: len(x) > 0)
            query_level_df['Has_Where_Clause'] = flattened_results_df['Where Columns'].apply(lambda x: len(x) > 0)
            query_level_df['Has_GroupBy'] = flattened_results_df['Group By'].apply(lambda x: len(x) > 0)
            query_level_df['Has_CTEs'] = flattened_results_df['CTEs'].apply(lambda x: len(x) > 0)
            query_level_df.to_excel(writer, sheet_name="Query-Level Analysis", index=False)

    print(f"Comprehensive parsing results saved to {OUTPUT_FILE}")
    spark.stop()
