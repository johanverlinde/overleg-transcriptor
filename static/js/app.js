/**
 * Raadsverslag - Gemeenteraad Transcriptor
 * Frontend JavaScript Application
 */

// ==========================================================================
// DOM ELEMENTS
// ==========================================================================

const tabs = document.querySelectorAll('.tab');
const tabContents = document.querySelectorAll('.tab-content');

// URL Form
const urlForm = document.getElementById('urlForm');
const videoUrlInput = document.getElementById('videoUrl');
const previewBtn = document.getElementById('previewBtn');
const metadataPreview = document.getElementById('metadataPreview');
const clearPreviewBtn = document.getElementById('clearPreview');

// Upload Form
const uploadForm = document.getElementById('uploadForm');
const uploadZone = document.getElementById('uploadZone');
const audioFileInput = document.getElementById('audioFile');
const selectedFileDiv = document.getElementById('selectedFile');
const fileNameSpan = document.getElementById('fileName');
const clearFileBtn = document.getElementById('clearFile');

// Transcript Form
const transcriptForm = document.getElementById('transcriptForm');
const transcriptTitle = document.getElementById('transcriptTitle');
const transcriptText = document.getElementById('transcriptText');

// Sections
const progressSection = document.getElementById('progressSection');
const resultsSection = document.getElementById('resultsSection');
const errorSection = document.getElementById('errorSection');

// Progress
const progressSteps = document.getElementById('progressSteps');
const progressSubtitle = document.getElementById('progressSubtitle');

// Results
const downloadBtn = document.getElementById('downloadBtn');
const summaryText = document.getElementById('summaryText');
const keyPointsList = document.getElementById('keyPointsList');
const motiesCount = document.getElementById('motiesCount');
const motiesList = document.getElementById('motiesList');
const toezeggingenCount = document.getElementById('toezeggingenCount');
const toezeggingenList = document.getElementById('toezeggingenList');
const amendementenStat = document.getElementById('amendementenStat');
const besluitenStat = document.getElementById('besluitenStat');
const sprekersStat = document.getElementById('sprekersStat');
const newAnalysisBtn = document.getElementById('newAnalysisBtn');

// Error
const errorMessage = document.getElementById('errorMessage');
const retryBtn = document.getElementById('retryBtn');

// ==========================================================================
// INITIALIZATION - Ensure clean state on page load
// ==========================================================================

(function initializeApp() {
  // Force hide all result/error sections on page load
  [progressSection, resultsSection, errorSection].forEach(section => {
    if (section) {
      section.classList.add('hidden');
      section.style.display = 'none';
    }
  });
  console.log('App initialized - sections hidden');
})();

// ==========================================================================
// TAB SWITCHING
// ==========================================================================

tabs.forEach(tab => {
  tab.addEventListener('click', () => {
    const tabId = tab.dataset.tab;
    
    // Update tab buttons
    tabs.forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    
    // Update tab content
    tabContents.forEach(content => {
      content.classList.remove('active');
      if (content.id === `${tabId}-tab`) {
        content.classList.add('active');
      }
    });
  });
});

// ==========================================================================
// MEETING TYPE SELECTION
// ==========================================================================

const meetingTypeSelect = document.getElementById('meetingType');
const meetingTypeHint = document.getElementById('meetingTypeHint');

if (meetingTypeSelect) {
  meetingTypeSelect.addEventListener('change', () => {
    const hints = {
      'gemeenteraad': 'Analyse gericht op moties, amendementen en toezeggingen',
      'teamoverleg': 'Analyse gericht op samenvatting en actielijst met verantwoordelijken'
    };
    if (meetingTypeHint) {
      meetingTypeHint.textContent = hints[meetingTypeSelect.value] || hints['gemeenteraad'];
    }
  });
}

// ==========================================================================
// FILE UPLOAD HANDLING
// ==========================================================================

// Drag and drop
uploadZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  uploadZone.classList.add('dragover');
});

uploadZone.addEventListener('dragleave', () => {
  uploadZone.classList.remove('dragover');
});

uploadZone.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadZone.classList.remove('dragover');
  
  if (e.dataTransfer.files.length) {
    audioFileInput.files = e.dataTransfer.files;
    showSelectedFile(e.dataTransfer.files[0]);
  }
});

