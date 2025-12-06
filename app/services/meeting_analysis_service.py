"""Analyse- en verslaglogica voor vergaderingen met AI-ondersteuning."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Configuratie - standaard Gemini (gratis tier)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")  # "gemini", "ollama", of "openai"

# Gemini configuratie (GRATIS - 60 requests/min)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Ollama configuratie (lokaal, gratis)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# OpenAI configuratie (betaald)
OPENAI_API_KEY = os.getenv("CHATGPT_API_KEY")
OPENAI_MODEL = os.getenv("CHATGPT_MODEL", "gpt-4o")

PARAGRAPH_SENTENCE_COUNT = 3


def clean_transcript(transcript: str) -> str:
    """Maak de transcriptie leesbaar door witruimte en herhalingen op te schonen."""

    text = re.sub(r"\s+", " ", transcript).strip()
    if not text:
        return "Transcriptie bevat geen inhoud."

    sentences = re.split(r"(?<=[.!?]) ", text)
    paragraphs: List[str] = []
    current: List[str] = []

    for sentence in sentences:
        normalized = sentence.strip()
        if not normalized:
            continue
        if len(normalized) > 1:
            normalized = normalized[0].upper() + normalized[1:]
        else:
            normalized = normalized.upper()
        current.append(normalized)
        if len(current) == PARAGRAPH_SENTENCE_COUNT:
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))

    return "\n\n".join(paragraphs)


@dataclass
class Motie:
    """Een motie uit de vergadering."""
    nummer: str = ""
    titel: str = ""
    indiener: str = ""
    partij: str = ""
    samenvatting: str = ""
    stemuitslag: str = ""


@dataclass
class Toezegging:
    """Een toezegging door wethouder of ambtenaar."""
    door: str = ""
    aan: str = ""
    onderwerp: str = ""
    deadline: str = ""
    context: str = ""


@dataclass
class Amendement:
    """Een amendement op een voorstel."""
    nummer: str = ""
    titel: str = ""
    indiener: str = ""
    partij: str = ""
    wijziging: str = ""
    stemuitslag: str = ""


@dataclass
class Spreker:
    """Een spreker in de vergadering."""
    naam: str = ""
    functie: str = ""
    partij: str = ""
    spreektijd_minuten: float = 0.0


@dataclass
class GemeenteraadAnalyse:
    """Volledige analyse van een gemeenteraadsvergadering."""
    samenvatting: str = ""
    belangrijkste_punten: List[str] = field(default_factory=list)
    moties: List[Motie] = field(default_factory=list)
    amendementen: List[Amendement] = field(default_factory=list)
    toezeggingen: List[Toezegging] = field(default_factory=list)
    besluiten: List[Dict[str, str]] = field(default_factory=list)
    sprekers: List[Spreker] = field(default_factory=list)
    besproken_onderwerpen: List[Dict[str, str]] = field(default_factory=list)
    opmerkingen: str = ""


@dataclass
class ActieItem:
    """Een actie-item uit het teamoverleg."""
    actie: str = ""
    verantwoordelijke: str = ""
    deadline: str = ""
    prioriteit: str = ""  # hoog, middel, laag
    status: str = "open"  # open, in_progress, done


@dataclass
class BesprekingsPunt:
    """Een besproken onderwerp in het teamoverleg."""
    onderwerp: str = ""
    samenvatting: str = ""
    besluit: str = ""
    opmerkingen: str = ""


@dataclass
class TeamOverlegAnalyse:
    """Analyse van een intern teamoverleg (bijv. Rotterdams WeerWoord)."""
    titel: str = ""
    datum: str = ""
    samenvatting: str = ""
    aanwezigen: List[str] = field(default_factory=list)
    besproken_punten: List[BesprekingsPunt] = field(default_factory=list)
    acties: List[ActieItem] = field(default_factory=list)
    besluiten: List[str] = field(default_factory=list)
    aandachtspunten: List[str] = field(default_factory=list)
    volgende_overleg: str = ""
    opmerkingen: str = ""


SYSTEM_PROMPT_GEMEENTERAAD = """Je bent een expert in het analyseren van Nederlandse gemeenteraadsvergaderingen. 
Je krijgt een transcriptie van een vergadering en moet een gestructureerde analyse maken.

