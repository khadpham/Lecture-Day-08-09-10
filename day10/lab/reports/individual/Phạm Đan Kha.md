> # Individual Report — AI in Action (Lab Day 10)
> **Name:** Phạm Đan Kha  
> **Role:** Embed Owner  
> 
> ### 1. Specific Responsibilities
> As the Embed Owner for this pipeline, my primary responsibility was managing the interface between the cleaned data artifact and our local ChromaDB vector store. I managed the `cmd_embed_internal` function within `etl_pipeline.py`, ensuring that the ingestion of text chunks into the `day10_kb` collection was seamless, idempotent, and perfectly mirrored the most recent output of the data cleaning team.
> 
> ### 2. Key Technical Decision: Idempotent Upserts and Pruning
> A critical data observability requirement is that rerunning a pipeline should not artificially bloat the downstream database. If we simply used `.add()` methods, multiple runs would duplicate the exact same chunks, destroying our retrieval accuracy. 
> 
> I implemented a strict idempotent strategy using two methods. First, I utilised ChromaDB's `.upsert()` function, mapping the unique `chunk_id` from the cleaned CSV directly to the vector store's internal ID. This ensures that if a chunk's text or metadata changes (e.g., a policy date is updated), the vector is overwritten rather than duplicated. Second, I introduced a pruning mechanism: the script calculates the set difference between existing vector IDs and the incoming `chunk_id`s (`prev_ids - set(ids)`). Any stale IDs that no longer exist in the freshly cleaned data are actively deleted (`col.delete()`). This guarantees that our vector index acts as an exact snapshot of the publish boundary.
> 
> ### 3. Anomaly Detected and Addressed
> During the initial execution of the embedding phase, our pipeline generated a startling log from the `sentence-transformers` library: `embeddings.position_ids | UNEXPECTED`. 
> 
> Initially, this looked like a critical failure in the model weight loading process. However, after investigating the model architecture, I identified this as a known, benign artifact when loading the `all-MiniLM-L6-v2` model from the Hugging Face Hub using the current version of the library. Because the model architecture strictly ignores these specific position IDs when loaded into this context, I made the informed decision to document this in our runbook as a non-fatal warning rather than halting the pipeline. It is an operational reality of using pre-trained weights, and the actual embedding function proceeded successfully.
> 
> ### 4. Before/After Evidence (Log Extraction)
> The success of the embedding logic is proven by the successful synchronisation in the logs.
> * **Evidence of successful final state:** `embed_upsert count=7 collection=day10_kb`
> 
> The pipeline successfully took the exact 7 records outputted by the cleaning team and synchronised them with Chroma without duplicating the quarantined records.
> 
> ### 5. Proposed 2-Hour Improvement
> If I had two more hours, I would replace the local, file-based ChromaDB instance with a persistent client connected to a dedicated vector database server (like Milvus or Qdrant via Docker). Currently, storing the database in `./chroma_db` is fine for local prototyping, but in a production environment with multiple Data Scientists running concurrent ETL jobs, we would face file-locking conflicts. A centralised server would resolve this and improve our CI/CD integration.

