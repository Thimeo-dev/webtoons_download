import os
import glob
import subprocess
import shutil
import re
import asyncio
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

app = FastAPI(title="Webtoon Downloader Live Pro")

DOWNLOAD_DIR = os.path.join(os.getcwd(), "temp_downloads")
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

class DownloadRequest(BaseModel):
    url: str

@app.get("/")
async def read_index():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    raise HTTPException(status_code=404, detail="Fichier index.html introuvable")

@app.get("/progress")
async def progress_stream(url: str = Query(...)):
    """Démarre le téléchargement et envoie la progression en temps réel au navigateur"""
    async def event_generator():
        if os.path.exists(DOWNLOAD_DIR):
            shutil.rmtree(DOWNLOAD_DIR)
        os.makedirs(DOWNLOAD_DIR)

        # On lance l'outil en récupérant le flux textuel de sa progression
        cmd = ["webtoon-downloader", url, "--save-as", "cbz", "--out", DOWNLOAD_DIR]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Lecture de la sortie de la commande en temps réel
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                
                decoded_line = line.decode('utf-8', errors='ignore').strip()
                
                # Expression régulière pour attraper les pourcentages (ex: 45% ou [45%])
                match = re.search(r'(\d+)%', decoded_line)
                if match:
                    percentage = match.group(1)
                    yield {"event": "progress", "data": percentage}
                
                # Si l'outil indique qu'il compile le CBZ
                if "Packaging" in decoded_line or "Compressing" in decoded_line:
                    yield {"event": "status", "data": "Création du fichier CBZ..."}

            await process.wait()

            if process.returncode == 0:
                # Téléchargement réussi, on cherche le fichier
                files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.cbz"))
                if not files:
                    files = glob.glob(os.path.join(DOWNLOAD_DIR, "**", "*.cbz"), recursive=True)
                
                if files:
                    filename = os.path.basename(files[0])
                    # On envoie l'événement de fin avec le nom du fichier pour le bouton de téléchargement
                    yield {"event": "done", "data": filename}
                else:
                    yield {"event": "error", "data": "Fichier CBZ introuvable après extraction."}
            else:
                stderr_data = await process.stderr.read()
                error_msg = stderr_data.decode('utf-8', errors='ignore').strip()
                yield {"event": "error", "data": f"Erreur outil : {error_msg}"}

        except Exception as e:
            yield {"event": "error", "data": f"Erreur système : {str(e)}"}

    return EventSourceResponse(event_generator())

@app.get("/get-file")
async def get_file(filename: str):
    """Permet de télécharger le fichier finalisé au clic sur le bouton"""
    # Recherche locale sécurisée du fichier
    files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.cbz"))
    if not files:
        files = glob.glob(os.path.join(DOWNLOAD_DIR, "**", "*.cbz"), recursive=True)
        
    if files and os.path.basename(files[0]) == filename:
        return FileResponse(
            path=files[0], 
            filename=filename, 
            media_type="application/x-cbz"
        )
    raise HTTPException(status_code=404, detail="Le fichier demandé a expiré ou n'existe pas.")
