"""Service voor transcripties van audio naar tekst via Gemini of Whisper."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

# Configuratie
TRANSCRIPTION_PROVIDER = os.getenv("TRANSCRIPTION_PROVIDER", "gemini")  # "gemini" of "whisper"
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

_whisper_model = None

# =============================================================================
# CONTEXT PROMPT - Helpt met specifieke termen en namen
# =============================================================================

CONTEXT_PROMPT = """
Dit is een transcriptie van een Nederlandse gemeenteraadsvergadering in Rotterdam.

COLLEGE VAN BURGEMEESTER EN WETHOUDERS ROTTERDAM (actueel):
- Burgemeester Carola Schouten
- Wethouder Faouzi Achbar - Welzijn, Samenleven, Sport en Digitale Inclusie
- Wethouder Ronald Buijt - Zorg, Ouderen en Jeugdzorg
- Wethouder Said Kasmi - Onderwijs, Cultuur en Evenementen
- Wethouder Pascal Lansink-Bastemeijer - Handhaving, Buitenruimte en Mobiliteit
- Wethouder Abigail Norville - Armoedebestrijding, Schuldhulpverlening, Taal en Toeslagen
- Wethouder Bart-Joost van Rij - Financiën, Organisatie, Dienstverlening en Grote Projecten
- Locoburgemeester Robert Simons - Haven, Economie, Horeca en Bestuur
- Wethouder Tim Versnel - Werk en Inkomen, NPRZ, EU-arbeidsmigranten, Dierenwelzijn
- Wethouder Chantal Zeegers - Klimaat, Bouwen en Wonen

GRIFFIE ROTTERDAM:
- Griffier Pascal Hendrikse

BURGERCOMMISSIELEDEN ROTTERDAM:
- VVD: Eveline Padberg-de Haan
- GroenLinks: Sigrid Oosterwegel
- D66: Pelle Meurink
- PvdA: Ryan Vos
- DENK: Safa Sodirijo
- Volt: Donatella Schalm-Civile, Femke Bouwer-van Schie
- BIJ1: Precious Sadhoe
- 50PLUS: Nico van Scheijndel, Jet Valk
- ChristenUnie: Gerben van Dijk
- SP: Emin Başoğlu, Tom Breedveld, Just Hovens Greve
- CDA: Sam Mak, Bernhard van Meeteren, Ellen Verouden

GEMEENTERAADSLEDEN ROTTERDAM (actueel):

Leefbaar Rotterdam:
- Simon Ceulemans (fractievoorzitter), Caroline Aafjes-van Aalst, Sebastiaan Bonte
- Vanessa Bruin, Manuel Crielaard, Geert Koster, Thomas Roskam
- Benvenido van Schaik, Marcel Verhoef, Joey de Waard

VVD:
- Dieke van Groningen (fractievoorzitter), Marike Abrahamse, Simon Becker
- Diederik van Dommelen, Erik Verweij, Jordi Vicario

GroenLinks:
- Astrid Kockelkoren (fractievoorzitter), Marvin Biljoen, Mina Morkoç
- Larissa Vlieger, Stephan Leewis

D66:
- Agnes Maassen (fractievoorzitter), Tim de Haan, Joan Nunnely
- Ingrid van Wifferen, Eyasu Balcha

PvdA:
- Sarah Reitema (fractievoorzitter), Duygu Yildirim
- Steven Lammering Varela, Amy de Bruijn

DENK:
- Serkan Soytekin (fractievoorzitter), Elika Rehim Zadeh
- Naoufal Akhatab, Rashied Dahoe

Volt:
- Luuc Dekkers (fractievoorzitter), Tim Kind

Partij voor de Dieren:
- Ruud van der Velden (fractievoorzitter), Sabrina van de Peppel

BIJ1:
- Marchiano van Campenhout (fractievoorzitter)

50PLUS:
- Ellen Verkoelen (fractievoorzitter)

ChristenUnie:
- Tjalling Vonk (fractievoorzitter)

SP:
- Theo Coşkun (fractievoorzitter)

CDA:
- René Segers-Hoogendoorn (fractievoorzitter)