audioFileInput.addEventListener('change', () => {
  if (audioFileInput.files.length) {
    showSelectedFile(audioFileInput.files[0]);
  }
});

function showSelectedFile(file) {
  fileNameSpan.textContent = file.name;
  uploadZone.classList.add('hidden');
  selectedFileDiv.classList.remove('hidden');
}

clearFileBtn.addEventListener('click', () => {
  audioFileInput.value = '';
  selectedFileDiv.classList.add('hidden');
  uploadZone.classList.remove('hidden');
});

// ==========================================================================
// URL PREVIEW
// ==========================================================================

previewBtn.addEventListener('click', async () => {
  const url = videoUrlInput.value.trim();
  if (!url) {
    alert('Voer eerst een URL in.');
    return;
  }
  
  previewBtn.disabled = true;
  previewBtn.innerHTML = `
    <svg class="spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <circle cx="12" cy="12" r="10" stroke-dasharray="60" stroke-dashoffset="30"/>
    </svg>
    Laden...
  `;
  
  try {
    const response = await fetch(`/api/scrape-metadata?url=${encodeURIComponent(url)}`);
    const data = await response.json();
    
    if (response.ok && data.status === 'success') {
      displayMetadataPreview(data.metadata);
    } else {
      throw new Error(data.detail || 'Kon metadata niet ophalen');
    }
  } catch (error) {
    alert(`Fout: ${error.message}`);
  } finally {
    previewBtn.disabled = false;
    previewBtn.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="8"/>
        <line x1="21" y1="21" x2="16.65" y2="16.65"/>
      </svg>
      Preview
    `;
  }
});

function displayMetadataPreview(metadata) {
  document.getElementById('previewCommissie').textContent = metadata.commissie || '-';
  document.getElementById('previewDatum').textContent = metadata.datum || '-';
  document.getElementById('previewTijd').textContent = metadata.tijd || '-';
  document.getElementById('previewLocatie').textContent = metadata.locatie || '-';
  
  const videoStatus = document.getElementById('previewVideo');
  if (metadata.video_beschikbaar) {
    // Check if it's CompanyWebcast (Rotterdam)
    const isCompanyWebcast = metadata.commissie && 
      (metadata.commissie.toLowerCase().includes('commissie') || 
       metadata.commissie.toLowerCase().includes('vergadering'));
    
    if (isCompanyWebcast) {
      videoStatus.innerHTML = '<span class="badge badge-warning">Handmatig downloaden vereist</span>';
    } else {
      videoStatus.innerHTML = '<span class="badge badge-success">Beschikbaar</span>';
    }
  } else {
    videoStatus.innerHTML = '<span class="badge badge-error">Niet gevonden</span>';
  }
  
  metadataPreview.classList.remove('hidden');
}

clearPreviewBtn.addEventListener('click', () => {
  metadataPreview.classList.add('hidden');
});

// ==========================================================================
// PROGRESS HANDLING
// ==========================================================================

function setStepState(step, state) {
  const stepEl = progressSteps.querySelector(`[data-step="${step}"]`);
  if (!stepEl) return;
  
  stepEl.classList.remove('active', 'done');
  
  const statusEl = stepEl.querySelector('.step-status');
  
  switch (state) {
    case 'active':
      stepEl.classList.add('active');
      statusEl.textContent = 'Bezig...';
      break;
    case 'done':
      stepEl.classList.add('done');
      statusEl.textContent = 'Voltooid';
      break;
    default:
      statusEl.textContent = 'Wachten...';
  }
}

function resetProgress() {
  ['download', 'transcribe', 'analyze', 'report'].forEach(step => {
    setStepState(step, '');
  });
}

function showSection(section) {
  // Force hide ALL sections first
  const allSections = [progressSection, resultsSection, errorSection];
  allSections.forEach(s => {
    if (s) {
      s.classList.add('hidden');
      s.style.display = 'none';
    }
  });
  
  // Show requested section
  if (section) {
    section.classList.remove('hidden');
    section.style.display = '';
    
    // Scroll to section after a brief delay to ensure DOM update
    requestAnimationFrame(() => {
      section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }
}

function hideAllSections() {
  const allSections = [progressSection, resultsSection, errorSection];
  allSections.forEach(s => {
    if (s) {
      s.classList.add('hidden');
      s.style.display = 'none';
    }
  });
}

// ==========================================================================
// URL FORM SUBMISSION
// ==========================================================================

urlForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const url = videoUrlInput.value.trim();
  if (!url) {
    alert('Voer een URL in.');
    return;
  }

  // Show progress
  resetProgress();
  showSection(progressSection);
  
  try {
    // Step 1: Download
    setStepState('download', 'active');
    progressSubtitle.textContent = 'Video wordt opgehaald van de server...';
    
    // Make the API call
    const response = await fetch('/api/analyze-url', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ url }),
    });
    
    // Simulate step progress during the long request
    setStepState('download', 'done');
    setStepState('transcribe', 'active');
    progressSubtitle.textContent = 'Audio wordt getranscribeerd...';
    
    // Wait a bit for visual feedback
    await new Promise(r => setTimeout(r, 500));
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Er ging iets mis');
    }
    
    setStepState('transcribe', 'done');
    setStepState('analyze', 'active');
    progressSubtitle.textContent = 'Vergadering wordt geanalyseerd...';
    
    await new Promise(r => setTimeout(r, 500));
    
    const data = await response.json();
    
    setStepState('analyze', 'done');
    setStepState('report', 'active');
    progressSubtitle.textContent = 'Rapport wordt gegenereerd...';
    
    await new Promise(r => setTimeout(r, 500));
    
    setStepState('report', 'done');
    
    // Display results
    displayResults(data);
    
    await new Promise(r => setTimeout(r, 500));
    showSection(resultsSection);
    
  } catch (error) {
    showError(error.message);
  }
});

// ==========================================================================
// UPLOAD FORM SUBMISSION
// ==========================================================================

uploadForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  
  if (!audioFileInput.files.length) {
    alert('Selecteer eerst een bestand.');
    return;
  }
  
  const file = audioFileInput.files[0];
  const formData = new FormData();
  formData.append('file', file);
  
  // Bepaal het type overleg en de juiste API endpoint
  const meetingTypeSelect = document.getElementById('meetingType');
  const meetingType = meetingTypeSelect ? meetingTypeSelect.value : 'gemeenteraad';
  const apiEndpoint = meetingType === 'teamoverleg' ? '/api/analyze-teamoverleg' : '/api/analyze';
  
  // Show progress
  resetProgress();
  showSection(progressSection);
  
  // Skip download step for uploads
  setStepState('download', 'done');
  
  try {
    setStepState('transcribe', 'active');
    const progressText = meetingType === 'teamoverleg' 
      ? 'Teamoverleg wordt verwerkt en getranscribeerd...'
      : 'Bestand wordt verwerkt en getranscribeerd...';
    progressSubtitle.textContent = progressText;

    const response = await fetch(apiEndpoint, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Er ging iets mis');
    }
    
    setStepState('transcribe', 'done');
    setStepState('analyze', 'active');
    progressSubtitle.textContent = 'Inhoud wordt geanalyseerd...';
    
    await new Promise(r => setTimeout(r, 500));

    const data = await response.json();

    setStepState('analyze', 'done');
    setStepState('report', 'done');
    
    // Display results
    displayResults(data);
    
    await new Promise(r => setTimeout(r, 500));
    showSection(resultsSection);
    
  } catch (error) {
    showError(error.message);
  }
});

// ==========================================================================
// TRANSCRIPT FORM SUBMISSION
// ==========================================================================

transcriptForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const transcript = transcriptText.value.trim();
  const titel = transcriptTitle.value.trim() || 'Vergadering';
  
  if (!transcript || transcript.length < 100) {
    alert('Voer een transcriptie in (minimaal 100 karakters).');
    return;
  }
  
  // Show progress
  resetProgress();
  showSection(progressSection);
  
  // Skip download and transcribe steps
  setStepState('download', 'done');
  setStepState('transcribe', 'done');
  
  try {
    setStepState('analyze', 'active');
    progressSubtitle.textContent = 'Transcriptie wordt geanalyseerd met AI...';

    const response = await fetch('/api/analyze-transcript', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ transcript, titel }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Er ging iets mis');
    }
    
    setStepState('analyze', 'done');
    setStepState('report', 'active');
    progressSubtitle.textContent = 'Rapport wordt gegenereerd...';
    
    await new Promise(r => setTimeout(r, 500));

    const data = await response.json();

    setStepState('report', 'done');
    
    // Display results
    displayResults(data);
    
    await new Promise(r => setTimeout(r, 500));
    showSection(resultsSection);
    
  } catch (error) {
    showError(error.message);
  }
});

// ==========================================================================
// RESULTS DISPLAY
// ==========================================================================

function displayResults(data) {
  try {
    // Download button
    if (downloadBtn && data.downloadUrl) {
      downloadBtn.href = data.downloadUrl;
    }
    
    // Summary
    if (summaryText) {
      summaryText.textContent = data.analyse?.samenvatting || 'Geen samenvatting beschikbaar.';
    }
    
    // Detecteer of dit een teamoverleg is (heeft acties ipv moties)
    const isTeamoverleg = data.analyse?.acties !== undefined;
    
    if (isTeamoverleg) {
      // ============= TEAMOVERLEG RESULTATEN =============
      
      // Key points: toon aanwezigen of aandachtspunten
      if (keyPointsList) {
        const aandachtspunten = data.analyse?.aandachtspunten || [];
        if (aandachtspunten.length) {
          keyPointsList.innerHTML = aandachtspunten
            .map(punt => `<li>${escapeHtml(punt)}</li>`)
            .join('');
        } else {
          keyPointsList.innerHTML = '<li>Geen specifieke aandachtspunten geïdentificeerd.</li>';
        }
      }
      
      // Acties in plaats van moties
      const acties = data.analyse?.acties || [];
      if (motiesCount) motiesCount.textContent = acties.length;
      
      // Update label voor moties sectie
      const motiesLabel = document.querySelector('.results-card h3');
      if (motiesLabel && motiesLabel.textContent.includes('Moties')) {
        motiesLabel.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg> Actielijst';
      }
      
      if (motiesList) {
        if (acties.length) {
          motiesList.innerHTML = acties.map(actie => `
            <div class="motie-item">
              <span class="titel">${escapeHtml(actie.actie || 'Onbekende actie')}</span>
              <span class="meta">
                ${actie.verantwoordelijke ? `Verantwoordelijke: ${escapeHtml(actie.verantwoordelijke)}` : ''}
                ${actie.deadline ? ` • Deadline: ${escapeHtml(actie.deadline)}` : ''}
              </span>
              ${actie.prioriteit ? `<span class="badge badge-${actie.prioriteit === 'hoog' ? 'danger' : actie.prioriteit === 'middel' ? 'warning' : 'success'}">${escapeHtml(actie.prioriteit)}</span>` : ''}
            </div>
          `).join('');
        } else {
          motiesList.innerHTML = '<p class="empty-state">Geen acties geïdentificeerd in dit overleg.</p>';
        }
      }
      
      // Lege toezeggingen sectie voor teamoverleg
      if (toezeggingenCount) toezeggingenCount.textContent = 0;
      if (toezeggingenList) {
        toezeggingenList.innerHTML = '<p class="empty-state">N.v.t. voor teamoverleg</p>';
      }
      
      // Stats
      if (amendementenStat) amendementenStat.textContent = '-';
      if (besluitenStat) besluitenStat.textContent = data.analyse?.besluiten_count ?? 0;
      if (sprekersStat) sprekersStat.textContent = data.analyse?.aanwezigen?.length ?? '-';
      
    } else {
      // ============= GEMEENTERAAD RESULTATEN =============
      
      // Key points
      if (keyPointsList) {
        if (data.analyse?.belangrijkste_punten?.length) {
          keyPointsList.innerHTML = data.analyse.belangrijkste_punten
            .map(punt => `<li>${escapeHtml(punt)}</li>`)
            .join('');
        } else {
          keyPointsList.innerHTML = '<li>Geen belangrijke punten geïdentificeerd.</li>';
        }
      }
      
      // Moties
      const moties = data.analyse?.moties || [];
      if (motiesCount) motiesCount.textContent = moties.length;
      
      if (motiesList) {
        if (moties.length) {
          motiesList.innerHTML = moties.map(motie => `
            <div class="motie-item">
              <span class="titel">${escapeHtml(motie.titel || 'Onbekende motie')}</span>
              <span class="meta">
                ${motie.indiener ? `Ingediend door: ${escapeHtml(motie.indiener)}` : ''}
                ${motie.partij ? ` (${escapeHtml(motie.partij)})` : ''}
              </span>
              ${motie.stemuitslag ? `<span class="badge ${getStemuitslagBadgeClass(motie.stemuitslag)}">${escapeHtml(motie.stemuitslag)}</span>` : ''}
            </div>
          `).join('');
        } else {
          motiesList.innerHTML = '<p class="empty-state">Geen moties gevonden in deze vergadering.</p>';
        }
      }
      
      // Toezeggingen
      const toezeggingen = data.analyse?.toezeggingen || [];
      if (toezeggingenCount) toezeggingenCount.textContent = toezeggingen.length;
      
      if (toezeggingenList) {
        if (toezeggingen.length) {
          toezeggingenList.innerHTML = toezeggingen.map(toezegging => `
            <div class="toezegging-item">
              <span class="onderwerp">${escapeHtml(toezegging.onderwerp || 'Onbekende toezegging')}</span>
              <span class="meta">
                ${toezegging.door ? `Door: ${escapeHtml(toezegging.door)}` : ''}
                ${toezegging.deadline ? ` • Deadline: ${escapeHtml(toezegging.deadline)}` : ''}
              </span>
            </div>
          `).join('');
        } else {
          toezeggingenList.innerHTML = '<p class="empty-state">Geen toezeggingen gevonden in deze vergadering.</p>';
        }
      }
      
      // Stats
      if (amendementenStat) amendementenStat.textContent = data.analyse?.amendementen_count ?? 0;
      if (besluitenStat) besluitenStat.textContent = data.analyse?.besluiten_count ?? 0;
      if (sprekersStat) sprekersStat.textContent = data.analyse?.sprekers_count ?? '-';
    }
    
    console.log('Results displayed successfully', data);
  } catch (error) {
    console.error('Error displaying results:', error);
  }
}



function getStemuitslagBadgeClass(stemuitslag) {
  const lower = stemuitslag.toLowerCase();
  if (lower.includes('aangenomen') || lower.includes('akkoord')) {
    return 'badge-success';
  }
  if (lower.includes('verworpen') || lower.includes('afgewezen')) {
    return 'badge-error';
  }
  if (lower.includes('ingetrokken') || lower.includes('aangehouden')) {
    return 'badge-warning';
  }
  return '';
}

// ==========================================================================
// ERROR HANDLING
// ==========================================================================

function showError(message) {
  if (!errorMessage || !errorSection) {
    console.error('Error elements not found:', message);
    alert(`Fout: ${message}`);
    return;
  }
  
  // Format multiline errors with line breaks
  if (message && message.includes('\n')) {
    errorMessage.innerHTML = message.replace(/\n/g, '<br>');
  } else {
    errorMessage.textContent = message || 'Er is een onbekende fout opgetreden.';
  }
  showSection(errorSection);
}

retryBtn.addEventListener('click', () => {
  hideAllSections();
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

// ==========================================================================
// NEW ANALYSIS
// ==========================================================================

newAnalysisBtn.addEventListener('click', () => {
  // Reset forms
  urlForm.reset();
  uploadForm.reset();
  transcriptForm.reset();
  
  // Hide file selection
  selectedFileDiv.classList.add('hidden');
  uploadZone.classList.remove('hidden');
  
  // Hide metadata preview
  metadataPreview.classList.add('hidden');
  
  // Hide results
  hideAllSections();
  
  // Scroll to top
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

// ==========================================================================
// UTILITIES
// ==========================================================================

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Add spinning animation CSS
const style = document.createElement('style');
style.textContent = `
  .spin {
    animation: spin 1s linear infinite;
  }
  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
`;
document.head.appendChild(style);