Identificeer en extraheer de volgende elementen:

1. SAMENVATTING: Een beknopte samenvatting van de vergadering (max 200 woorden)

2. BELANGRIJKSTE PUNTEN: De 5-10 belangrijkste besproken punten

3. MOTIES: Voor elke motie:
   - Nummer/naam
   - Titel/onderwerp
   - Indiener(s) en partij
   - Korte samenvatting van de inhoud
   - Stemuitslag (aangenomen/verworpen/ingetrokken/aangehouden)

4. AMENDEMENTEN: Voor elk amendement:
   - Nummer
   - Titel
   - Indiener(s) en partij
   - Wat wordt gewijzigd
   - Stemuitslag

5. TOEZEGGINGEN: Voor elke toezegging door wethouder/college:
   - Wie doet de toezegging
   - Aan wie (welke partij/raadslid)
   - Wat wordt toegezegd
   - Wanneer (deadline indien genoemd)
   - Context

6. BESLUITEN: Formele besluiten die genomen zijn

7. SPREKERS: Belangrijkste sprekers met hun rol (raadslid, wethouder, inspreker)

8. BESPROKEN ONDERWERPEN: Agendapunten met korte beschrijving van de discussie

Geef je antwoord ALLEEN als valid JSON in het volgende formaat (geen andere tekst):
{
    "samenvatting": "...",
    "belangrijkste_punten": ["punt 1", "punt 2"],
    "moties": [
        {
            "nummer": "...",
            "titel": "...",
            "indiener": "...",
            "partij": "...",
            "samenvatting": "...",
            "stemuitslag": "..."
        }
    ],
    "amendementen": [],
    "toezeggingen": [
        {
            "door": "...",
            "aan": "...",
            "onderwerp": "...",
            "deadline": "...",
            "context": "..."
        }
    ],
    "besluiten": [
        {
            "titel": "...",
            "besluit": "...",
            "context": "..."
        }
    ],
    "sprekers": [
        {
            "naam": "...",
            "functie": "...",
            "partij": "..."
        }
    ],
    "besproken_onderwerpen": [
        {
            "titel": "...",
            "samenvatting": "..."
        }
    ],
    "opmerkingen": "..."
}

Wees nauwkeurig en baseer je analyse alleen op wat daadwerkelijk in de transcriptie staat.
Als iets niet duidelijk is of niet voorkomt, laat het veld leeg of gebruik een lege array.
"""


SYSTEM_PROMPT_TEAMOVERLEG = """Je bent een expert in het analyseren en samenvatten van interne teamoverleggen.
Je krijgt een transcriptie van een teamoverleg en moet een gestructureerde analyse maken met focus op:
1. Een duidelijke samenvatting van wat er besproken is
2. Een concrete actielijst met wie wat gaat doen

CONTEXT: Dit is een overleg van het programmateam Rotterdams WeerWoord, het klimaatadaptatieprogramma 
van de gemeente Rotterdam. Het team bespreekt regelmatig de voortgang van projecten, uitdagingen, 
en volgende stappen op het gebied van:
- Klimaatadaptatie en wateroverlast
- Hittestress en vergroening
- Samenwerking met bewoners en stakeholders
- Projectvoortgang en planning
- Budget en capaciteit

Identificeer en extraheer de volgende elementen:

1. SAMENVATTING: Een beknopte samenvatting van het overleg (max 300 woorden)
   - Wat was de hoofdlijn van het gesprek?
   - Welke onderwerpen kwamen aan bod?
   - Wat is de algemene stand van zaken?

