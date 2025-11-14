// Legal Document Comparator - Frontend Logic

// State management
const state = {
    file1: null,
    file2: null,
    results: null
};

// API Configuration
const API_BASE = window.location.origin;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    setupDropZones();
    setupFileInputs();
    setupCompareButton();
});

// Setup drag-and-drop zones
function setupDropZones() {
    const dropZones = [
        { zone: document.getElementById('dropZone1'), input: document.getElementById('file1'), num: 1 },
        { zone: document.getElementById('dropZone2'), input: document.getElementById('file2'), num: 2 }
    ];

    dropZones.forEach(({ zone, input, num }) => {
        // Click to upload
        zone.addEventListener('click', (e) => {
            if (!e.target.classList.contains('remove-btn')) {
                input.click();
            }
        });

        // Drag events
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('drag-over');
        });

        zone.addEventListener('dragleave', () => {
            zone.classList.remove('drag-over');
        });

        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('drag-over');
            
            const file = e.dataTransfer.files[0];
            if (file) {
                handleFileSelect(file, num);
            }
        });
    });
}

// Setup file input handlers
function setupFileInputs() {
    document.getElementById('file1').addEventListener('change', (e) => {
        if (e.target.files[0]) {
            handleFileSelect(e.target.files[0], 1);
        }
    });

    document.getElementById('file2').addEventListener('change', (e) => {
        if (e.target.files[0]) {
            handleFileSelect(e.target.files[0], 2);
        }
    });
}

// Handle file selection
function handleFileSelect(file, num) {
    // Validate file
    const maxSize = 10 * 1024 * 1024; // 10MB
    const allowedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
    
    if (file.size > maxSize) {
        alert('File is too large. Maximum size is 10MB.');
        return;
    }

    if (!allowedTypes.includes(file.type)) {
        alert('Invalid file type. Please upload PDF, PNG, or JPG files.');
        return;
    }

    // Store file
    if (num === 1) {
        state.file1 = file;
    } else {
        state.file2 = file;
    }

    // Update UI
    showFilePreview(file, num);
    updateCompareButton();
}

// Show file preview
function showFilePreview(file, num) {
    const dropZone = document.getElementById(`dropZone${num}`);
    const preview = document.getElementById(`preview${num}`);
    const content = dropZone.querySelector('.drop-zone-content');

    content.style.display = 'none';
    preview.style.display = 'flex';
    preview.querySelector('.file-name').textContent = file.name;
}

// Remove file
function removeFile(num) {
    if (num === 1) {
        state.file1 = null;
        document.getElementById('file1').value = '';
    } else {
        state.file2 = null;
        document.getElementById('file2').value = '';
    }

    const dropZone = document.getElementById(`dropZone${num}`);
    const preview = document.getElementById(`preview${num}`);
    const content = dropZone.querySelector('.drop-zone-content');

    content.style.display = 'block';
    preview.style.display = 'none';

    updateCompareButton();
}

// Update compare button state
function updateCompareButton() {
    const compareBtn = document.getElementById('compareBtn');
    compareBtn.disabled = !(state.file1 && state.file2);
}

// Setup compare button
function setupCompareButton() {
    document.getElementById('compareBtn').addEventListener('click', compareDocuments);
}

// Compare documents
async function compareDocuments() {
    const uploadSection = document.getElementById('uploadSection');
    const resultsSection = document.getElementById('resultsSection');
    const loading = document.getElementById('loading');
    const loadingText = document.getElementById('loadingText');

    // Show loading
    loading.style.display = 'block';
    loadingText.textContent = 'Extracting text...';

    try {
        // Prepare form data
        const formData = new FormData();
        formData.append('file1', state.file1);
        formData.append('file2', state.file2);

        // Make API request
        loadingText.textContent = 'Processing with AI...';
        const response = await fetch(`${API_BASE}/api/compare`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Comparison failed');
        }

        const results = await response.json();
        state.results = results;

        // Hide upload, show results
        loading.style.display = 'none';
        uploadSection.style.display = 'none';
        resultsSection.style.display = 'block';

        // Display results
        displayResults(results);

    } catch (error) {
        console.error('Error:', error);
        alert(`Error: ${error.message}`);
        loading.style.display = 'none';
    }
}

