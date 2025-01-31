from fastapi import FastAPI, Depends, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
import sqlite3
import json
import os

app = FastAPI()
DB_NAME = "transcriptions.db"
UPLOAD_FOLDER = "uploads"

# Ensure the uploads directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    """Establishes database connection."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Allows dictionary-style row access
    return conn

# Create tables for transcriptions and segments
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transcriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        text TEXT,
        language TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS segments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transcription_id INTEGER,
        start REAL,
        end REAL,
        text TEXT,
        tokens TEXT,
        temperature REAL,
        avg_logprob REAL,
        compression_ratio REAL,
        no_speech_prob REAL,
        confidence REAL,
        words TEXT,
        FOREIGN KEY (transcription_id) REFERENCES transcriptions(id) ON DELETE CASCADE
    );
    """)
    
    conn.commit()
    conn.close()
    print("Database tables are ready.")

create_tables()

@app.post("/upload/")
async def upload_audio(file: UploadFile = File(...)):
    """Handles file upload and saves metadata."""
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    
    # Save the uploaded file
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Insert into transcriptions table (initial metadata only)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO transcriptions (filename, text, language) VALUES (?, ?, ?)", 
                   (file.filename, "", "unknown"))
    transcription_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return JSONResponse(content={"message": "File uploaded successfully", "transcription_id": transcription_id})

@app.get("/transcriptions")
def get_transcriptions():
    """Fetch all transcriptions."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transcriptions")
    transcriptions = cursor.fetchall()
    conn.close()
    return [{"id": row["id"], "filename": row["filename"], "text": row["text"], "language": row["language"]} for row in transcriptions]

@app.get("/transcriptions/{transcription_id}/segments")
def get_segments(transcription_id: int):
    """Fetch segments for a given transcription."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM segments WHERE transcription_id = ?", (transcription_id,))
    segments = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row["id"],
            "start": row["start"],
            "end": row["end"],
            "text": row["text"],
            "tokens": json.loads(row["tokens"]),
            "temperature": row["temperature"],
            "avg_logprob": row["avg_logprob"],
            "compression_ratio": row["compression_ratio"],
            "no_speech_prob": row["no_speech_prob"],
            "confidence": row["confidence"],
            "words": json.loads(row["words"])
        }
        for row in segments
    ]

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    """Serve the frontend HTML page."""
    with open("index.html", "r") as f:
        return f.read()

# Start the server with: uvicorn server:app --reload
