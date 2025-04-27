from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from query_generator import generate_sql_query, execute_query
from database import list_databases, list_tables, list_columns

# Initialize FastAPI app
app = FastAPI()

class QueryRequest(BaseModel):
    query: str

@app.post("/generate_sql/")
async def generate_sql(request: QueryRequest):
    """Generate SQL query from natural language input."""
    sql_query = generate_sql_query(request.query)
    if not sql_query:
        raise HTTPException(status_code=500, detail="Failed to generate SQL")
    return {"sql_query": sql_query}

@app.post("/execute_sql/")
async def execute_sql(request: QueryRequest):
    """Execute a given SQL query and return results."""
    sql_query = request.query
    try:
        results = execute_query(sql_query)
        
        if results is None:
            raise HTTPException(status_code=500, detail="Error executing query")
        
        # If error is present in results, return it directly
        if "error" in results:
            raise HTTPException(status_code=500, detail=results["error"])
        
        # Ensure proper JSON serialization
        serialized_results = results["results"] if isinstance(results["results"], list) else []
        
        return {
            "results": serialized_results,
            "optimization_tips": results.get("optimization_tips", "")
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/list_databases/")
def api_list_databases():
    return list_databases()

@app.get("/list_tables/{database_name}")
def api_list_tables(database_name: str):
    return list_tables(database_name)

@app.get("/list_columns/{database_name}/{table_name}")
def api_list_columns(database_name: str, table_name: str):
    return list_columns(database_name, table_name)

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
