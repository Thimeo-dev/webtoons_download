import os
import glob
import subprocess
import shutil
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Webtoon Downloader Cloud")

# Dossier temporaire sur Render pour stocker le fichier avant l'envoi
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
    
    # Nettoyage du dossier temporaire avant de commencer pour éviter de mélanger les téléchargements
    if os.path.exists(DOWNLOAD_DIR):
        shutil.rmtree(DOWNLOAD_DIR)
    os.makedirs(DOWNLOAD_DIR)

    try:
        # On appelle directement 'webtoon-downloader' (sans 'uv' qui n'existe pas sur Render)
        process = subprocess.run([
            "webtoon-downloader", 
            url, 
            "--save-as", "cbz", 
            "--output", DOWNLOAD_DIR
        ], capture_output=True, text=True, check=True)
        
        # On cherche le fichier .cbz qui a été créé dans le dossier temporaire
        files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.cbz"))
        
        if not files:
            # Si aucun .cbz n'est trouvé, on vérifie s'il y a un sous-dossier créé par l'outil
            files = glob.glob(os.path.join(DOWNLOAD_DIR, "**", "*.cbz"), recursive=True)
            
        if files:
            target_file = files[0] # On prend le premier fichier trouvé
            filename = os.path.basename(target_file)
            
            # On renvoie le fichier directement au navigateur de l'utilisateur
            return FileResponse(
                path=target_file, 
                filename=filename, 
                media_type="application/x-cbz"
            )
        else:
            raise HTTPException(status_code=500, detail="L'extraction a réussi mais le fichier .cbz n'a pas été trouvé.")
            
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else e.stdout
        raise HTTPException(status_code=500, detail=f"Erreur d'extraction : {error_msg}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur système : {str(e)}")
