"""Service voor het scrapen van gemeenteraad vergaderpagina's."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


@dataclass
class AgendaItem:
    """Agendapunt van een vergadering."""
    
    nummer: str
    titel: str
    type: str = ""  # bijv. "Ter bespreking", "Ter advisering"
    documenten: List[str] = field(default_factory=list)


@dataclass
class VergaderingMetadata:
    """Metadata van een gemeenteraadsvergadering."""
    
    titel: str
    datum: str
    tijd: str
    locatie: str
    voorzitter: str
    commissie: str
    video_url: Optional[str] = None
    video_embed_id: Optional[str] = None
    agenda_items: List[AgendaItem] = field(default_factory=list)
    source_url: str = ""


def _extract_companywebcast_id(html: str) -> Optional[str]:
    """Haal het CompanyWebcast video ID uit de HTML."""
    
    # iBabs/Rotterdam specifiek: data-video-id attribuut
    # Format: gemeenterotterdam/20251118_2 -> gemeenterotterdam_20251118_2
    pattern_ibabs = r'data-video-id=["\']([^"\']+)["\']'
    match_ibabs = re.search(pattern_ibabs, html)
    if match_ibabs:
        video_id = match_ibabs.group(1)
        # Converteer slash naar underscore
        return video_id.replace("/", "_")
    
    # Zoek naar het SDK player script met ID
    # Voorbeeld: sdk.companywebcast.com/sdk/player/?id=gemeenterotterdam_20251118_2
    pattern = r'sdk\.companywebcast\.com/sdk/player/\?id=([^&"\'>\s]+)'
    match = re.search(pattern, html)
    if match:
        return match.group(1)
    
    # Alternatief: zoek in client.js initialisatie
    # CompanyWebcast.SDK.Player.create({id: "gemeenterotterdam_20251118_2"})
    pattern2 = r'CompanyWebcast\.SDK\.Player\.create\s*\(\s*\{[^}]*id\s*:\s*["\']([^"\']+)["\']'
    match2 = re.search(pattern2, html)
    if match2:
        return match2.group(1)
    
    # Alternatief: zoek naar data attributen
    pattern3 = r'data-webcast-id=["\']([^"\']+)["\']'
    match3 = re.search(pattern3, html)
    if match3:
        return match3.group(1)
    
    # Zoek naar de volledige URL in een script of iframe
    pattern4 = r'["\']https://sdk\.companywebcast\.com/sdk/player/\?id=([^&"\'>\s]+)'
    match4 = re.search(pattern4, html)
    if match4:
        return match4.group(1)
    
    return None


def _extract_video_embed_url(html: str) -> Optional[str]:
    """Haal de video embed URL uit de HTML."""
    # CompanyWebcast iframe URL
    pattern = r'(https://sdk\.companywebcast\.com/sdk/player/[^"\'>\s]+)'
    match = re.search(pattern, html)
    if match:
        return match.group(1)
    return None


async def scrape_vergadering_metadata(url: str) -> VergaderingMetadata:
    """
    Haal metadata op van een gemeenteraad vergaderpagina.
    
    Ondersteunt:
    - gemeenteraad.rotterdam.nl (iBabs)
    - Andere gemeenteraad systemen kunnen later toegevoegd worden
    
    Args:
        url: URL naar de vergaderpagina
        
    Returns:
        VergaderingMetadata object met alle beschikbare informatie
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0, headers=headers) as client:
        response = await client.get(url)
        response.raise_for_status()
        html = response.text
    
    soup = BeautifulSoup(html, "html.parser")
    
    # Basis informatie - zoek titel in h1 of page-title class
    titel = ""
    title_tag = soup.find("h1") or soup.find(class_=re.compile(r"page-title|title", re.I))
    if title_tag:
        titel = title_tag.get_text(strip=True)
    
    # Datum en tijd - zoek naar h2 of specifieke datum elementen
    datum = ""
    tijd = ""
    
    # iBabs heeft vaak een specifieke structuur
    date_heading = soup.find("h2")
    if date_heading:
        date_text = date_heading.get_text(strip=True)
        datum = date_text
    
    # Zoek naar tijd info (bijv. "19:30 - 23:30")
    tijd_pattern = r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})"
    tijd_match = re.search(tijd_pattern, html)
    if tijd_match:
        tijd = f"{tijd_match.group(1)} - {tijd_match.group(2)}"
    
    # Locatie en voorzitter
    locatie = ""
    voorzitter = ""
    
    # Zoek in hele HTML tekst met regex
    locatie_match = re.search(r"Locatie\s*</?\w*>?\s*([^<\n]+)", html, re.IGNORECASE)
    if locatie_match:
        locatie = locatie_match.group(1).strip()
    
    voorzitter_match = re.search(r"Voorzitter\s*</?\w*>?\s*([^<\n]+)", html, re.IGNORECASE)
    if voorzitter_match:
        voorzitter = voorzitter_match.group(1).strip()
    
    # Commissie naam uit breadcrumb of titel
    commissie = ""
    breadcrumb = soup.find("nav", {"aria-label": "Kruimelpad"}) or soup.find("nav", class_="breadcrumb")
    if breadcrumb:
        links = breadcrumb.find_all("a")
        if len(links) >= 2:
            commissie = links[-1].get_text(strip=True)
    
    # Als geen commissie gevonden, probeer uit titel of h1
    if not commissie:
        # Zoek naar "Commissie" in de tekst
        commissie_match = re.search(r"(Commissie[^<\n]+)", html)
        if commissie_match:
            commissie = commissie_match.group(1).strip()
        elif titel:
            commissie = titel
    
    # Video informatie
    video_embed_id = _extract_companywebcast_id(html)
    video_url = _extract_video_embed_url(html)
    
    # Agenda items - probeer verschillende patronen
    agenda_items: List[AgendaItem] = []
    
    # Zoek naar agenda items in list items
    for li in soup.find_all("li"):
        text = li.get_text(strip=True)
        # Zoek naar items die beginnen met een nummer (2.01, 2.02, etc.)
        if re.match(r"^\d+\.?\d*\s", text):
            nummer_match = re.match(r"^(\d+\.?\d*)\s*(.+)", text)
            if nummer_match:
                nummer = nummer_match.group(1)
                rest = nummer_match.group(2)
                # Neem eerste 100 karakters als titel
                titel_item = rest[:100] + "..." if len(rest) > 100 else rest
                agenda_items.append(AgendaItem(
                    nummer=nummer,
                    titel=titel_item,
                ))
    
    # Limiteer tot max 20 agenda items
    agenda_items = agenda_items[:20]
    
    return VergaderingMetadata(
        titel=titel,
        datum=datum,
        tijd=tijd,
        locatie=locatie,
        voorzitter=voorzitter,
        commissie=commissie,
        video_url=video_url,
        video_embed_id=video_embed_id,
        agenda_items=agenda_items,
        source_url=url,
    )


def build_companywebcast_stream_url(embed_id: str) -> str:
    """
    Bouw de directe stream URL voor CompanyWebcast.
    
    Let op: Dit vereist mogelijk authenticatie tokens die tijdelijk zijn.
    Voor productie gebruik is het beter om yt-dlp te gebruiken die dit automatisch afhandelt.
    """
    return f"https://sdk.companywebcast.com/sdk/player/?id={embed_id}"

