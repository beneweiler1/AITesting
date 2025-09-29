from fastapi import APIRouter, HTTPException
from ..routers.vdb import vdb_search
from ..services.llm import chat_once
from ..config import DEFAULT_MODEL
from ..services.sql_context import retrieve_sql_context
import logging
import time

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/chat")
def chat(payload: dict):
    msg = str(payload.get("message") or "")
    model = str(payload.get("model") or DEFAULT_MODEL)
    use_rag = payload.get("use_rag", False)
    topk = int(payload.get("topk", 5))
    use_sql = payload.get("use_sql", False)
    selected_tables = payload.get("selected_tables", [])
    
    if not msg.strip():
        raise HTTPException(status_code=400, detail="message required")
    
    logger.info(f"[CHAT] Starting chat request - Question: '{msg[:100]}...'")
    logger.info(f"[CHAT] Config: use_rag={use_rag}, use_sql={use_sql}, model={model}, topk={topk}")
    
    t0 = time.time()
    debug_info = _initialize_debug_info(use_rag, use_sql, topk, model, msg, selected_tables)
    
    context_sections = []
    all_sources = {"files": [], "sql": []}
    
    # VDB retrieval
    if use_rag:
        vdb_context, vdb_sources, vdb_debug = _retrieve_vdb_context(msg, topk)
        if vdb_context:
            context_sections.append(vdb_context)
        all_sources["files"] = vdb_sources
        debug_info.update(vdb_debug)
    
    # SQL retrieval
    if use_sql:
        sql_context, sql_sources, sql_debug = _retrieve_sql_context_wrapper(msg, model, selected_tables)
        if sql_context:
            context_sections.append(sql_context)
        all_sources["sql"] = sql_sources
        debug_info.update(sql_debug)
    
    print(context_sections)
    # Build final prompt
    augmented_prompt = _build_final_prompt(msg, context_sections)
    debug_info["augmented_prompt"] = augmented_prompt
    
    # Get LLM response
    answer, llm_debug = _get_llm_response(model, augmented_prompt)
    debug_info.update(llm_debug)
    
    # Calculate total time
    total_time = round((time.time() - t0) * 1000.0, 1)
    debug_info["total_latency_ms"] = total_time
    logger.info(f"[CHAT] ✓ Total request completed in {total_time}ms")
    
    return {
        "answer": answer,
        "sources": all_sources,
        "debug": debug_info
    }


def _initialize_debug_info(use_rag, use_sql, topk, model, msg, selected_tables):
    """Initialize debug information dictionary"""
    return {
        "use_rag": use_rag,
        "use_sql": use_sql,
        "top_k": topk,
        "model": model,
        "original_message": msg,
        "selected_tables": selected_tables
    }


def _retrieve_vdb_context(query: str, topk: int):
    """
    Retrieve context from vector database
    
    Returns:
        tuple: (context_string, sources_list, debug_dict)
    """
    logger.info(f"[VDB] Starting vector database search (top_k={topk})")
    
    try:
        t_start = time.time()
        vdb_results = search_vector_db_internal(query, topk)
        elapsed_ms = round((time.time() - t_start) * 1000.0, 1)
        
        sources = vdb_results.get("sources", [])
        num_chunks = len(sources)
        
        logger.info(f"[VDB] ✓ Retrieved {num_chunks} chunks in {elapsed_ms}ms")
        
        # Log each retrieved chunk
        _log_vdb_chunks(sources)
        
        context = None
        if vdb_results.get("context"):
            context = "Context from Files:\n" + "\n\n".join(vdb_results["context"])
        
        debug = {
            "vdb_search_ms": elapsed_ms,
            "num_chunks_found": num_chunks
        }
        
        return context, sources, debug
        
    except Exception as e:
        logger.error(f"[VDB] ✗ Error during VDB search: {str(e)}")
        return None, [], {"vdb_error": str(e)}


def _log_vdb_chunks(sources):
    """Log details about retrieved VDB chunks"""
    for idx, source in enumerate(sources, 1):
        filename = source.get("filename", "unknown")
        chunk_id = source.get("chunk", "?")
        score = source.get("score", 0)
        text_preview = source.get("text", "")[:100]
        
        logger.info(f"[VDB]   Chunk {idx}: {filename} (chunk={chunk_id}, score={score:.4f})")
        logger.info(f"[VDB]   Preview: {text_preview}...")


