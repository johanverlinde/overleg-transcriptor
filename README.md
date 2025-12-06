# Raadsverslag — Gemeenteraad Transcriptor

Een moderne webapplicatie voor het automatisch transcriberen en analyseren van gemeenteraadsvergaderingen. Upload een audio/video bestand of plak een URL van een vergaderpagina, en ontvang een compleet verslag met moties, toezeggingen, amendementen en meer.

## Features

- 🎥 **Video-ondersteuning**: Download automatisch video's van gemeenteraad websites (o.a. Rotterdam, Amsterdam)
- 🎙️ **Nauwkeurige transcriptie**: Spraak-naar-tekst met OpenAI Whisper
- 🤖 **AI-analyse**: Automatische extractie van moties, toezeggingen, amendementen en besluiten
- 📄 **Word-rapporten**: Professionele verslagen met alle details
- 🌐 **URL-scraping**: Metadata ophalen van vergaderpagina's (iBabs)

## Ondersteunde platforms

- **gemeenteraad.rotterdam.nl** (iBabs met CompanyWebcast)
- **Andere iBabs-gebaseerde gemeenteraad sites**
- **YouTube** en andere video platforms (via yt-dlp)
- **Directe video/audio uploads** (MP3, WAV, M4A, MP4)

## Installatie

### Vereisten

- Python 3.10 of hoger
- FFmpeg (voor audio-extractie uit video's)
- OpenAI API key

### FFmpeg installeren

**macOS (met Homebrew):**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install ffmpeg
```

**Windows:**
Download van [ffmpeg.org](https://ffmpeg.org/download.html) en voeg toe aan PATH.

### Applicatie installeren

1. **Clone de repository** of download de bestanden

2. **Maak een virtuele omgeving aan** (aanbevolen):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. **Installeer dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Configuratie

Stel de volgende omgevingsvariabelen in:

```bash
# Verplicht: OpenAI API key
export CHATGPT_API_KEY="sk-..."

# Optioneel: Model voor transcriptie (standaard: gpt-4o-transcribe)
export CHATGPT_TRANSCRIPTION_MODEL="gpt-4o-transcribe"

# Optioneel: Model voor analyse (standaard: gpt-4o)
export CHATGPT_MODEL="gpt-4o"

# Optioneel: FFmpeg pad (indien niet in PATH)
export FFMPEG_PATH="/usr/local/bin/ffmpeg"
```

Je kunt ook een `.env` bestand maken in de projectroot.

## Applicatie starten

```bash
uvicorn app.main:app --reload
```

Open daarna [http://localhost:8000](http://localhost:8000) in je browser.

## Gebruik

### 1. URL-analyse (aanbevolen voor gemeenteraadsvergaderingen)

1. Ga naar een vergaderpagina, bijv. [Commissie BWB Rotterdam](https://gemeenteraad.rotterdam.nl/Agenda/Index/2d53fee1-0f9f-4a17-9084-034d4405443a)
2. Kopieer de URL
3. Plak de URL in het "URL invoeren" veld
4. Klik op "Preview" om de vergaderinfo te controleren
5. Klik op "Start analyse"
6. Wacht tot de analyse klaar is (kan enkele minuten duren)
7. Download het Word-rapport

### 2. Bestand uploaden

1. Klik op de "Bestand uploaden" tab
2. Sleep een audio/video bestand naar het upload gebied of klik om te selecteren
3. Klik op "Start analyse"
4. Download het Word-rapport

## API Endpoints

| Methode | Endpoint | Beschrijving |
|---------|----------|--------------|
| `GET` | `/` | Web interface |
| `POST` | `/api/analyze-url` | Analyseer vergadering vanaf URL |
| `POST` | `/api/analyze` | Analyseer geüpload bestand |
| `GET` | `/api/scrape-metadata?url=...` | Haal metadata op van vergaderpagina |
| `GET` | `/api/report/{report_id}` | Download gegenereerd rapport |

### Voorbeeld: URL analyse

```bash
curl -X POST "http://localhost:8000/api/analyze-url" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://gemeenteraad.rotterdam.nl/Agenda/Index/..."}'
```

## Projectstructuur

```
app/
├── main.py                     # FastAPI routes
├── services/
│   ├── transcription_service.py    # Audio transcriptie (OpenAI)
│   ├── meeting_analysis_service.py # AI-analyse van vergaderingen
│   ├── video_download_service.py   # Video download & audio extractie
│   ├── scraper_service.py          # URL scraping voor metadata
│   └── report_service.py           # Word rapport generatie
static/
├── css/styles.css              # Styling
└── js/app.js                   # Frontend JavaScript
templates/
└── index.html                  # Web interface
```

## Gegenereerd rapport bevat

Het Word-rapport bevat de volgende secties:

1. **Basisgegevens** - Datum, tijd, locatie, voorzitter
2. **Samenvatting** - Korte samenvatting van de vergadering
3. **Moties** - Alle ingediende moties met indiener, partij en stemuitslag
4. **Amendementen** - Wijzigingsvoorstellen op raadsvoorstellen
5. **Toezeggingen** - Toezeggingen door wethouders aan de raad
6. **Besluiten** - Formele besluiten
7. **Besproken onderwerpen** - Overzicht van agendapunten
8. **Sprekers** - Lijst van sprekers met functie en partij
9. **Bijlage: Transcriptie** - Volledige getranscribeerde tekst

## Tips

- **Lange vergaderingen**: Vergaderingen van 2+ uur kunnen enkele minuten duren om te analyseren
- **Nauwkeurigheid**: Controleer altijd de output; AI-transcriptie kan namen verkeerd transcriberen
- **Kosten**: Transcriptie en analyse gebruiken OpenAI API credits

## Probleemoplossing

### FFmpeg niet gevonden
Zorg dat FFmpeg geïnstalleerd is en in je PATH staat, of stel `FFMPEG_PATH` in.

### Video download mislukt
Sommige video's zijn beveiligd. Probeer de pagina URL in plaats van een directe video URL.

### API errors
Controleer of je `CHATGPT_API_KEY` correct is ingesteld en voldoende credits hebt.

## Licentie

Dit project is opgezet als voorbeeld en kan vrij worden aangepast.
