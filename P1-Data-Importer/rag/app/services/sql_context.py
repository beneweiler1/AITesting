from typing import List, Dict
import json
from ..db import get_all_schemas, get_sample_data, execute_sql_query
from .llm import chat_once

def build_schema_prompt(question: str, schemas: Dict, include_samples: bool = True) -> str:
    """Build a prompt with database schema for SQL generation"""
    
    schema_text = "DATABASE SCHEMA:\n\n"
    
    for table_name, schema in schemas.items():
        cols = []
        for col in schema["columns"]:
            col_def = f"{col['name']} {col['type']}"
            if not col.get("nullable", True):
                col_def += " NOT NULL"
            cols.append(col_def)
        
        schema_text += f"TABLE {table_name}:\n"
        schema_text += "  " + "\n  ".join(cols) + "\n\n"
        
        # Include sample data
        if include_samples:
            try:
                sample_df = get_sample_data(table_name, limit=2)
                if not sample_df.empty:
                    schema_text += f"SAMPLE DATA FROM {table_name}:\n"
                    schema_text += sample_df.to_string(index=False) + "\n\n"
            except Exception:
                pass
    
    prompt = f"""You are a SQL expert. Given the database schema below, generate SQL queries to retrieve relevant data that would help answer the user's question.

{schema_text}

USER QUESTION: {question}

Generate 1-3 SQL queries that would retrieve the most relevant data to answer this question. 
For each query, explain what data it retrieves and why it's relevant.

Return your response in this JSON format:
{{
  "queries": [
    {{
      "sql": "SELECT ... FROM ...",
      "explanation": "This query retrieves...",
      "relevance": "This data is relevant because..."
    }}
  ],
  "reasoning": "Overall strategy for answering this question..."
}}

IMPORTANT: 
- Only use tables and columns that exist in the schema above
- Use proper SQL syntax for MySQL
- Limit results appropriately (e.g., LIMIT 100)
- Use JOINs when relationships between tables are clear
- Return ONLY valid JSON, no additional text
"""
    
    return prompt


def extract_json_from_response(response: str) -> dict:
    """Extract JSON from LLM response, handling markdown code blocks"""
    response = response.strip()
    
    # Try to find JSON in markdown code blocks
    if "```json" in response:
        start = response.find("```json") + 7
        end = response.find("```", start)
        response = response[start:end].strip()
    elif "```" in response:
        start = response.find("```") + 3
        end = response.find("```", start)
        response = response[start:end].strip()
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # Fallback: try to find JSON object in the response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
        raise


def retrieve_sql_context(question: str, model: str, selected_tables: List[str] = None) -> Dict:
    """
    Use an LLM to generate and execute SQL queries to retrieve relevant context
    
    Returns:
        {
            "context": ["formatted context strings"],
            "sources": [{"table": "...", "query": "...", "row_count": ...}],
            "queries_executed": [...],
            "reasoning": "..."
        }
    """
    
    # Get schemas
    all_schemas = get_all_schemas()
    
    # Filter to selected tables if specified
    if selected_tables:
        schemas = {k: v for k, v in all_schemas.items() if k in selected_tables}
    else:
        schemas = all_schemas
    
    if not schemas:
        return {
            "context": [],
            "sources": [],
            "queries_executed": [],
            "reasoning": "No tables available"
        }
    
    # Build prompt and get SQL queries from LLM
    prompt = build_schema_prompt(question, schemas, include_samples=True)
    
    try:
        llm_response = chat_once(model, prompt)
        parsed = extract_json_from_response(llm_response)
    except Exception as e:
        return {
            "context": [],
            "sources": [],
            "queries_executed": [],
            "reasoning": f"Failed to generate queries: {str(e)}",
            "error": str(e)
        }
    
    queries = parsed.get("queries", [])
    reasoning = parsed.get("reasoning", "")
    
    # Execute queries and collect results
    context_parts = []
    sources = []
    queries_executed = []
    
    for idx, query_info in enumerate(queries[:3]):  # Limit to 3 queries
        sql = query_info.get("sql", "")
        explanation = query_info.get("explanation", "")
        
        if not sql:
            continue
        
        try:
            # Execute the query
            df = execute_sql_query(sql)
            
            queries_executed.append({
                "sql": sql,
                "explanation": explanation,
                "row_count": len(df),
                "success": True
            })
            
            if not df.empty:
                # Format the data as context
                context_text = f"QUERY {idx + 1}: {explanation}\n"
                context_text += f"SQL: {sql}\n"
                context_text += f"RESULTS ({len(df)} rows):\n"
                context_text += df.to_csv(index=False)
                context_parts.append(context_text)
                
                # Track source
                sources.append({
                    "query_index": idx + 1,
                    "tables_used": extract_tables_from_sql(sql),
                    "row_count": len(df),
                    "explanation": explanation
                })
        
        except Exception as e:
            queries_executed.append({
                "sql": sql,
                "explanation": explanation,
                "error": str(e),
                "success": False
            })
    
    return {
        "context": context_parts,
        "sources": sources,
        "queries_executed": queries_executed,
        "reasoning": reasoning
    }


def extract_tables_from_sql(sql: str) -> List[str]:
    """Simple extraction of table names from SQL (basic parser)"""
    import re
    sql_upper = sql.upper()
    tables = []
    
    # Find FROM clauses
    from_pattern = r'FROM\s+`?(\w+)`?'
    tables.extend(re.findall(from_pattern, sql_upper, re.IGNORECASE))
    
    # Find JOIN clauses
    join_pattern = r'JOIN\s+`?(\w+)`?'
    tables.extend(re.findall(join_pattern, sql_upper, re.IGNORECASE))
    
    return list(set(tables))