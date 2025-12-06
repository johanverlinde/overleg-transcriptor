"""Service voor het downloaden van video's en extraheren van audio."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import httpx
import yt_dlp


def _get_ffmpeg_path() -> str:
    """Zoek ffmpeg in PATH of retourneer standaard 'ffmpeg'."""
    ffmpeg = os.getenv("FFMPEG_PATH", "ffmpeg")
    return ffmpeg


def _extract_companywebcast_hls_url(embed_id: str) -> Optional[str]:
    """
    Haal de HLS stream URL op van CompanyWebcast API.
    
    CompanyWebcast gebruikt een meerstaps authenticatie:
    1. Haal player info op
    2. Haal access token op
    3. Haal stream URL op
    """
    base_url = "https://sdk.companywebcast.com"
    
    try:
        with httpx.Client(timeout=30.0) as client:
            # Stap 1: Haal player info
            info_url = f"{base_url}/players/{embed_id}/info"
            info_resp = client.get(info_url)
            
            if info_resp.status_code != 200:
                # Probeer alternatieve ID format
                # gemeenterotterdam_20251118_2 -> zoek via mapping
                return None
            
            player_info = info_resp.json()
            player_id = player_info.get("id")
            
            if not player_id:
                return None
            
            # Stap 2: Haal access token
            token_url = f"{base_url}/accessrules/{player_id}/token"
            token_resp = client.get(token_url)
            
            if token_resp.status_code != 200:
                # Probeer zonder token (sommige streams zijn publiek)
                stream_url = f"{base_url}/players/{player_id}/stream/hls"
                stream_resp = client.get(stream_url)
                if stream_resp.status_code == 200:
                    stream_data = stream_resp.json()
                    return stream_data.get("url")
                return None
            
            token_data = token_resp.json()
            signature = token_data.get("Signature", "")
            policy = token_data.get("Policy", "")
            key_pair_id = token_data.get("Key-Pair-Id", "")
            
            # Stap 3: Haal stream URL met auth
            stream_url = f"{base_url}/players/{player_id}/stream/hls"
            params = {
                "Signature": signature,
                "Policy": policy,
                "Key-Pair-Id": key_pair_id,
            }
            stream_resp = client.get(stream_url, params=params)
            
            if stream_resp.status_code == 200:
                stream_data = stream_resp.json()
                return stream_data.get("url")
            
    except Exception:
        pass
    
    return None


def download_video_audio(video_url: str, output_dir: Path) -> Path:
    """
    Download video van URL en extraheer audio als mp3.
    
    Ondersteunt:
    - YouTube
    - CompanyWebcast (gemeenteraad.rotterdam.nl)
    - Directe video/HLS URLs
    
    Args:
        video_url: URL naar de video of pagina met video
        output_dir: Directory waar audio opgeslagen wordt
        
    Returns:
        Path naar het geëxtraheerde audiobestand
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check of dit een CompanyWebcast URL is
    companywebcast_match = re.search(
        r'sdk\.companywebcast\.com/sdk/player/\?id=([^&\s]+)', 
        video_url
    )
    
    if companywebcast_match:
        embed_id = companywebcast_match.group(1)
        
        # Probeer HLS URL te verkrijgen via API
        hls_url = _extract_companywebcast_hls_url(embed_id)
        
        if hls_url:
            # Download HLS stream direct met ffmpeg
            return download_hls_stream(hls_url, output_dir, f"{embed_id}.mp3")
        
        # Als API niet werkt, probeer yt-dlp met de embed URL
        # (sommige yt-dlp versies ondersteunen CompanyWebcast)
    
    # Standaard yt-dlp download
    output_template = str(output_dir / "%(id)s.%(ext)s")
    
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
        "no_warnings": True,
        "extractaudio": True,
        "ffmpeg_location": _get_ffmpeg_path(),
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            
            # yt-dlp geeft het ID terug, we moeten de output file vinden
            video_id = info.get("id", "audio")
            audio_path = output_dir / f"{video_id}.mp3"
            
            if not audio_path.exists():
                # Zoek naar enig mp3 bestand in de output directory
                mp3_files = list(output_dir.glob("*.mp3"))
                if mp3_files:
                    audio_path = mp3_files[0]
                else:
                    raise FileNotFoundError(
                        f"Audio extractie mislukt. Geen mp3 gevonden in {output_dir}"
                    )
        
        return audio_path
        
    except Exception as ydl_error:
        # Als yt-dlp faalt en dit is een CompanyWebcast URL, geef duidelijkere fout
        if companywebcast_match:
            raise RuntimeError(
                "CompanyWebcast video's (gemeenteraad.rotterdam.nl) kunnen helaas niet automatisch worden gedownload. "
                "Dit videosysteem vereist speciale authenticatie.\n\n"
                "OPLOSSING:\n"
                "1. Ga naar de vergaderpagina in je browser\n"
                "2. Klik op 'Start nu' om de video te bekijken\n"
                "3. Gebruik een browser extensie zoals 'Video DownloadHelper' om de video te downloaden\n"
                "4. Upload het gedownloade bestand via de 'Bestand uploaden' tab\n\n"
                "Alternatief: Gebruik een screen recorder om de audio op te nemen terwijl de video speelt."
            )
        raise


def download_hls_stream(hls_url: str, output_dir: Path, filename: str = "stream.mp3") -> Path:
    """
    Download HLS stream direct met ffmpeg.
    
    Voor gevallen waar yt-dlp niet werkt (bijv. directe HLS URLs van CompanyWebcast).
    
    Args:
        hls_url: URL naar HLS manifest (.m3u8)
        output_dir: Directory waar audio opgeslagen wordt
        filename: Naam voor het output bestand
        
    Returns:
        Path naar het geëxtraheerde audiobestand
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    
    ffmpeg = _get_ffmpeg_path()
    
    cmd = [
        ffmpeg,
        "-i", hls_url,
        "-vn",  # Geen video
        "-acodec", "libmp3lame",
        "-ab", "192k",
        "-y",  # Overschrijf bestaand bestand
        str(output_path),
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg fout: {result.stderr}")
    
    if not output_path.exists():
        raise FileNotFoundError(f"Audio extractie mislukt: {output_path}")
    
    return output_path


def extract_audio_from_video(video_path: Path, output_dir: Optional[Path] = None) -> Path:
    """
    Extraheer audio uit een lokaal videobestand.
    
    Args:
        video_path: Path naar het videobestand
        output_dir: Optionele output directory (standaard: zelfde als video)
        
    Returns:
        Path naar het geëxtraheerde audiobestand
    """
    if not video_path.exists():
        raise FileNotFoundError(f"Videobestand niet gevonden: {video_path}")
    
    if output_dir is None:
        output_dir = video_path.parent
    
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{video_path.stem}.mp3"
    
    ffmpeg = _get_ffmpeg_path()
    
    cmd = [
        ffmpeg,
        "-i", str(video_path),
        "-vn",
        "-acodec", "libmp3lame",
        "-ab", "192k",
        "-y",
        str(output_path),
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg fout: {result.stderr}")
    
    return output_path

