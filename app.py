from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import time
import os
from agent_graph import SimpleAgent
from document_gen import DocumentGenerator

# Initialize the  application and document generator.
app = FastAPI(title="AI Agent API")
doc_gen = DocumentGenerator()


#incoming request schema
class AgentRequest(BaseModel):
    request: str
    model_name: Optional[str] = "openai/gpt-oss-120b"  

#response schema
class AgentResponse(BaseModel):
    request: str
    tasks: List[str]
    results: Dict[str, Any]
    final_output: str
    document_path: str
    execution_time: float
    status: str
    model_used: str

#request to the workflow, Process user request and generate document.
@app.post("/agent", response_model=AgentResponse)
async def process_request(req: AgentRequest):
    
    try:
        start_time = time.time()
        
        # Initialize agent with specified model
        agent = SimpleAgent(model_name=req.model_name)
        
        # Process through agent
        result = agent.process_request(req.request)
        
        # Generate document
        doc_path = doc_gen.create_document(
            content=result.get("final_output", ""),
            title=f"Document: {req.request[:50]}..."
        )
        
        execution_time = time.time() - start_time
        
        return AgentResponse(
            request=req.request,
            tasks=result.get("tasks", []),
            results=result.get("results", {}),
            final_output=result.get("final_output", ""),
            document_path=doc_path,
            execution_time=execution_time,
            status="success",
            model_used=req.model_name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#  Download generated document
@app.get("/download/{filename}")
async def download_document(filename: str):
  
    filepath = os.path.join("generated_docs", filename)
    if os.path.exists(filepath):
        return FileResponse(
            filepath,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=filename
        )
    raise HTTPException(status_code=404, detail="Document not found")

#Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "model": "openai/gpt-oss-120b"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)