2. AANWEZIGEN: Wie waren er bij het overleg (voor zover genoemd)

3. BESPROKEN PUNTEN: Voor elk besproken onderwerp:
   - Onderwerp/titel
   - Samenvatting van de discussie
   - Eventueel genomen besluit
   - Bijzondere opmerkingen

4. ACTIELIJST: Voor elke actie die is afgesproken:
   - Wat moet er gebeuren (concrete actie)
   - Wie is verantwoordelijk
   - Deadline (indien genoemd)
   - Prioriteit (hoog/middel/laag, inschatten op basis van context)

5. BESLUITEN: Formele besluiten of afspraken die zijn gemaakt

6. AANDACHTSPUNTEN: Zaken die aandacht behoeven, risico's, zorgen

7. VOLGENDE OVERLEG: Wanneer is het volgende overleg gepland (indien genoemd)

Geef je antwoord ALLEEN als valid JSON in het volgende formaat (geen andere tekst):
{
    "titel": "Programmateam Rotterdams WeerWoord",
    "datum": "...",
    "samenvatting": "...",
    "aanwezigen": ["naam 1", "naam 2"],
    "besproken_punten": [
        {
            "onderwerp": "...",
            "samenvatting": "...",
            "besluit": "...",
            "opmerkingen": "..."
        }
    ],
    "acties": [
        {
            "actie": "...",
            "verantwoordelijke": "...",
            "deadline": "...",
            "prioriteit": "hoog/middel/laag"
        }
    ],
    "besluiten": ["besluit 1", "besluit 2"],
    "aandachtspunten": ["punt 1", "punt 2"],
    "volgende_overleg": "...",
    "opmerkingen": "..."
}