// Display results
function displayResults(results) {
    const summary = results.summary;
    const verdict = results.verdict;
    const differences = results.differences;
    const recommendations = results.recommendations;

    // Overall match score
    document.getElementById('scoreValue').textContent = `${summary.overall_match}%`;
    document.getElementById('verdictMessage').textContent = verdict.message;
    document.getElementById('verdictDescription').textContent = 
        `${summary.matched_sentences} of ${Math.max(summary.total_sentences_doc1, summary.total_sentences_doc2)} sentences matched`;

    // Set verdict card color
    const verdictCard = document.getElementById('verdictCard');
    verdictCard.style.background = getVerdictGradient(verdict.color);

    // Statistics
    document.getElementById('statMatched').textContent = summary.matched_sentences;
    document.getElementById('statExact').textContent = summary.exact_matches;
    document.getElementById('statDifferences').textContent = summary.significant_differences;
    document.getElementById('statReorderings').textContent = summary.reorderings_detected;

    // Recommendations
    if (recommendations && recommendations.length > 0) {
        const recommendationsDiv = document.getElementById('recommendations');
        const recommendationsList = document.getElementById('recommendationsList');
        
        recommendationsList.innerHTML = '';
        recommendations.forEach(rec => {
            const li = document.createElement('li');
            li.textContent = rec;
            recommendationsList.appendChild(li);
        });
        
        recommendationsDiv.style.display = 'block';
    }

    // Differences
    document.getElementById('diffCount').textContent = differences.length;
    displayDifferences(differences);
}

// Get verdict gradient color
function getVerdictGradient(color) {
    const gradients = {
        green: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
        yellow: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
        orange: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
        red: 'linear-gradient(135deg, #eb3349 0%, #f45c43 100%)'
    };
    return gradients[color] || gradients.green;
}

// Display differences
function displayDifferences(differences) {
    const container = document.getElementById('differencesList');
    container.innerHTML = '';

    if (differences.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #999; padding: 40px;">No differences found. Documents match perfectly!</p>';
        return;
    }

    differences.forEach((diff, index) => {
        const diffElement = createDifferenceElement(diff, index + 1);
        container.appendChild(diffElement);
    });
}

// Create difference element
function createDifferenceElement(diff, index) {
    const div = document.createElement('div');
    div.className = `difference-item severity-${diff.severity}`;

    const typeLabel = diff.classification.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    
    div.innerHTML = `
        <div class="difference-header">
            <span class="difference-type">
                #${index} - ${typeLabel}
            </span>
            <span class="similarity-badge">${(diff.similarity * 100).toFixed(1)}% match</span>
        </div>

        <div class="sentence-comparison">
            ${diff.sentence1 ? `
                <div class="sentence-box">
                    <div class="sentence-label">Document 1 (Position ${diff.position1})</div>
                    <div class="sentence-text">${escapeHtml(diff.sentence1)}</div>
                </div>
            ` : '<div class="sentence-box" style="background: #ffe0e0;"><div class="sentence-text">Missing in Document 1</div></div>'}

            ${diff.sentence2 ? `
                <div class="sentence-box">
                    <div class="sentence-label">Document 2 (Position ${diff.position2})</div>
                    <div class="sentence-text">${escapeHtml(diff.sentence2)}</div>
                </div>
            ` : '<div class="sentence-box" style="background: #ffe0e0;"><div class="sentence-text">Missing in Document 2</div></div>'}
        </div>

        ${diff.suggestions && diff.suggestions.length > 0 ? `
            <div class="suggestions">
                <div class="suggestions-title">Possible Causes:</div>
                <ul>
                    ${diff.suggestions.map(s => `<li>${escapeHtml(s)}</li>`).join('')}
                </ul>
            </div>
        ` : ''}
    `;

    return div;
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Reset comparison
function resetComparison() {
    state.file1 = null;
    state.file2 = null;
    state.results = null;

    document.getElementById('file1').value = '';
    document.getElementById('file2').value = '';

    removeFile(1);
    removeFile(2);

    document.getElementById('uploadSection').style.display = 'block';
    document.getElementById('resultsSection').style.display = 'none';

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Health check on load
fetch(`${API_BASE}/api/health`)
    .then(res => res.json())
    .then(data => {
        console.log('API Health:', data);
    })
    .catch(err => {
        console.warn('API health check failed:', err);
    });
