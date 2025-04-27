import os
import google.generativeai as genai
import sqlparse
import re
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from database import engine, list_databases, list_tables, list_columns

# Load environment variables
load_dotenv()

# Gemini API Key
gemini_api_key = os.getenv("gemini.api_key")
genai.configure(api_key=gemini_api_key)
# Limits to avoid token limit issues
MAX_TABLES = 5
MAX_COLUMNS_PER_TABLE = 5


def clean_sql_output(response_text):
    """Extracts SQL query from AI response."""
    clean_query = re.sub(r"```sql\n(.*?)\n```", r"\1", response_text, flags=re.DOTALL)
    sql_match = re.search(r"SELECT .*?;", clean_query, re.DOTALL | re.IGNORECASE)
    return sql_match.group(0) if sql_match else clean_query.strip()

def get_limited_schema():
    """Fetches a reduced database schema to fit within OpenAI's token limits."""
    schema = {}
    databases = list_databases().get("databases", [])  
    for db in databases:
        schema[db] = {}
        tables = list_tables(db).get("tables", [])[:MAX_TABLES]
        for table in tables:
            schema[db][table] = list_columns(db, table).get("columns", [])[:MAX_COLUMNS_PER_TABLE]

    return schema


def generate_sql_query(nl_query):
    """Converts a natural language query into an optimized SQL query using Google Gemini."""
    schema = get_limited_schema()
    schema_text = "\n".join([
        f"{db}.{table}: {', '.join(columns)}" for db, tables in schema.items() for table, columns in tables.items()
    ])

    prompt = f"""
    You are an SQL expert. Convert the following natural language query into an optimized MySQL query.
    - Use indexing where applicable.
    - Prefer JOINS over subqueries.
    - Use GROUP BY for aggregations if needed.

    Database Schema (Limited View):
    {schema_text}

    User Query: {nl_query}

    SQL Query:
    """

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        raw_sql_query = response.text.strip()
        return clean_sql_output(raw_sql_query)
    except Exception as e:
        return f"Error generating SQL query: {e}"

def execute_query(sql_query):
    """Executes a validated and optimized SQL query and returns JSON-serializable results."""
    try:
        with engine.connect() as connection:
            result = connection.execute(text(sql_query))
            # Check if the statement returns rows
            if result.returns_rows:
                rows = result.fetchall()
                column_names = result.keys()
                formatted_results = [dict(zip(column_names, row)) for row in rows]
                return {"results": formatted_results}
            else:
                # For INSERT/UPDATE/DELETE/DDL, commit if needed and return affected row count
                connection.commit()
                return {"results": [], "message": f"Query executed successfully. Rows affected: {result.rowcount}"}
    except SQLAlchemyError as e:
        return {"error": str(e)}