Forum voor Democratie:
- Ardi Oostdijk (fractievoorzitter)

Groep De Jong:
- Michantely de Jong (fractievoorzitter)

Veelvoorkomende functies en rollen:
- Wethouder, raadslid, griffier, voorzitter, burgemeester
- Commissielid, fractievoorzitter, inspreekster, inspreker
- Ambtenaar, beleidsadviseur, projectleider, directeur

Politieke partijen Rotterdam:
- VVD, D66, GroenLinks, PvdA, CDA, SP, ChristenUnie-SGP
- Partij voor de Dieren, DENK, PVV, NIDA, Volt, 50PLUS
- Leefbaar Rotterdam

Vaktermen watermanagement en klimaatadaptatie:
- Wateroverlast, hittestress, klimaatadaptatie, waterberging
- Riolering, hemelwaterafvoer, infiltratie, wadi
- Groenblauw, vergroening, ontharding, waterbeheer
- Droogte, waterschap, hoogwaterbescherming, dijkversterking
- Regenwateropvang, retentie, afkoppelen, gescheiden rioolstelsel
- Klimaatbestendige stad, sponswerking, stedelijk water

Vaktermen stedenbouw en ruimtelijke ordening:
- Bestemmingsplan, omgevingsvisie, omgevingsplan, welstandsnota
- Erfpacht, grondzaken, ruimtelijke ordening, gebiedsontwikkeling
- Woningbouw, sociale huur, middenhuur, koopwoning
- Verdichting, binnenstedelijk, transformatie, herontwikkeling
- Mobiliteit, parkeerbeleid, fietspad, openbaar vervoer
- Hoogbouw, woningnood, wooncrisis, huisvestingsvergunning

Vaktermen gemeentelijk beleid:
- Collegebrief, raadsvoorstel, amendement, motie, toezegging
- Hamerstuk, bespreekstuk, termijnagenda, portefeuillehouder
- Zienswijze, bezwaar, beroep, vergunning, subsidie
- Begrotingswijziging, jaarrekening, kadernota
- Raadsinformatiebrief, schriftelijke vragen, mondelinge vragen

