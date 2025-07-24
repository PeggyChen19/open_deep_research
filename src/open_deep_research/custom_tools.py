import os
import faiss
from dotenv import load_dotenv

from langchain.tools import Tool
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.schema import Document
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SimilarityPostprocessor

# Load OpenAI key from env
load_dotenv("app.env")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

INDEX = None

def build_index():
    global INDEX
    if INDEX is not None:
        return INDEX

    with open("src/open_deep_research/data/input.txt", "r", encoding="utf-8") as f:
        raw_logs = f.read()

    embed_model = OpenAIEmbedding(model="text-embedding-3-large")

    chunks = raw_logs.split("---")
    docs = [Document(text=chunk.strip()) for chunk in chunks if chunk.strip()]
    
    parser = SimpleNodeParser()
    nodes = parser.get_nodes_from_documents(docs)
    for i, node in enumerate(nodes):
        node.node_id = str(i)

    faiss_index = faiss.IndexFlatL2(3072)
    vector_store = FaissVectorStore(faiss_index=faiss_index)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    INDEX = VectorStoreIndex(nodes, storage_context=storage_context, embed_model=embed_model)
    return INDEX

def query_log_index(query: str) -> str:
    index = build_index()

    retriever = VectorIndexRetriever(index=index, similarity_top_k=5)
    query_engine = RetrieverQueryEngine(
        retriever=retriever,
        node_postprocessors=[SimilarityPostprocessor(similarity_cutoff=0.5)]
    )

    response = query_engine.query(query)
    results = [node.get_content().strip() for node in response.source_nodes if node.get_content().strip()]

    if not results:
        return "No relevant log entries found."
    return "\n---\n".join(results)

query_logs_tool = Tool.from_function(
    name="RetrieveEventLogChunks",
    description="Retrieves semantically relevant chunks from an indexed Windows Event Log file. Each query should be phrased clearly and specifically (e.g., Event ID, Time, Computer, TargetUserName, LogonType, IpAddress, ServiceName).",
    func=query_log_index
)