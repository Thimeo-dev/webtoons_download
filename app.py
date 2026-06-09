import os
import glob
import subprocess
import shutil
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Webtoon Downloader Render Fixed")

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

@app.post("/download")
async def start_download(request: DownloadRequest):
    url = request.url.strip()
    
    if not url:
        raise HTTPException(status_code=400, detail="L'URL fournie est vide.")
    
    # Nettoyage des anciens fichiers
    if os.path.exists(DOWNLOAD_DIR):
        shutil.rmtree(DOWNLOAD_DIR)
    os.makedirs(DOWNLOAD_DIR)

    try:
        # Exécution directe et robuste
        process = subprocess.run([
            "webtoon-downloader", 
            url, 
            "--save-as", "cbz", 
            "--out", DOWNLOAD_DIR
        ], capture_output=True, text=True, check=True)
        
        # On cherche le fichier CBZ généré
        files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.cbz"))
        if not files:
            files = glob.glob(os.path.join(DOWNLOAD_DIR, "**", "*.cbz"), recursive=True)
            
        if files:
            filename = os.path.basename(files[0])
            return {"status": "success", "filename": filename}
        else:
            raise HTTPException(status_code=500, detail="L'extraction a réussi mais le fichier .cbz est introuvable.")
            
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else e.stdout
        raise HTTPException(status_code=500, detail=f"Erreur d'extraction : {error_msg}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur système : {str(e)}")

@app.get("/get-file")
async def get_file(filename: str):
    files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.cbz"))
    if not files:
        files = glob.glob(os.path.join(DOWNLOAD_DIR, "**", "*.cbz"), recursive=True)
        
    if files and os.path.basename(files[0]) == filename:
        return FileResponse(
            path=files[0], 
            filename=filename, 
            media_type="application/x-cbz"
        )
    raise HTTPException(status_code=404, detail="Fichier introuvable ou expiré.")