Rotterdamse locaties en organisaties:
- Coolsingel, Erasmusbrug, Maas, Rijnmond, Nieuwe Maas
- Kralingen, Feijenoord, Charlois, Delfshaven, Hoogvliet
- Prins Alexander, Overschie, Pernis, Rozenburg, Hoek van Holland
- IJsselmonde, Lombardijen, Zuid, Noord, Centrum, West
- Stadsbeheer, DCMR, Havenbedrijf Rotterdam, RET
- Woonstad Rotterdam, Havensteder, Vestia
- Erasmus MC, Ikazia, Maasstad Ziekenhuis
"""


def _get_whisper_model():
    """Laad het Whisper model (cached na eerste keer laden)."""
    global _whisper_model
    if _whisper_model is None:
        import whisper
        print(f"Whisper model '{WHISPER_MODEL}' laden (eerste keer kan even duren)...")
        _whisper_model = whisper.load_model(WHISPER_MODEL)
        print(f"Whisper model geladen!")
    return _whisper_model


def _transcribe_with_whisper(audio_path: Path) -> str:
    """Transcribeer audio met lokale Whisper."""
    model = _get_whisper_model()
    
    file_size_mb = audio_path.stat().st_size / (1024 * 1024)
    print(f"[Whisper] Start transcriptie van {audio_path.name} ({file_size_mb:.1f}MB)...")
    print(f"Dit kan even duren afhankelijk van de lengte van het bestand...")
    
    result = model.transcribe(
        str(audio_path),
        language="nl",
        task="transcribe",
        verbose=False,
        initial_prompt=CONTEXT_PROMPT,
    )
    
    transcript = result.get("text", "")
    print(f"[Whisper] Transcriptie voltooid! ({len(transcript)} karakters)")
    return transcript.strip()


def _split_audio_into_chunks(audio_path: Path, chunk_duration_ms: int = 600000) -> list[Path]:
    """
    Split audio in chunks van opgegeven duur (standaard 10 minuten).
    
    Returns:
        Lijst van paden naar chunk bestanden
    """
    from pydub import AudioSegment
    import tempfile
    
    print(f"[Gemini] Audio laden voor chunking...")
    
    # Bepaal formaat op basis van extensie
    ext = audio_path.suffix.lower()
    if ext in ['.mp3']:
        audio = AudioSegment.from_mp3(str(audio_path))
    elif ext in ['.wav']:
        audio = AudioSegment.from_wav(str(audio_path))
    elif ext in ['.m4a', '.mp4', '.aac']:
        audio = AudioSegment.from_file(str(audio_path), format="mp4")
    elif ext in ['.ogg']:
        audio = AudioSegment.from_ogg(str(audio_path))
    elif ext in ['.flac']:
        audio = AudioSegment.from_file(str(audio_path), format="flac")
    else:
        audio = AudioSegment.from_file(str(audio_path))
    
    duration_ms = len(audio)
    duration_min = duration_ms / 60000
    
    print(f"[Gemini] Audio duur: {duration_min:.1f} minuten")
    
    # Als audio kort genoeg is, geen chunking nodig
    if duration_ms <= chunk_duration_ms:
        return [audio_path]
    
    # Split in chunks
    chunks = []
    chunk_dir = audio_path.parent / "chunks"
    chunk_dir.mkdir(exist_ok=True)
    
    num_chunks = (duration_ms // chunk_duration_ms) + (1 if duration_ms % chunk_duration_ms else 0)
    print(f"[Gemini] Audio splitsen in {num_chunks} delen van ~{chunk_duration_ms // 60000} minuten...")
    
    for i in range(0, duration_ms, chunk_duration_ms):
        chunk_num = i // chunk_duration_ms + 1
        chunk = audio[i:i + chunk_duration_ms]
        chunk_path = chunk_dir / f"chunk_{chunk_num:03d}.mp3"
        chunk.export(str(chunk_path), format="mp3")
        chunks.append(chunk_path)
        print(f"[Gemini] Chunk {chunk_num}/{num_chunks} opgeslagen")
    
    return chunks


def _transcribe_single_chunk(audio_path: Path, chunk_num: int = 0, total_chunks: int = 1) -> str:
    """Transcribeer een enkel audio bestand met Gemini."""
    import google.generativeai as genai
    import time
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    prefix = f"[Gemini {chunk_num}/{total_chunks}]" if total_chunks > 1 else "[Gemini]"
    
    # Upload audio bestand naar Gemini
    print(f"{prefix} Audio uploaden naar Gemini...")
    audio_file = genai.upload_file(str(audio_path))
    
    # Wacht tot bestand verwerkt is
    while audio_file.state.name == "PROCESSING":
        print(f"{prefix} Bestand wordt verwerkt...")
        time.sleep(5)
        audio_file = genai.get_file(audio_file.name)
    
    if audio_file.state.name == "FAILED":
        raise RuntimeError(f"Audio upload mislukt: {audio_file.state.name}")
    
    print(f"{prefix} Starten met transcriptie...")
    
    # Transcribeer met Gemini
    model = genai.GenerativeModel("gemini-2.0-flash")
    
    transcription_prompt = f"""
Transcribeer de volgende audio-opname van een Nederlandse gemeenteraadsvergadering.

BELANGRIJKE INSTRUCTIES:
1. Transcribeer ALLE gesproken tekst letterlijk en volledig
2. Gebruik de correcte spelling van namen en termen (zie context hieronder)
3. Geef alleen de transcriptie terug, geen samenvattingen of analyses
4. Behoud de volgorde van sprekers
5. Als een naam of term onduidelijk is, gebruik de meest waarschijnlijke spelling uit de context

CONTEXT MET NAMEN EN TERMEN:
{CONTEXT_PROMPT}

