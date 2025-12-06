from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Laad .env bestand vóór andere imports
load_dotenv()

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.services.meeting_analysis_service import (
    GemeenteraadAnalyse,
    TeamOverlegAnalyse,
    analyse_gemeenteraad_vergadering,
    analyse_teamoverleg,
    analyse_meeting,
    clean_transcript,
    generate_summary_report,
)
from app.services.report_service import build_gemeenteraad_report, build_teamoverleg_report, build_word_report
from app.services.scraper_service import scrape_vergadering_metadata
from app.services.transcription_service import transcribe_audio
from app.services.video_download_service import download_video_audio

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "temp_uploads"
REPORT_DIR = BASE_DIR / "generated_reports"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

UPLOAD_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Overleg Transcriptor", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

REPORT_REGISTRY: dict[str, Path] = {}


class UrlAnalyzeRequest(BaseModel):
    """Request model voor URL-gebaseerde analyse."""
    url: str


class TranscriptAnalyzeRequest(BaseModel):
    """Request model voor analyse van bestaande transcriptie."""
    transcript: str
    titel: str = "Vergadering"


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


def _validate_upload(file: UploadFile) -> None:
    allowed_types = {
        "audio/mpeg",
        "audio/wav",
        "audio/x-wav",
        "audio/mp3",
        "audio/x-m4a",
        "audio/mp4",
        "audio/x-flac",
        "video/mp4",
        "video/webm",
        "video/quicktime",
    }
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Bestandstype wordt niet ondersteund.")


@app.post("/api/analyze")
async def analyze_uploaded_file(file: UploadFile = File(...)) -> JSONResponse:
    """Analyseer een geüpload audio/video bestand met AI."""
    if not file:
        raise HTTPException(status_code=400, detail="Geen bestand ontvangen.")

    _validate_upload(file)

    saved_path = UPLOAD_DIR / f"{uuid.uuid4()}_{file.filename}"

    try:
        with saved_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    try:
        # Stap 1: Transcribeer audio
        print("Stap 1/3: Transcriberen...")
        transcript = transcribe_audio(saved_path)
        cleaned_transcript = clean_transcript(transcript)
        
        # Stap 2: Analyseer met AI (GPT)
        print("Stap 2/3: Analyseren met AI...")
        metadata_dict = {
            "titel": file.filename or "Geüploade vergadering",
            "source_type": "upload",
        }
        
        analyse = analyse_gemeenteraad_vergadering(
            cleaned_transcript,
            metadata=metadata_dict,
        )
        
        # Stap 3: Genereer rapport
        print("Stap 3/3: Rapport genereren...")
        report_id = str(uuid.uuid4())
        report_path = REPORT_DIR / f"gemeenteraad_{report_id}.docx"
        
        build_gemeenteraad_report(
            report_path,
            analyse,
            metadata=metadata_dict,
            transcript=cleaned_transcript,
        )
        
        REPORT_REGISTRY[report_id] = report_path

        # Bouw response met analyse resultaten
        return JSONResponse(
            {
                "status": "success",
                "reportId": report_id,
                "downloadUrl": f"/api/report/{report_id}",
                "analyse": {
                    "samenvatting": analyse.samenvatting,
                    "belangrijkste_punten": analyse.belangrijkste_punten,
                    "moties_count": len(analyse.moties),
                    "amendementen_count": len(analyse.amendementen),
                    "toezeggingen_count": len(analyse.toezeggingen),
                    "besluiten_count": len(analyse.besluiten),
                },
            }
        )
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - safeguard
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if saved_path.exists():
            saved_path.unlink()


