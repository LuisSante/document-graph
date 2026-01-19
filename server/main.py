import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from api import documents

app = FastAPI()

origins = [
    "http://localhost:5173", 
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router, prefix="/api/v1")

@app.get("/")
def home():
    return {"message": "Hola desde FastAPI"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/documents/init")
def home():
    return {"message": "Document initialization endpoint"}