def _retrieve_sql_context_wrapper(query: str, model: str, selected_tables: list):
    """
    Retrieve context from SQL database using LLM-generated queries
    
    Returns:
        tuple: (context_string, sources_list, debug_dict)
    """
    logger.info(f"[SQL] Starting SQL context retrieval (tables={selected_tables or 'all'})")
    
    try:
        t_start = time.time()
        sql_results = retrieve_sql_context(query, model, selected_tables)
        elapsed_ms = round((time.time() - t_start) * 1000.0, 1)
        
        num_queries = len(sql_results.get("queries_executed", []))
        logger.info(f"[SQL] ✓ Executed {num_queries} queries in {elapsed_ms}ms")
        logger.info(f"[SQL] Reasoning: {sql_results.get('reasoning', 'N/A')}")
        
        # Log each executed query
        _log_sql_queries(sql_results.get("queries_executed", []))
        
        context = None
        if sql_results.get("context"):
            context = "Context from Database:\n" + "\n\n".join(sql_results["context"])
        
        debug = {
            "sql_search_ms": elapsed_ms,
            "sql_queries_executed": num_queries,
            "sql_reasoning": sql_results.get("reasoning", ""),
            "sql_queries": sql_results.get("queries_executed", [])
        }
        
        return context, sql_results.get("sources", []), debug
        
    except Exception as e:
        logger.error(f"[SQL] ✗ Error during SQL retrieval: {str(e)}")
        return None, [], {"sql_error": str(e)}


def _log_sql_queries(queries_executed):
    """Log details about executed SQL queries"""
    for idx, query_info in enumerate(queries_executed, 1):
        success = query_info.get("success", False)
        status = "✓" if success else "✗"
        sql_query = query_info.get("sql", "")
        explanation = query_info.get("explanation", "")
        
        if success:
            row_count = query_info.get("row_count", 0)
            logger.info(f"[SQL]   {status} Query {idx}: {explanation}")
            logger.info(f"[SQL]      SQL: {sql_query[:200]}...")
            logger.info(f"[SQL]      Retrieved {row_count} rows")
        else:
            error = query_info.get("error", "unknown")
            logger.error(f"[SQL]   {status} Query {idx} FAILED: {explanation}")
            logger.error(f"[SQL]      SQL: {sql_query[:200]}...")
            logger.error(f"[SQL]      Error: {error}")


def _build_final_prompt(question: str, context_sections: list):
    """
    Build the final prompt with all retrieved context
    
    Args:
        question: Original user question
        context_sections: List of context strings from different sources
        
    Returns:
        str: Final augmented prompt
    """
    if context_sections:
        context_block = "\n\n---\n\n".join(context_sections)
        augmented_prompt = f"Use the provided context to answer.\n\n{context_block}\n\nQuestion:\n{question}\n\nAnswer:"
        
        logger.info(f"[PROMPT] Built augmented prompt with {len(context_sections)} context section(s)")
        logger.info(f"[PROMPT] Total prompt length: {len(augmented_prompt)} characters")
        
        return augmented_prompt
    else:
        logger.info(f"[PROMPT] No context retrieved, using original question")
        return question


def _get_llm_response(model: str, prompt: str):
    """
    Get response from LLM
    
    Returns:
        tuple: (answer_string, debug_dict)
    """
    logger.info(f"[LLM] Sending request to model: {model}")
    
    t_start = time.time()
    answer = chat_once(model, prompt)
    elapsed_ms = round((time.time() - t_start) * 1000.0, 1)
    
    logger.info(f"[LLM] ✓ Generated response in {elapsed_ms}ms")
    logger.info(f"[LLM] Response preview: {answer[:150]}...")
    
    debug = {
        "llm_response_ms": elapsed_ms
    }
    
    return answer, debug


def search_vector_db_internal(query: str, k: int = 2):
    """Search the vector database using the internal /search endpoint"""
    payload = {"q": query, "k": k}
    results = vdb_search(payload)
    
    hits = results.get("results", [])
    
    # Format results
    context_chunks = []
    sources = []
    
    for hit in hits:
        meta = hit.get("meta", {})
        text = hit.get("text", "")
        
        context_chunks.append(
            f"[file:{meta.get('filename','')} id:{meta.get('file_id')} "
            f"chunk:{meta.get('chunk')}] {text}"
        )
        
        sources.append({
            "file_id": meta.get("file_id"),
            "filename": meta.get("filename"),
            "chunk": meta.get("chunk"),
            "score": hit.get("score"),
            "text": text
        })
    
    return {
        "context": context_chunks,
        "sources": sources
    }


def build_rag_prompt(question: str, vdb_results: dict):
    """Build the RAG prompt with context"""
    context_chunks = vdb_results.get("context", [])
    
    if not context_chunks:
        return question
    
    context_block = "Context Files:\n" + "\n\n".join(context_chunks)
    
    return (
        f"Use the provided context to answer.\n\n"
        f"{context_block}\n\n"
        f"Question:\n{question}\n\n"
        f"Answer:"
    )