Transcribeer nu de audio:
"""
    
    response = model.generate_content(
        [transcription_prompt, audio_file],
        generation_config=genai.GenerationConfig(
            temperature=0.1,  # Lage temperatuur voor nauwkeurige transcriptie
            max_output_tokens=100000,
        ),
    )
    
    transcript = response.text.strip()
    
    # Cleanup: verwijder uploaded file
    try:
        genai.delete_file(audio_file.name)
    except Exception:
        pass  # Niet kritiek als cleanup faalt
    
    print(f"{prefix} Transcriptie voltooid! ({len(transcript)} karakters)")
    return transcript


def _transcribe_with_gemini(audio_path: Path) -> str:
    """Transcribeer audio met Google Gemini, met automatische chunking voor lange bestanden."""
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY ontbreekt. "
            "Haal een gratis API key op: https://aistudio.google.com/app/apikey"
        )
    
    import shutil
    
    file_size_mb = audio_path.stat().st_size / (1024 * 1024)
    print(f"[Gemini] Start transcriptie van {audio_path.name} ({file_size_mb:.1f}MB)...")
    
    # Split audio in chunks van 10 minuten voor betere resultaten
    # Gemini kan wel langere audio aan maar geeft dan incomplete transcripties
    chunk_duration_ms = 10 * 60 * 1000  # 10 minuten
    
    chunks = _split_audio_into_chunks(audio_path, chunk_duration_ms)
    
    if len(chunks) == 1 and chunks[0] == audio_path:
        # Geen chunking nodig, transcribeer direct
        return _transcribe_single_chunk(audio_path)
    
    # Transcribeer alle chunks
    transcripts = []
    total_chunks = len(chunks)
    
    print(f"[Gemini] Transcriberen van {total_chunks} audio delen...")
    
    for i, chunk_path in enumerate(chunks, 1):
        try:
            transcript = _transcribe_single_chunk(chunk_path, i, total_chunks)
            transcripts.append(transcript)
        except Exception as e:
            print(f"[Gemini] Waarschuwing: Chunk {i} mislukt: {e}")
            transcripts.append(f"[Deel {i} kon niet worden getranscribeerd]")
    
    # Cleanup chunk bestanden
    chunk_dir = audio_path.parent / "chunks"
    if chunk_dir.exists():
        try:
            shutil.rmtree(chunk_dir)
        except Exception:
            pass
    
    # Voeg alle transcripties samen
    full_transcript = "\n\n".join(transcripts)
    print(f"[Gemini] Volledige transcriptie: {len(full_transcript)} karakters uit {total_chunks} delen")
    
    return full_transcript


def transcribe_audio(audio_path: Path, custom_prompt: str = "") -> str:
    """
    Transcribeer audio via Gemini (cloud) of Whisper (lokaal).
    
    De provider wordt bepaald door TRANSCRIPTION_PROVIDER in .env:
    - "gemini": Google Gemini (cloud, gratis tier)
    - "whisper": Lokale Whisper (offline, geen limieten)
    
    Args:
        audio_path: Pad naar het audiobestand
        custom_prompt: Optionele extra context (alleen voor Whisper)
        
    Returns:
        De getranscribeerde tekst
    """
    if not audio_path.exists():
        raise FileNotFoundError("Audiobestand ontbreekt voor transcriptie.")
    
    provider = TRANSCRIPTION_PROVIDER.lower()
    
    try:
        if provider == "gemini":
            return _transcribe_with_gemini(audio_path)
        elif provider == "whisper":
            return _transcribe_with_whisper(audio_path)
        else:
            raise RuntimeError(f"Onbekende transcriptie provider: {provider}")
            
    except Exception as e:
        error_msg = str(e)
        
        # Specifieke foutmeldingen
        if "CUDA" in error_msg or "GPU" in error_msg:
            raise RuntimeError(
                f"GPU fout: {error_msg}. "
                f"Probeer WHISPER_MODEL=tiny of WHISPER_MODEL=base."
            )
        if "quota" in error_msg.lower() or "429" in error_msg:
            raise RuntimeError(
                "Gemini quota bereikt. Wacht even of schakel over naar Whisper "
                "(TRANSCRIPTION_PROVIDER=whisper in .env)"
            )
        
        raise RuntimeError(f"Transcriptie mislukt: {error_msg}")