@app.post("/api/analyze-teamoverleg")
async def analyze_teamoverleg_file(file: UploadFile = File(...)) -> JSONResponse:
    """
    Analyseer een teamoverleg (bijv. Rotterdams WeerWoord) met focus op:
    - Samenvatting van de discussie
    - Actielijst met verantwoordelijken
    """
    if not file:
        raise HTTPException(status_code=400, detail="Geen bestand ontvangen.")

    _validate_upload(file)

    saved_path = UPLOAD_DIR / f"{uuid.uuid4()}_{file.filename}"

    try:
        with saved_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    try:
        # Stap 1: Transcribeer audio
        print("Stap 1/3: Transcriberen...")
        transcript = transcribe_audio(saved_path)
        cleaned_transcript = clean_transcript(transcript)
        
        # Stap 2: Analyseer met AI (teamoverleg specifiek)
        print("Stap 2/3: Analyseren met AI (teamoverleg)...")
        metadata_dict = {
            "titel": file.filename or "Teamoverleg Rotterdams WeerWoord",
            "source_type": "upload",
        }
        
        analyse = analyse_teamoverleg(
            cleaned_transcript,
            metadata=metadata_dict,
        )
        
        # Stap 3: Genereer rapport
        print("Stap 3/3: Rapport genereren...")
        report_id = str(uuid.uuid4())
        report_path = REPORT_DIR / f"teamoverleg_{report_id}.docx"
        
        build_teamoverleg_report(
            report_path,
            analyse,
            metadata=metadata_dict,
            transcript=cleaned_transcript,
        )
        
        REPORT_REGISTRY[report_id] = report_path

        # Bouw response met analyse resultaten
        return JSONResponse(
            {
                "status": "success",
                "reportId": report_id,
                "downloadUrl": f"/api/report/{report_id}",
                "analyse": {
                    "samenvatting": analyse.samenvatting,
                    "aanwezigen": analyse.aanwezigen,
                    "acties": [
                        {
                            "actie": a.actie,
                            "verantwoordelijke": a.verantwoordelijke,
                            "deadline": a.deadline,
                            "prioriteit": a.prioriteit,
                        }
                        for a in analyse.acties
                    ],
                    "besproken_punten_count": len(analyse.besproken_punten),
                    "besluiten_count": len(analyse.besluiten),
                    "aandachtspunten": analyse.aandachtspunten,
                },
            }
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if saved_path.exists():
            saved_path.unlink()


@app.post("/api/analyze-url")
async def analyze_meeting_url(request: UrlAnalyzeRequest) -> JSONResponse:
    """
    Analyseer een gemeenteraadsvergadering vanaf een URL.
    
    Ondersteunt:
    - gemeenteraad.rotterdam.nl
    - Andere iBabs-gebaseerde gemeenteraad sites
    - Directe video URLs (YouTube, etc.)
    """
    url = request.url.strip()
    
    if not url:
        raise HTTPException(status_code=400, detail="Geen URL opgegeven.")
    
    session_id = str(uuid.uuid4())
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    
    metadata_dict: dict = {}
    
    try:
        # Stap 1: Haal metadata op van de pagina
        try:
            metadata = await scrape_vergadering_metadata(url)
            metadata_dict = {
                "titel": metadata.titel,
                "datum": metadata.datum,
                "tijd": metadata.tijd,
                "locatie": metadata.locatie,
                "voorzitter": metadata.voorzitter,
                "commissie": metadata.commissie,
                "source_url": url,
            }
            
            # Bepaal de video URL
            video_url = None
            
            # Probeer CompanyWebcast embed URL
            if metadata.video_embed_id:
                video_url = f"https://sdk.companywebcast.com/sdk/player/?id={metadata.video_embed_id}"
            elif metadata.video_url:
                video_url = metadata.video_url
                
        except Exception as scrape_error:
            # Als scraping faalt, probeer de URL direct
            metadata_dict = {"source_url": url}
            video_url = None
        
        # Stap 2: Download video en extraheer audio
        download_errors = []
        audio_path = None
        
        # Probeer verschillende video URL opties
        urls_to_try = []
        if video_url:
            urls_to_try.append(("CompanyWebcast embed", video_url))
        urls_to_try.append(("Originele pagina", url))
        
        for source_name, try_url in urls_to_try:
            try:
                audio_path = download_video_audio(try_url, session_dir)
                break  # Succesvol gedownload
            except Exception as e:
                download_errors.append(f"{source_name}: {str(e)}")
                continue
        
        if audio_path is None:
            error_details = "\n".join(download_errors)
            raise HTTPException(
                status_code=400,
                detail=f"Kon video niet downloaden. Probeer het audiobestand handmatig te downloaden en te uploaden.\n\nDetails:\n{error_details}"
            )
        
        # Stap 3: Transcribeer audio
        transcript = transcribe_audio(audio_path)
        cleaned_transcript = clean_transcript(transcript)
        
        # Stap 4: Analyseer met AI
        analyse = analyse_gemeenteraad_vergadering(
            cleaned_transcript,
            metadata=metadata_dict,
        )
        
        # Stap 5: Genereer rapport
        report_id = str(uuid.uuid4())
        report_path = REPORT_DIR / f"gemeenteraad_{report_id}.docx"
        
        build_gemeenteraad_report(
            report_path,
            analyse,
            metadata=metadata_dict,
            transcript=cleaned_transcript,
        )
        
        REPORT_REGISTRY[report_id] = report_path
        
        # Bouw response
        response_data = {
            "status": "success",
            "reportId": report_id,
            "downloadUrl": f"/api/report/{report_id}",
            "metadata": metadata_dict,
            "analyse": {
                "samenvatting": analyse.samenvatting,
                "belangrijkste_punten": analyse.belangrijkste_punten,
                "moties": [
                    {
                        "titel": m.titel,
                        "indiener": m.indiener,
                        "partij": m.partij,
                        "stemuitslag": m.stemuitslag,
                    }
                    for m in analyse.moties
                ],
                "toezeggingen": [
                    {
                        "door": t.door,
                        "onderwerp": t.onderwerp,
                        "deadline": t.deadline,
                    }
                    for t in analyse.toezeggingen
                ],
                "amendementen_count": len(analyse.amendementen),
                "besluiten_count": len(analyse.besluiten),
                "sprekers_count": len(analyse.sprekers),
            },
        }
        
        return JSONResponse(response_data)
        
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        # Cleanup session directory
        if session_dir.exists():
            shutil.rmtree(session_dir, ignore_errors=True)


@app.get("/api/report/{report_id}")
def download_report(report_id: str) -> FileResponse:
    report_path = REPORT_REGISTRY.get(report_id)
    if not report_path or not report_path.exists():
        raise HTTPException(status_code=404, detail="Verslag niet gevonden.")

    return FileResponse(
        path=report_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=report_path.name,
    )


@app.post("/api/analyze-transcript")
async def analyze_transcript_only(request: TranscriptAnalyzeRequest) -> JSONResponse:
    """
    Analyseer een bestaande transcriptie (zonder opnieuw te transcriberen).
    
    Handig als je al een transcriptie hebt en alleen de AI-analyse wilt.
    """
    if not request.transcript or len(request.transcript.strip()) < 100:
        raise HTTPException(
            status_code=400, 
            detail="Transcriptie is te kort. Minimaal 100 karakters vereist."
        )
    
    try:
        # Clean de transcriptie
        cleaned_transcript = clean_transcript(request.transcript)
        
        metadata_dict = {
            "titel": request.titel,
            "source_type": "transcript_upload",
        }
        
        # Analyseer met AI
        print("Analyseren met AI (alleen analyse, geen transcriptie)...")
        analyse = analyse_gemeenteraad_vergadering(
            cleaned_transcript,
            metadata=metadata_dict,
        )
        
        # Genereer rapport
        report_id = str(uuid.uuid4())
        report_path = REPORT_DIR / f"gemeenteraad_{report_id}.docx"
        
        build_gemeenteraad_report(
            report_path,
            analyse,
            metadata=metadata_dict,
            transcript=cleaned_transcript,
        )
        
        REPORT_REGISTRY[report_id] = report_path

        return JSONResponse(
            {
                "status": "success",
                "reportId": report_id,
                "downloadUrl": f"/api/report/{report_id}",
                "analyse": {
                    "samenvatting": analyse.samenvatting,
                    "belangrijkste_punten": analyse.belangrijkste_punten,
                    "moties_count": len(analyse.moties),
                    "amendementen_count": len(analyse.amendementen),
                    "toezeggingen_count": len(analyse.toezeggingen),
                    "besluiten_count": len(analyse.besluiten),
                },
            }
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/scrape-metadata")
async def scrape_metadata(url: str) -> JSONResponse:
    """
    Haal alleen metadata op van een vergaderpagina zonder te analyseren.
    Handig voor preview voordat de volledige analyse gestart wordt.
    """
    if not url:
        raise HTTPException(status_code=400, detail="Geen URL opgegeven.")
    
    try:
        metadata = await scrape_vergadering_metadata(url)
        
        return JSONResponse({
            "status": "success",
            "metadata": {
                "titel": metadata.titel,
                "datum": metadata.datum,
                "tijd": metadata.tijd,
                "locatie": metadata.locatie,
                "voorzitter": metadata.voorzitter,
                "commissie": metadata.commissie,
                "video_beschikbaar": bool(metadata.video_embed_id or metadata.video_url),
                "agenda_items": [
                    {"nummer": item.nummer, "titel": item.titel}
                    for item in metadata.agenda_items
                ],
            },
        })
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Kon metadata niet ophalen: {str(exc)}")
