## **OraQx**

OraQx is the resultant repo of possible solutions and current-state script versions designed to facilitate the identification and analysis of critical tables and columns by analyzing SQL queries w/o accessing the DB. It offers a variety of workflows and tools, ranging from static analysis to dynamic database-assisted methods, to cater to different technical requirements and environments.

## Purpose

The primary goal of OraQx is to streamline the process of understanding and optimizing database structures by identifying key tables, columns, CTEs, and other such metadata frequently accessed or crucial for performance. This can be particularly useful for tasks such as database migration, query optimization, and data warehousing.

## Features

OraQx provides a diverse set of workflows, each tailored to different scenarios and levels of technical expertise:

### Top-Tier Workflows

1. **Python-Based Static Analysis and Metadata Extraction**
   - **Details:** Extracts and analyzes SQL queries using Python libraries to identify table and column references.
   - **Tools:** Python, PySpark, sqlparse, SQLGlot, sql-metadata, SQLFluff, Pandas, matplotlib, seaborn.

2. **LLM-Augmented Static Analysis**
   - **Details:** Uses Large Language Models (LLMs) to provide context-aware analysis of SQL queries.
   - **Tools:** Python, sqlparse, SQLGlot, sql-metadata, LLMs (e.g., OpenAI, Google's AI Studio), Epic Clarity Documentation, Tableau Workbook Metadata.

3. **Database-Assisted Query Analysis**
   - **Details:** Executes SQL queries against an Oracle database to gather execution statistics and logs for analysis.
   - **Tools:** Oracle Database, SQL Server Profiler, custom scripting for log analysis.

4. **Snowflake Migration Assessment Workflow**
   - **Details:** Combines static analysis with dynamic analysis in a Snowflake environment to assess query execution patterns.
   - **Tools:** Python, sqlparse, SQLGlot, sql-metadata, Snowflake.

5. **End-to-End Migration with Specialized Tools**
   - **Details:** Utilizes dedicated migration tools to analyze and prioritize Oracle-to-Snowflake migrations.
   - **Tools:** SnowConvert by Mobilize.Net, Matillion, Fivetran, Azure Data Factory.

6. **Azure-Centric Data Analysis Workflow**
   - **Details:** Ingests and processes SQL queries using Azure services to identify critical database elements.
   - **Tools:** Azure Data Lake Storage, Azure Blob Storage, Azure Data Factory, Azure Synapse Analytics, Azure SQL Database, Azure Machine Learning, Power BI.

7. **Epic and Tableau Integrated Analysis**
   - **Details:** Leverages Epic Clarity/Caboodle Data Dictionaries and Tableau metadata to understand data usage patterns.
   - **Tools:** Epic Clarity/Caboodle Data Dictionaries, Tableau, FHIR Analytics, FHIR Connect.

### Mid-Tier Workflows

8. **Java-Based Static Analysis**
   - **Details:** Uses Java libraries to parse and analyze SQL queries.
   - **Tools:** Java, jsqlparser.

9. **Static Code Analysis Tools for SQL**
   - **Details:** Analyzes SQL queries for syntax and standards using tools like SonarQube.
   - **Tools:** SonarQube, sqlhint.

10. **Custom Scripting with ANTLR**
    - **Details:** Creates custom SQL parsers using ANTLR or similar tools for specific needs.
    - **Tools:** ANTLR, custom scripting (Python, Java).

### Lower-Tier Workflows

11. **Snowflake-Specific Feature Analysis**
    - **Details:** Utilizes Snowflake features for post-migration optimization.
    - **Tools:** Snowflake (Time Travel, Zero-Copy Cloning, Materialized Views).

12. **Basic Scripting with Regular Expressions**
    - **Details:** Extracts table and column names using simple pattern matching.
    - **Tools:** Python, re module, PowerShell.

13. **SQL Linter and Formatter Workflow**
    - **Details:** Standardizes SQL queries before further analysis.
    - **Tools:** SQLFluff, sqlformat.

14. **IDE Extensions for Visual Analysis**
    - **Details:** Uses IDE extensions for basic SQL syntax highlighting.
    - **Tools:** VS Code, Visual Studio.

15. **Data Visualization for Metadata**
    - **Details:** Visualizes relationships and usage patterns of database elements.
    - **Tools:** LightGraph, matplotlib.pyplot.

16. **Vector Database and Reranking**
    - **Details:** Uses advanced techniques to embed and rerank database elements.
    - **Tools:** Vector databases (e.g., Pinecone, Weaviate), embedding models.

17. **Simple Analysis with Excel**
    - **Details:** Manually identifies and counts database elements using Excel.
    - **Tools:** Microsoft Excel, Python.

18. **Cloud-Based Spreadsheet Analysis**
    - **Details:** Analyzes SQL queries using Google Sheets.
    - **Tools:** Google Sheets, Google Apps Script.

19. **GitHub CodeSpaces/Repositories**
    - **Details:** Manages scripts and resources for SQL query analysis.
    - **Tools:** GitHub CodeSpaces, GitHub Repositories.

## Contributions

Contributions to OraQx are welcome. Please follow the standard GitHub workflow for contributing code, including forking the repository, making changes, and submitting pull requests.

## License

OraQx is licensed under the Apache 2.0 License. See the LICENSE file for more details.