Let extra op:
- Formuleer acties SMART: Specifiek, Meetbaar, Acceptabel, Realistisch, Tijdgebonden
- Als geen deadline is genoemd, laat het veld leeg (niet invullen met "niet genoemd")
- Prioriteit inschatten op basis van urgentie in de discussie
- Namen van teamleden correct overnemen
"""


def _call_gemini(prompt: str, system_prompt: str) -> str:
    """Roep Google Gemini aan voor tekstgeneratie (GRATIS tier)."""
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY ontbreekt. "
            "Haal een gratis API key op: https://aistudio.google.com/app/apikey"
        )
    
    import google.generativeai as genai
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=system_prompt,
    )
    
    print(f"Analyseren met Gemini ({GEMINI_MODEL})...")
    
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            temperature=0.3,
            max_output_tokens=8000,
        ),
    )
    
    return response.text


def _call_ollama(prompt: str, system_prompt: str) -> str:
    """Roep Ollama aan voor tekstgeneratie (lokaal)."""
    import httpx
    
    url = f"{OLLAMA_BASE_URL}/api/generate"
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_ctx": 32768,
        },
    }
    
    print(f"Analyseren met Ollama ({OLLAMA_MODEL})...")
    
    try:
        with httpx.Client(timeout=600.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
    except httpx.ConnectError:
        raise RuntimeError(
            "Kan geen verbinding maken met Ollama. "
            "Start Ollama met: ollama serve"
        )


def _call_openai(prompt: str, system_prompt: str) -> str:
    """Roep OpenAI aan voor tekstgeneratie (betaald)."""
    if not OPENAI_API_KEY:
        raise RuntimeError("CHATGPT_API_KEY ontbreekt.")
    
    from openai import OpenAI
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    print(f"Analyseren met OpenAI ({OPENAI_MODEL})...")
    
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=8000,
    )
    
    return response.choices[0].message.content or "{}"


def _call_llm(prompt: str, system_prompt: str) -> str:
    """Roep de geconfigureerde LLM aan."""
    provider = LLM_PROVIDER.lower()
    
    if provider == "gemini":
        return _call_gemini(prompt, system_prompt)
    elif provider == "ollama":
        return _call_ollama(prompt, system_prompt)
    elif provider == "openai":
        return _call_openai(prompt, system_prompt)
    else:
        raise RuntimeError(f"Onbekende LLM provider: {provider}")


def _extract_json_from_response(response: str) -> dict:
    """Haal JSON uit de LLM response."""
    # Probeer direct te parsen
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    # Zoek naar JSON block
    json_match = re.search(r'\{[\s\S]*\}', response)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # Zoek naar ```json blocks
    code_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
    if code_match:
        try:
            return json.loads(code_match.group(1))
        except json.JSONDecodeError:
            pass
    
    return {}


def analyse_gemeenteraad_vergadering(
    transcript: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> GemeenteraadAnalyse:
    """
    Analyseer een gemeenteraadsvergadering met AI.
    
    Ondersteunt: Gemini (gratis), Ollama (lokaal), OpenAI (betaald)
    """
    # Voeg context toe
    context = ""
    if metadata:
        context_parts = []
        if metadata.get("datum"):
            context_parts.append(f"Datum: {metadata['datum']}")
        if metadata.get("commissie"):
            context_parts.append(f"Commissie: {metadata['commissie']}")
        if metadata.get("titel"):
            context_parts.append(f"Titel: {metadata['titel']}")
        
        if context_parts:
            context = "CONTEXT VERGADERING:\n" + "\n".join(context_parts) + "\n\n"
    
    # Beperk transcript lengte
    max_chars = 100000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "\n\n[TRANSCRIPTIE INGEKORT]"
    
    user_message = f"{context}TRANSCRIPTIE:\n\n{transcript}"
    
    # Roep LLM aan
    try:
        result_text = _call_llm(user_message, SYSTEM_PROMPT_GEMEENTERAAD)
    except Exception as e:
        print(f"LLM fout: {e}")
        return GemeenteraadAnalyse(
            samenvatting="Analyse kon niet worden voltooid.",
            opmerkingen=str(e),
        )
    
    # Parse JSON
    data = _extract_json_from_response(result_text)
    
    if not data:
        return GemeenteraadAnalyse(
            samenvatting="Analyse kon niet worden geparsed.",
            opmerkingen=f"Response: {result_text[:500]}...",
        )
    
    # Parse resultaten
    moties = [
        Motie(
            nummer=m.get("nummer", ""),
            titel=m.get("titel", ""),
            indiener=m.get("indiener", ""),
            partij=m.get("partij", ""),
            samenvatting=m.get("samenvatting", ""),
            stemuitslag=m.get("stemuitslag", ""),
        )
        for m in data.get("moties", []) if isinstance(m, dict)
    ]
    
    amendementen = [
        Amendement(
            nummer=a.get("nummer", ""),
            titel=a.get("titel", ""),
            indiener=a.get("indiener", ""),
            partij=a.get("partij", ""),
            wijziging=a.get("wijziging", ""),
            stemuitslag=a.get("stemuitslag", ""),
        )
        for a in data.get("amendementen", []) if isinstance(a, dict)
    ]
    
    toezeggingen = [
        Toezegging(
            door=t.get("door", ""),
            aan=t.get("aan", ""),
            onderwerp=t.get("onderwerp", ""),
            deadline=t.get("deadline", ""),
            context=t.get("context", ""),
        )
        for t in data.get("toezeggingen", []) if isinstance(t, dict)
    ]
    
    sprekers = [
        Spreker(
            naam=s.get("naam", ""),
            functie=s.get("functie", ""),
            partij=s.get("partij", ""),
        )
        for s in data.get("sprekers", []) if isinstance(s, dict)
    ]
    
    print("Analyse voltooid!")
    
    return GemeenteraadAnalyse(
        samenvatting=data.get("samenvatting", ""),
        belangrijkste_punten=data.get("belangrijkste_punten", []),
        moties=moties,
        amendementen=amendementen,
        toezeggingen=toezeggingen,
        besluiten=data.get("besluiten", []),
        sprekers=sprekers,
        besproken_onderwerpen=data.get("besproken_onderwerpen", []),
        opmerkingen=data.get("opmerkingen", ""),
    )


def analyse_teamoverleg(
    transcript: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> TeamOverlegAnalyse:
    """
    Analyseer een intern teamoverleg (bijv. Rotterdams WeerWoord) met AI.
    
    Focus op:
    - Samenvatting van de discussie
    - Actielijst met verantwoordelijken
    """
    # Voeg context toe
    context = ""
    if metadata:
        context_parts = []
        if metadata.get("datum"):
            context_parts.append(f"Datum: {metadata['datum']}")
        if metadata.get("titel"):
            context_parts.append(f"Titel: {metadata['titel']}")
        
        if context_parts:
            context = "CONTEXT OVERLEG:\n" + "\n".join(context_parts) + "\n\n"
    
    # Beperk transcript lengte
    max_chars = 100000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "\n\n[TRANSCRIPTIE INGEKORT]"
    
    user_message = f"{context}TRANSCRIPTIE:\n\n{transcript}"
    
    # Roep LLM aan
    try:
        result_text = _call_llm(user_message, SYSTEM_PROMPT_TEAMOVERLEG)
    except Exception as e:
        print(f"LLM fout: {e}")
        return TeamOverlegAnalyse(
            samenvatting="Analyse kon niet worden voltooid.",
            opmerkingen=str(e),
        )
    
    # Parse JSON
    data = _extract_json_from_response(result_text)
    
    if not data:
        return TeamOverlegAnalyse(
            samenvatting="Analyse kon niet worden geparsed.",
            opmerkingen=f"Response: {result_text[:500]}...",
        )
    
    # Parse besproken punten
    besproken_punten = [
        BesprekingsPunt(
            onderwerp=p.get("onderwerp", ""),
            samenvatting=p.get("samenvatting", ""),
            besluit=p.get("besluit", ""),
            opmerkingen=p.get("opmerkingen", ""),
        )
        for p in data.get("besproken_punten", []) if isinstance(p, dict)
    ]
    
    # Parse acties
    acties = [
        ActieItem(
            actie=a.get("actie", ""),
            verantwoordelijke=a.get("verantwoordelijke", ""),
            deadline=a.get("deadline", ""),
            prioriteit=a.get("prioriteit", "middel"),
        )
        for a in data.get("acties", []) if isinstance(a, dict)
    ]
    
    print("Teamoverleg analyse voltooid!")
    
    return TeamOverlegAnalyse(
        titel=data.get("titel", "Teamoverleg"),
        datum=data.get("datum", ""),
        samenvatting=data.get("samenvatting", ""),
        aanwezigen=data.get("aanwezigen", []),
        besproken_punten=besproken_punten,
        acties=acties,
        besluiten=data.get("besluiten", []),
        aandachtspunten=data.get("aandachtspunten", []),
        volgende_overleg=data.get("volgende_overleg", ""),
        opmerkingen=data.get("opmerkingen", ""),
    )


# Legacy functies
def analyse_meeting(transcript: str) -> Dict[str, object]:
    """Legacy functie."""
    analyse = analyse_gemeenteraad_vergadering(transcript)
    return {
        "basisgegevens": {"datum": "N.n.b.", "tijd": "N.t.b.", "locatie": "Onbekend", "aanwezigen": "Onbekend"},
        "summary": analyse.samenvatting,
        "topics": [{"title": o.get("titel", ""), "details": o.get("samenvatting", "")} for o in analyse.besproken_onderwerpen],
        "decisions": analyse.besluiten,
        "actions": [],
        "risks": [],
    }


def generate_summary_report(analysis: Dict[str, object]) -> str:
    """Legacy functie."""
    return analysis.get("summary", "Geen samenvatting beschikbaar.")
