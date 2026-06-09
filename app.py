import os
import subprocess
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Webtoon Downloader GUI")

# Dossier de destination par défaut (au même endroit que le script)
DOWNLOAD_DIR = os.path.join(os.getcwd(), "Telechargements_Webtoons")
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)


class DownloadRequest(BaseModel):
    url: str


@app.get("/")
async def read_index():
    # Renvoie l'interface graphique
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    raise HTTPException(status_code=404, detail="Fichier index.html introuvable")


@app.post("/download")
async def start_download(request: DownloadRequest):
    url = request.url.strip()

    if not url:
        raise HTTPException(
            status_code=400, detail="L'URL fournie est vide."
        )

    try:
        # Exécute la commande via l'outil 'uv' que tu as configuré
        # On force la sauvegarde en .cbz et on définit le dossier de sortie
        process = subprocess.run(
            [
                "uv",
                "run",
                "webtoon-downloader",
                url,
                "--save-as",
                "cbz",
                "--output",
                DOWNLOAD_DIR,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        return {
            "status": "success",
            "message": f"Téléchargement terminé avec succès ! Les fichiers CBZ sont dans : {DOWNLOAD_DIR}",
        }

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else e.stdout
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du téléchargement : {error_msg}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur système : {str(e)}")


if __name__ == "__main__":
    # Lance le serveur local sur le port 8000
    print(f"Les fichiers seront sauvegardés dans : {DOWNLOAD_DIR}")
    uvicorn.run(app, host="127.0.0.1", port=8000)
