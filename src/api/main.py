from fastapi import FastAPI, status, HTTPException
from fastapi.requests import Request
from fastapi.responses import StreamingResponse,JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from src.api.retrieve_data import retrieve_data
from src.api.call_ai_server import create_thread, stream_from_ai_server
from dotenv import load_dotenv
load_dotenv(".env")

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/aireport/stream")
async def stream_handler(request: Request):
    try:
        body = await request.json()
        agent = body.get("agent")
        gte = body.get("gte")
        lte = body.get("lte")

        if not agent or gte is None or lte is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required parameters")

        retrieve_data(agent, gte, lte)
        thread_id = create_thread()
        if not thread_id:
            return JSONResponse({"error": "Failed to create thread"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return StreamingResponse(
            stream_from_ai_server(thread_id),
            media_type="text/event-stream",
            status_code=200
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=status.HTTP_502_BAD_GATEWAY)