// ============================================
// Legal Document Comparator - Production Ready
// Fixed: Single export system, consistent state management
// ============================================
console.log("LDC Script loaded successfully");

// Namespace to avoid global pollution
window.LDC = window.LDC || {};

(function (LDC) {
'use strict';

/* =========================
   CONSTANTS & CONFIGURATION
========================= */
const CONFIG = {
    MAX_FILE_SIZE: 10 * 1024 * 1024,
    ALLOWED_TYPES: [
        'application/pdf',
        'image/png',
        'image/jpeg',
        'image/jpg',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/octet-stream'
    ],
    PARAGRAPH_GAP_THRESHOLD: 20,
    MAX_TOASTS: 3,
    TOAST_DURATION: 3000,
    AUTO_ADVANCE_DELAY: 500,
    SCROLL_DEBOUNCE: 50
};

/* =========================
   STATE (Single Source)
========================= */
const state = {
    file1: null,
    file2: null,
    comparisonData: null,
    reportId: null,
    differences: [],
    currentDiffIndex: -1,
    userDecisions: {},
    userComments: {},
    globalNotes: "",
    sentences1: [],
    sentences2: [],
    sentenceCache: { doc1: null, doc2: null },
    toastQueue: []
};

/* =========================
   UTILITIES
========================= */
const Utils = {
    positionToIndex: p => (p && p > 0 ? p - 1 : null),
    indexToPosition: i => (i !== null && i >= 0 ? i + 1 : null),
    escapeHtml(text) {
        const d = document.createElement('div');
        d.textContent = text || '';
        return d.innerHTML;
    },
    debounce(fn, wait) {
        let t;
        return (...a) => {
            clearTimeout(t);
            t = setTimeout(() => fn(...a), wait);
        };
    },
    getElement(id) {
        const el = document.getElementById(id);
        if (!el) console.warn(`Element not found: ${id}`);
        return el;
    }
};


// ============================================
// ADAPTIVE RECONSTRUCTOR
// ============================================
class AdaptiveReconstructor {
    constructor() {
        this.analysisLog = [];
    }

    analyzeDocument(sentences) {
        if (!sentences || sentences.length === 0) {
            return { error: 'No sentences to analyze' };
        }

        const analysis = {
            hasLineIds: sentences.every(s => s.line_id !== undefined),
            hasCharPositions: sentences.every(s =>
                s.start_char !== undefined && s.end_char !== undefined
            ),
            hasCollapsedSentences: sentences.some(s =>
                s.collapsed_count && s.collapsed_count > 1
            ),
            avgSentenceLength: sentences.reduce((sum, s) =>
                sum + (s.text?.length || 0), 0
            ) / sentences.length,
            shortSentenceCount: sentences.filter(s =>
                (s.text?.length || 0) <= 5
            ).length,
            allUppercase: sentences.filter(s =>
                s.text && s.text === s.text.toUpperCase()
            ).length / sentences.length > 0.5,
            hasNumberedItems: sentences.some(s => /^\d+\./.test(s.text || ''))
        };

        this.log(`Document analyzed: ${sentences.length} sentences`, 'info');
        return analysis;
    }

    chooseStrategy(analysis) {
        if (analysis.error) {
            this.log('Strategy: SEQUENTIAL (error)', 'error');
            return 'sequential';
        }

        if (analysis.hasNumberedItems ||
            (analysis.allUppercase && analysis.avgSentenceLength < 30)) {
            this.log('Strategy: SEQUENTIAL (lists/names)', 'success');
            return 'sequential';
        }

        if (analysis.hasCollapsedSentences) {
            this.log('Strategy: SEQUENTIAL (collapsed)', 'success');
            return 'sequential';
        }

        if (analysis.hasCharPositions) {
            this.log('Strategy: SMART HYBRID', 'success');
            return 'smart';
        }

        this.log('Strategy: SEQUENTIAL (fallback)', 'warning');
        return 'sequential';
    }

    reconstruct(sentences, matchMap) {
        this.analysisLog = [];

        if (!sentences || sentences.length === 0) {
            return {
                html: '<p class="error">No content to display</p>',
                strategy: 'error',
                analysis: this.analysisLog
            };
        }

        const analysis = this.analyzeDocument(sentences);
        const strategy = this.chooseStrategy(analysis);

        let html = '';
        if (strategy === 'sequential') {
            html = this.sequentialStrategy(sentences, matchMap);
        } else {
            html = this.smartHybridStrategy(sentences, matchMap);
        }

        return { html, strategy, analysis: this.analysisLog };
    }

    sequentialStrategy(sentences, matchMap) {
        const fragment = [];

        sentences.forEach(sent => {
            const matchStatus = matchMap[sent.id] || 'unknown';
            const cssClass = matchStatus === 'exact' ? 'match' :
                             matchStatus === 'diff' ? 'diff' : 'missing';

            let debugInfo = '';
            if (sent.collapsed_count && sent.collapsed_count > 1) {
                debugInfo = ` <small class="collapsed-info" title="This represents ${sent.collapsed_count} merged sentences">[${sent.collapsed_count} merged]</small>`;
            }

            const diffId = matchMap[sent.id + '_diffId'] || '';
            const dataAttrs = `data-id="${sent.id}" data-diff-id="${diffId}"`;

            fragment.push(
                `<p>
                    <span class="sentence ${cssClass}" ${dataAttrs}>
                        ${Utils.escapeHtml(sent.text)}${debugInfo}
                    </span>
                </p>`
            );
        });

        return fragment.join('');
    }

    smartHybridStrategy(sentences, matchMap) {
        const fragment = [];
        let currentParagraph = [];

        sentences.forEach((sent, idx) => {
            const matchStatus = matchMap[sent.id] || 'unknown';
            const cssClass = matchStatus === 'exact' ? 'match' :
                             matchStatus === 'diff' ? 'diff' : 'missing';

            let shouldBreak = false;

            if (idx > 0) {
                const prevSent = sentences[idx - 1];

                if (sent.start_char !== undefined && prevSent.end_char !== undefined) {
                    const gap = sent.start_char - prevSent.end_char;
                    if (gap > CONFIG.PARAGRAPH_GAP_THRESHOLD) {
                        shouldBreak = true;
                    }
                }

                if ((sent.text?.length || 0) <= 3 && /^[IVX]+\.$/.test(sent.text || '')) {
                    shouldBreak = true;
                }
            }

            if (shouldBreak && currentParagraph.length > 0) {
                fragment.push(`<p>${currentParagraph.join(' ')}</p>`);
                currentParagraph = [];
            }

            let debugInfo = '';
            if (sent.collapsed_count && sent.collapsed_count > 1) {
                debugInfo = ` <small class="collapsed-info" title="This represents ${sent.collapsed_count} merged sentences">[${sent.collapsed_count} merged]</small>`;
            }

            const diffId = matchMap[sent.id + '_diffId'] || '';
            const dataAttrs = `data-id="${sent.id}" data-diff-id="${diffId}"`;

            currentParagraph.push(
                `<span class="sentence ${cssClass}" ${dataAttrs}>
                    ${Utils.escapeHtml(sent.text)}${debugInfo}
                </span>`
            );
        });

        if (currentParagraph.length > 0) {
            fragment.push(`<p>${currentParagraph.join(' ')}</p>`);
        }

        return fragment.join('');
    }

    log(message, type = 'info') {
        this.analysisLog.push({ message, type, timestamp: Date.now() });
    }
}

// ============================================
// INITIALIZATION
// ============================================
function initialize() {
    setupDropZones();
    setupFileInputs();
    setupKeyboardShortcuts();
    setupModalAccessibility();
}

// ============================================
// FILE UPLOAD HANDLING
// ============================================
function setupDropZones() {
    const zones = [
        { zone: Utils.getElement('dropZone1'), input: Utils.getElement('file1'), num: 1 },
        { zone: Utils.getElement('dropZone2'), input: Utils.getElement('file2'), num: 2 }
    ];

    zones.forEach(({ zone, input, num }) => {
        if (!zone || !input) return;

        zone.addEventListener('click', () => input.click());

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
            if (file) handleFileSelect(file, num);
        });
    });
}

function setupFileInputs() {
    const file1Input = Utils.getElement('file1');
    const file2Input = Utils.getElement('file2');

    if (file1Input) {
        file1Input.addEventListener('change', (e) => {
            if (e.target.files[0]) handleFileSelect(e.target.files[0], 1);
        });
    }

    if (file2Input) {
        file2Input.addEventListener('change', (e) => {
            if (e.target.files[0]) handleFileSelect(e.target.files[0], 2);
        });
    }
}

function handleFileSelect(file, num) {
    if (!validateFile(file)) return;

    if (num === 1) {
        state.file1 = file;
        updateFileUI(1, file.name);
    } else {
        state.file2 = file;
        updateFileUI(2, file.name);
    }

    updateCompareButton();
}

function validateFile(file) {
    if (!CONFIG.ALLOWED_TYPES.includes(file.type)) {
        const isDocOrDocx = file.name.toLowerCase().match(/\.(doc|docx)$/);
        if (!(file.type === 'application/octet-stream' && isDocOrDocx)) {
            showToast('Invalid file type. Please upload PDF, DOC, DOCX, PNG, or JPG files.', 'error');
            return false;
        }
    }

    if (file.size > CONFIG.MAX_FILE_SIZE) {
        showToast(`File is too large. Maximum size is ${CONFIG.MAX_FILE_SIZE / (1024 * 1024)}MB.`, 'error');
        return false;
    }

    return true;
}

function updateFileUI(num, fileName) {
    const fileNameEl = Utils.getElement(`fileName${num}`);
    const dropContent = Utils.getElement(`dropContent${num}`);
    const preview = Utils.getElement(`preview${num}`);

    if (fileNameEl) fileNameEl.textContent = fileName;
    if (dropContent) dropContent.style.display = 'none';
    if (preview) preview.style.display = 'flex';
}

function removeFile(num) {
    if (num === 1) {
        state.file1 = null;
    } else {
        state.file2 = null;
    }

    const fileInput = Utils.getElement(`file${num}`);
    const dropContent = Utils.getElement(`dropContent${num}`);
    const preview = Utils.getElement(`preview${num}`);

    if (fileInput) fileInput.value = '';
    if (dropContent) dropContent.style.display = 'block';
    if (preview) preview.style.display = 'none';

    updateCompareButton();
}

function updateCompareButton() {
    const btn = Utils.getElement('compareBtn');
    if (btn) {
        btn.disabled = !(state.file1 && state.file2);
    }
}

// ============================================
// COMPARISON LOGIC
// ============================================
async function startComparison() {
    const loadingOverlay = Utils.getElement('loadingOverlay');
    const loadingText = Utils.getElement('loadingText');
    const progressFill = Utils.getElement('progressFill');

    if (loadingOverlay) loadingOverlay.style.display = 'flex';
    updateProgress(loadingText, progressFill, 'Uploading documents...', 10);

    try {
        const formData = new FormData();
        formData.append('file1', state.file1);
        formData.append('file2', state.file2);

        updateProgress(loadingText, progressFill, 'Extracting text with OCR...', 30);

        const response = await fetch(`${window.location.origin}/api/compare`, {
            method: 'POST',
            body: formData
        });

        const data = await handleResponse(response);

        // 🔒 CRITICAL: Log to verify data structure
        console.log('📦 API Response:', {
            hasReportId: !!data.report_id,
            hasDifferences: !!data.differences,
            reportId: data.report_id
        });

        // Set state IMMEDIATELY
        state.comparisonData = data;
        state.reportId = data.report_id;
        state.differences = data.differences || [];

        updateProgress(loadingText, progressFill, 'Processing with AI...', 70);

        // Verify it was set
        console.log('✅ State after setting:', {
            reportId: state.reportId,
            differencesCount: state.differences.length
        });

        updateProgress(loadingText, progressFill, 'Rendering results...', 90);

        state.sentences1 = extractSentencesFromResponse(data, 1);
        state.sentences2 = extractSentencesFromResponse(data, 2);

        updateProgress(loadingText, progressFill, 'Complete!', 100);

        setTimeout(() => {
            if (loadingOverlay) loadingOverlay.style.display = 'none';
            displayComparisonResults();
        }, 300);

    } catch (error) {
        console.error('Comparison error:', error);
        showToast(`Error: ${error.message || 'An unexpected error occurred'}`, 'error');
        if (loadingOverlay) loadingOverlay.style.display = 'none';
    }
}

async function handleResponse(response) {
    let data = null;

    try {
        const text = await response.text();
        data = JSON.parse(text);
    } catch (jsonError) {
        console.error('JSON parse error:', jsonError);
        throw new Error('Failed to parse server response. Please try again.');
    }

    if (!response.ok) {
        const errorMsg = data?.detail || data?.message || `Server error (${response.status})`;
        throw new Error(errorMsg);
    }

    if (!data.sentences1 || !data.sentences2) {
        throw new Error('Invalid response: missing sentence data');
    }

    return data;
}

function updateProgress(textEl, fillEl, text, percent) {
    if (textEl) textEl.textContent = text;
    if (fillEl) fillEl.style.width = `${percent}%`;
}

function extractSentencesFromResponse(data, docNum) {
    const sentences = docNum === 1 ? data.sentences1 : data.sentences2;

    // If identity match, return a placeholder sentence
    if ((!Array.isArray(sentences) || sentences.length === 0) && data.summary?.identity_check) {
        return [{
            id: 0,
            text: '[Document identical]',
            hasDiff: false,
            diffId: null
        }];
    }

    if (!Array.isArray(sentences) || sentences.length === 0) {
        console.warn(`No sentences found for document ${docNum}`);
        return [];
    }

    const enrichedSentences = sentences.map(sent => ({
        ...sent,
        hasDiff: false,
        diffId: null
    }));

    if (Array.isArray(data.differences)) {
        data.differences.forEach((diff, diffIdx) => {
            const pos = docNum === 1 ? diff.position1 : diff.position2;
            const idx = Utils.positionToIndex(pos);

            if (idx !== null && idx < enrichedSentences.length) {
                enrichedSentences[idx].hasDiff = true;
                enrichedSentences[idx].diffId = diffIdx;
            }
        });
    }

    return enrichedSentences;
}

function buildMatchMap(sentences, differences, docNum) {
    const map = {};

    sentences.forEach(sent => {
        map[sent.id] = 'exact';
        map[sent.id + '_diffId'] = null;
    });

    differences.forEach((diff, diffIdx) => {
        const pos = docNum === 1 ? diff.position1 : diff.position2;
        const idx = Utils.positionToIndex(pos);

        if (idx !== null && idx < sentences.length) {
            const sent = sentences[idx];
            map[sent.id] = 'diff';
            map[sent.id + '_diffId'] = diffIdx;
        }
    });

    return map;
}

function setupSentenceClickListeners() {
    ['doc1Content', 'doc2Content'].forEach(docId => {
        const container = Utils.getElement(docId);
        if (!container) return;

        container.addEventListener('click', (e) => {
            const span = e.target.closest('.sentence');
            if (!span) return;

            const diffId = span.dataset.diffId;
            if (diffId !== undefined && diffId !== '') {
                state.currentDiffIndex = Number(diffId);
                showDiffModal(state.currentDiffIndex);
                highlightDiff(state.currentDiffIndex);
            }
        });
    });
}

// ============================================
// 🔑 FIXED: SINGLE EXPORT SYSTEM
// ============================================
async function exportReport() {
    console.log('🚀 Export starting...');
    console.log('📊 Current state:', {
        reportId: state.reportId,
        hasComparisonData: !!state.comparisonData,
        differencesCount: state.differences.length,
        userDecisionsCount: Object.keys(state.userDecisions).length
    });

    // Validate report ID exists
    if (!state.reportId) {
        console.error('❌ No report ID - state:', state);
        showToast('Export failed: No report ID. Please re-run comparison.', 'error');
        return;
    }

    // Get format
    const formatSelector = document.querySelector('input[name="exportFormat"]:checked');
    const format = formatSelector ? formatSelector.value : 'pdf';

    console.log('📄 Export format:', format);

    const exportBtn = Utils.getElement('exportBtn');

    try {
        // Disable button
        if (exportBtn) {
            exportBtn.disabled = true;
            exportBtn.classList.add('loading');
            exportBtn.innerHTML = '<span>⏳</span> Generating...';
        }

        // Extract comments from userDecisions
        const userComments = {};
        const cleanDecisions = {};

        Object.entries(state.userDecisions).forEach(([idx, value]) => {
            if (typeof value === 'object') {
                if (value.note && value.note.trim()) {
                    userComments[idx] = value.note;
                }
                if (value.decision) {
                    cleanDecisions[idx] = value.decision;
                }
            } else if (typeof value === 'string') {
                cleanDecisions[idx] = value;
            }
        });

        console.log('💬 Extracted comments:', Object.keys(userComments).length);
        console.log('✅ Extracted decisions:', Object.keys(cleanDecisions).length);

        // Build payload
        const exportPayload = {
            user_comments: userComments,
            user_decisions: cleanDecisions,
            global_notes: state.globalNotes || '',
            summary: {
                total_differences: state.differences.length,
                reviewed: Object.keys(cleanDecisions).length,
                flagged: Object.values(cleanDecisions).filter(d => d === 'flag').length,
                accepted: Object.values(cleanDecisions).filter(d => d === 'accept').length
            }
        };

        console.log('📦 Export payload:', exportPayload.summary);

        // Create FormData
        const formData = new FormData();
        formData.append('format', format);
        formData.append('comparison_id', state.reportId);
        formData.append('export_data', JSON.stringify(exportPayload));

        console.log('🌐 Sending request to /api/export-report...');

        // Send request
        const response = await fetch('/api/export-report', {
            method: 'POST',
            body: formData
        });

        console.log('📡 Response status:', response.status);

        if (!response.ok) {
            const errorText = await response.text();
            console.error('❌ Server error:', errorText);

            let errorMsg = 'Export failed';
            try {
                const errorJson = JSON.parse(errorText);
                errorMsg = errorJson.error || errorJson.detail || errorMsg;
            } catch (e) {
                errorMsg = errorText.substring(0, 100);
            }

            throw new Error(errorMsg);
        }

        // Download file
        const blob = await response.blob();
        console.log('📥 Received blob:', blob.size, 'bytes');

        if (blob.size === 0) {
            throw new Error('Server returned empty file');
        }

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `comparison_report_${state.reportId}.${format === 'pdf' ? 'pdf' : 'docx'}`;
        document.body.appendChild(a);
        a.click();

        // Cleanup
        setTimeout(() => {
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        }, 100);

        console.log('✅ Export successful!');
        showToast(`${format.toUpperCase()} report downloaded!`, 'success');

    } catch (error) {
        console.error('❌ Export failed:', error);
        showToast(`Export failed: ${error.message}`, 'error');
    } finally {
        // Re-enable button
        if (exportBtn) {
            exportBtn.disabled = false;
            exportBtn.classList.remove('loading');
            exportBtn.innerHTML = '<span>📄</span> Generate & Download';
        }
    }
}

function displayComparisonResults() {
    const resultContainer = document.getElementById('comparisonResults');

    // Clear previous results before showing new ones
    resultContainer.innerHTML = '';

    const data = state.comparisonData; // ✅ pull comparison data first

    // =====================================================
    // 🆕 HANDLE IDENTITY MATCH
    // =====================================================
    if (data.summary?.identity_check || data.summary?.exact_match) {
        // Show identity match banner
        const banner = document.createElement('div');
        banner.className = 'identity-banner';
        banner.textContent = '✅ Exact Match Detected\nDocuments are textually identical after normalization. No differences found.';
        resultContainer.appendChild(banner);

        // Hide upload, show comparison section
        const uploadSection = Utils.getElement("uploadSection");
        const comparisonSection = Utils.getElement("comparisonSection");
        if (uploadSection) uploadSection.style.display = "none";
        if (comparisonSection) comparisonSection.style.display = "block";

        // ✅ Override document name headers to avoid misleading filenames
        const docName1Elem = Utils.getElement('docName1');
        const docName2Elem = Utils.getElement('docName2');
        if (docName1Elem) docName1Elem.textContent = '[Comparison skipped]';
        if (docName2Elem) docName2Elem.textContent = '[Comparison skipped]';

        // Update summary stats
        updateElement('overallMatch', '100%');
        updateElement('totalDiffs', '0');
        updateElement('highPriority', '0');
        updateElement('commentsCount', '0');

        // Hide diff navigation
        const diffNav = Utils.getElement('diff-navigation');
        if (diffNav) diffNav.style.display = 'none';

        // Show simple success message in document panels
        const doc1Content = Utils.getElement('doc1Content');
        const doc2Content = Utils.getElement('doc2Content');
        const identicalHtml = `
            <div style="text-align: center; padding: 40px; color: #27ae60;">
                <h2 style="font-size: 2rem; margin-bottom: 20px;">✅</h2>
                <h3>Documents are Identical</h3>
                <p style="color: #666; margin-top: 15px;">
                    After normalization, these documents contain exactly the same text.
                </p>
            </div>
        `;
        if (doc1Content) doc1Content.innerHTML = identicalHtml;
        if (doc2Content) doc2Content.innerHTML = identicalHtml;

        showToast('Documents are identical! ✅', 'success');
        return; // Stop here - no need to render diffs
    }

    // =====================================================
    // 📊 NORMAL FLOW (Documents differ)
    // =====================================================
    const uploadSection = Utils.getElement("uploadSection");
    const comparisonSection = Utils.getElement("comparisonSection");
    if (uploadSection) uploadSection.style.display = "none";
    if (comparisonSection) comparisonSection.style.display = "block";

    updateElement('docName1', state.file1.name);
    updateElement('docName2', state.file2.name);

    updateElement('overallMatch', `${data.summary.overall_match}%`);
    updateElement('totalDiffs', data.summary.significant_differences || 0);
    updateElement('highPriority', data.differences?.filter(d => d.severity === 'high').length || 0);
    updateCommentsCount();
    updateElement('strategyUsed', 'ADAPTIVE');

    state.differences = data.differences || [];

    const matchMap1 = buildMatchMap(state.sentences1, state.differences, 1);
    const matchMap2 = buildMatchMap(state.sentences2, state.differences, 2);

    const reconstructor = new AdaptiveReconstructor();
    const result1 = reconstructor.reconstruct(state.sentences1, matchMap1);
    const result2 = reconstructor.reconstruct(state.sentences2, matchMap2);

    const doc1Content = Utils.getElement('doc1Content');
    const doc2Content = Utils.getElement('doc2Content');
    if (doc1Content) doc1Content.innerHTML = result1.html;
    if (doc2Content) doc2Content.innerHTML = result2.html;

    setupSentenceClickListeners();
    setupDifferenceNavigation();
    setupScrollSync();

    showToast('Comparison complete!', 'success');
}

// 🆕 Helper function for identity banner
function showIdentityMatchBanner() {
    const summaryBar = document.querySelector('.summary-bar');
    if (!summaryBar) return;

    // Insert banner before summary
    const banner = document.createElement('div');
    banner.className = 'identity-match-banner';
    banner.innerHTML = `
        <div style="background: linear-gradient(135deg, #27ae60 0%, #229954 100%);
                    color: white; padding: 20px 30px; text-align: center;">
            <h2 style="margin: 0 0 10px 0; font-size: 1.5rem;">
                ✅ Exact Match Detected
            </h2>
            <p style="margin: 0; opacity: 0.95; font-size: 1.1rem;">
                Documents are textually identical after normalization.
                No differences found.
            </p>
        </div>
    `;

    summaryBar.parentNode.insertBefore(banner, summaryBar);
}

// 🔒 NEW FUNCTION - Add this after displayComparisonResults()
function updateCommentsCount() {
    let commentCount = 0;

    Object.values(state.userDecisions).forEach(value => {
        if (typeof value === 'object' && value.note && value.note.trim()) {
            commentCount++;
        }
    });

    updateElement('commentsCount', commentCount);
    console.log('📝 Comments count updated:', commentCount);
}

function setupDifferenceNavigation() {
    const diffCounter = Utils.getElement('diffCounter');

    if (state.differences.length > 0) {
        state.currentDiffIndex = 0;

        const nextDiffBtn = Utils.getElement('nextDiffBtn');
        const prevDiffBtn = Utils.getElement('prevDiffBtn');

        if (nextDiffBtn) nextDiffBtn.disabled = state.differences.length <= 1;
        if (prevDiffBtn) prevDiffBtn.disabled = true;

        if (diffCounter) {
            diffCounter.textContent = `1 / ${state.differences.length}`;
        }

        highlightDiff(0);
    } else {
        if (diffCounter) diffCounter.textContent = '0 / 0';
    }
}

function updateElement(id, content) {
    const el = Utils.getElement(id);
    if (el) {
        el.textContent = typeof content === 'string' ? content : String(content);
    }
}

// ============================================
// NAVIGATION
// ============================================
function navigateDiff(direction) {
    if (state.differences.length === 0) return;

    const newIndex = Math.max(
        0,
        Math.min(state.currentDiffIndex + direction, state.differences.length - 1)
    );

    if (newIndex === state.currentDiffIndex) return;

    state.currentDiffIndex = newIndex;
    highlightDiff(newIndex);
    updateNavigationButtons();
    updateDiffCounter();
}

function updateNavigationButtons() {
    const prevBtn = Utils.getElement('prevDiffBtn');
    const nextBtn = Utils.getElement('nextDiffBtn');

    if (prevBtn) prevBtn.disabled = state.currentDiffIndex === 0;
    if (nextBtn) nextBtn.disabled = state.currentDiffIndex === state.differences.length - 1;
}

function updateDiffCounter() {
    const counter = Utils.getElement('diffCounter');
    if (counter && state.differences.length > 0) {
        counter.textContent = `${state.currentDiffIndex + 1} / ${state.differences.length}`;
    }
}

function highlightDiff(index) {
    if (index < 0 || index >= state.differences.length) return;

    const diff = state.differences[index];

    document.querySelectorAll('.sentence.active').forEach(el => {
        el.classList.remove('active');
    });

    const doc1Sentences = getSentenceElements('doc1');
    const doc2Sentences = getSentenceElements('doc2');

    highlightAndScrollToSentence(doc1Sentences, diff.position1);
    highlightAndScrollToSentence(doc2Sentences, diff.position2);
}

function getSentenceElements(docKey) {
    if (!state.sentenceCache[docKey]) {
        const contentEl = Utils.getElement(`${docKey}Content`);
        state.sentenceCache[docKey] = contentEl ?
            Array.from(contentEl.querySelectorAll('.sentence')) : [];
    }
    return state.sentenceCache[docKey];
}

function highlightAndScrollToSentence(sentenceElements, position) {
    const idx = Utils.positionToIndex(position);
    if (idx !== null && idx < sentenceElements.length) {
        const element = sentenceElements[idx];
        element.classList.add('active');
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

// ============================================
// MODAL
// ============================================
function setupModalAccessibility() {
    const modal = Utils.getElement('modalOverlay');
    if (!modal) return;

    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-labelledby', 'modalTitle');

    modal.addEventListener('keydown', trapFocus);
}

function trapFocus(e) {
    const modal = Utils.getElement('modalOverlay');
    if (!modal || modal.style.display !== 'flex') return;

    const focusableElements = modal.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    if (e.key === 'Tab') {
        if (e.shiftKey && document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
        } else if (!e.shiftKey && document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
        }
    }
}

function showDiffModal(index) {
    if (index < 0 || index >= state.differences.length) return;

    const diff = state.differences[index];
    const modal = Utils.getElement('modalOverlay');
    if (!modal) return;

    updateElement('modalTitle', `Difference #${index + 1} - ${formatDiffType(diff.classification)}`);
    updateElement('diffType', formatDiffType(diff.classification));

    const severitySpan = Utils.getElement('diffSeverity');
    if (severitySpan) {
        severitySpan.textContent = diff.severity.toUpperCase();
        severitySpan.className = `severity-badge severity-${diff.severity}`;
    }

    updateElement('diffSimilarity', `${(diff.similarity * 100).toFixed(1)}%`);
    updateElement('diffPosition', `Doc1: ${diff.position1 || 'N/A'}, Doc2: ${diff.position2 || 'N/A'}`);

    const diffText1 = Utils.getElement('diffText1');
    const diffText2 = Utils.getElement('diffText2');
    if (diffText1) diffText1.innerHTML = diff.diff_html1 || Utils.escapeHtml(diff.sentence1 || 'N/A');
    if (diffText2) diffText2.innerHTML = diff.diff_html2 || Utils.escapeHtml(diff.sentence2 || 'N/A');

    const suggestionsDiv = Utils.getElement('aiSuggestions');
    if (suggestionsDiv) {
        if (Array.isArray(diff.suggestions) && diff.suggestions.length > 0) {
            const items = diff.suggestions.map(s =>
                `<li>${Utils.escapeHtml(s)}</li>`
            ).join('');
            suggestionsDiv.innerHTML = `<ul>${items}</ul>`;
        } else {
            suggestionsDiv.innerHTML = '<p>No specific suggestions available.</p>';
        }
    }

    const recommendation = generateRecommendation(diff);
    updateElement('recommendationText', recommendation);

    modal.style.display = 'flex';
    const firstButton = modal.querySelector('button');
    if (firstButton) setTimeout(() => firstButton.focus(), 100);
}

function closeModal(event) {
    const modalOverlay = Utils.getElement('modalOverlay');
    if (!modalOverlay) return;

    if (!event || event.target === modalOverlay || event.type === 'keydown') {
        modalOverlay.style.display = 'none';

        const doc1Content = Utils.getElement('doc1Content');
        if (doc1Content) doc1Content.focus();
    }
}

// ============================================
// COMMENT MODAL FUNCTIONS
// ============================================

function openCommentModal() {
    if (state.currentDiffIndex < 0 || state.currentDiffIndex >= state.differences.length) {
        showToast('Please select a difference first', 'warning');
        return;
    }

    const modal = Utils.getElement('commentModal');
    const input = Utils.getElement('commentInput');
    const diffNumber = Utils.getElement('commentDiffNumber');
    const diffSummary = Utils.getElement('commentDiffSummary');

    if (!modal || !input) {
        console.error('Comment modal elements not found');
        return;
    }

    const idx = state.currentDiffIndex;
    const diff = state.differences[idx];

    // Load existing comment from userComments (not userDecisions)
    const existingComment =
      state.userDecisions[idx]?.note || "";

    // Populate modal
    if (diffNumber) diffNumber.textContent = idx + 1;
    if (diffSummary) {
        const type = formatDiffType(diff.classification);
        const severity = diff.severity.toUpperCase();
        diffSummary.textContent = `${type} (${severity})`;
    }

    // Load existing comment
    input.value = existingComment;

    // Show modal and focus input
    modal.style.display = 'flex';
    setTimeout(() => {
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length);
    }, 100);
}

// Add flag at top of file (near state declaration)
let isSavingComment = false;

function saveComment() {
    // Prevent multiple simultaneous calls
    if (isSavingComment) {
        console.log('🚫 Already saving comment, ignoring duplicate call');
        return;
    }

    isSavingComment = true;

    const input = Utils.getElement('commentInput');
    if (!input) {
        isSavingComment = false;
        return;
    }

    const idx = state.currentDiffIndex;
    const text = input.value.trim();

    // Ensure object structure
    if (!state.userDecisions[idx] || typeof state.userDecisions[idx] === 'string') {
        state.userDecisions[idx] = {
            decision: state.userDecisions[idx] || null,
            note: ""
        };
    }

    // Save comment
    state.userDecisions[idx].note = text;

    // Update visual indicators
    if (text) {
        const doc1Sentences = getSentenceElements('doc1');
        const doc2Sentences = getSentenceElements('doc2');
        const diff = state.differences[idx];

        const idx1 = Utils.positionToIndex(diff.position1);
        const idx2 = Utils.positionToIndex(diff.position2);

        if (idx1 !== null && idx1 < doc1Sentences.length) {
            doc1Sentences[idx1].classList.add('has-comment');
        }
        if (idx2 !== null && idx2 < doc2Sentences.length) {
            doc2Sentences[idx2].classList.add('has-comment');
        }
    }

    // Update count
    updateCommentsCount();

    // Close modal
    closeCommentModal();

    // Show toast ONCE after everything settles
    setTimeout(() => {
        showToast(text ? 'Comment saved' : 'Comment removed',
                  text ? 'success' : 'info');
        isSavingComment = false; // Reset flag
    }, 100);
}

function closeCommentModal(event) {
    const modal = Utils.getElement('commentModal');
    if (!modal) return;

    if (!event || event.target === modal || event.type === 'keydown') {
        modal.style.display = 'none';
    }
}

// Add keyboard shortcut for comments (Ctrl+M)
document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'm') {
        e.preventDefault();
        openCommentModal();
    }
});

function showGlobalNotesModal() {
    const modal = Utils.getElement('notesModal');
    const textarea = Utils.getElement('globalNotesTextarea');

    if (!modal) {
        console.error('❌ Global notes modal not found');
        return;
    }
    if (!textarea) {
        console.error('❌ Global notes textarea not found');
        return;
    }

    // Load existing notes
    textarea.value = state.globalNotes || '';

    modal.style.display = 'flex';
    setTimeout(() => {
        textarea.focus();
        textarea.setSelectionRange(textarea.value.length, textarea.value.length);
    }, 100);

    console.log('✅ Global notes modal opened');
}

// Add flag at top of file (near state declaration)
let isSavingGlobalNotes = false;

function saveGlobalNotes() {
    // Prevent multiple simultaneous calls
    if (isSavingGlobalNotes) {
        console.log('🚫 Already saving global notes, ignoring duplicate call');
        return;
    }

    isSavingGlobalNotes = true;

    const textarea = Utils.getElement('globalNotesTextarea');
    if (!textarea) {
        isSavingGlobalNotes = false;
        return;
    }

    state.globalNotes = textarea.value.trim();

    closeNotesModal();

    setTimeout(() => {
        showToast('Document notes saved successfully', 'success');
        isSavingGlobalNotes = false; // Reset flag
    }, 100);

    console.log('✅ Global notes saved:', state.globalNotes.substring(0, 50) + '...');
}

function closeNotesModal(event) {
    const modal = Utils.getElement('notesModal');
    if (!modal) return;

    // Close if clicking overlay or pressing Escape
    if (!event || event.target === modal || event.type === 'keydown') {
        modal.style.display = 'none';
        console.log('✅ Global notes modal closed');
    }
}
/* =========================
   MODAL NAVIGATION (FIXED)
========================= */
function navigateDiffInModal(direction) {
    const newIndex = state.currentDiffIndex + direction;
    if (newIndex < 0 || newIndex >= state.differences.length) return;

    state.currentDiffIndex = newIndex;
    updateNavigationButtons();
    updateDiffCounter();
    showDiffModal(newIndex);
    highlightDiff(newIndex);
}

function markDiff(action) {
    if (state.currentDiffIndex < 0 || state.currentDiffIndex >= state.differences.length) return;

    const idx = state.currentDiffIndex;
    const diff = state.differences[idx];

    // FIXED: Always use object structure
    if (!state.userDecisions[idx] || typeof state.userDecisions[idx] === 'string') {
        state.userDecisions[idx] = {
            decision: action,
            note: state.userDecisions[idx]?.note || ""  // Preserve existing note
        };
    } else {
        state.userDecisions[idx].decision = action;
    }

    // Apply visual feedback
    applyDiffMarking(diff, action);

    showToast(
        `Difference ${action === 'accept' ? 'accepted' : action === 'flag' ? 'flagged' : 'skipped'}`,
        'success'
    );

    // Auto-advance to next diff
    if (state.currentDiffIndex < state.differences.length - 1) {
        setTimeout(() => {
            navigateDiffInModal(1);
        }, CONFIG.AUTO_ADVANCE_DELAY);
    } else {
        closeModal();
    }
}

function applyDiffMarking(diff, action) {
    const cssClass = action === 'accept' ? 'user-accepted' :
                    action === 'flag' ? 'user-flagged' : '';

    if (!cssClass) return;

    const doc1Sentences = getSentenceElements('doc1');
    const doc2Sentences = getSentenceElements('doc2');

    const idx1 = Utils.positionToIndex(diff.position1);
    const idx2 = Utils.positionToIndex(diff.position2);

    if (idx1 !== null && idx1 < doc1Sentences.length) {
        doc1Sentences[idx1].classList.add(cssClass);
    }

    if (idx2 !== null && idx2 < doc2Sentences.length) {
        doc2Sentences[idx2].classList.add(cssClass);
    }
}

// ============================================
// UTILITIES
// ============================================
function formatDiffType(classification) {
    if (!classification) return 'Unknown';
    return classification.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function generateRecommendation(diff) {
    if (diff.severity === 'low' && diff.similarity > 0.9) {
        return 'Minor difference. Consider accepting if content meaning is preserved.';
    } else if (diff.severity === 'high') {
        return 'Significant difference detected. Manual review strongly recommended.';
    } else if (diff.classification?.includes('ocr')) {
        return 'Likely OCR error. Verify against original document if critical.';
    } else {
        return 'Review this difference and decide based on document context.';
    }
}

function setupScrollSync() {
    const doc1Content = Utils.getElement('doc1Content');
    const doc2Content = Utils.getElement('doc2Content');

    if (!doc1Content || !doc2Content) return;

    let isSyncing = false;

    const syncScroll = Utils.debounce((source, target) => {
        if (isSyncing) return;
        isSyncing = true;
        target.scrollTop = source.scrollTop;
        setTimeout(() => { isSyncing = false; }, CONFIG.SCROLL_DEBOUNCE);
    }, 10);

    doc1Content.addEventListener('scroll', () => syncScroll(doc1Content, doc2Content));
    doc2Content.addEventListener('scroll', () => syncScroll(doc2Content, doc1Content));
}

// REPLACE the entire function with:
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        const comparisonSection = Utils.getElement('comparisonSection');
        const modalOverlay = Utils.getElement('modalOverlay');
        const commentModal = Utils.getElement('commentModal');
        const notesModal = Utils.getElement('notesModal');

        // 🔒 FIX: Check if user is typing in an input field
        const isTyping = (
            e.target.tagName === 'TEXTAREA' ||
            e.target.tagName === 'INPUT' ||
            e.target.contentEditable === 'true'
        );

        if (!comparisonSection || comparisonSection.style.display === 'none') return;

        const diffModalOpen = modalOverlay && modalOverlay.style.display === 'flex';
        const commentModalOpen = commentModal && commentModal.style.display === 'flex';
        const notesModalOpen = notesModal && notesModal.style.display === 'flex';

        // Escape always works (even when typing)
        if (e.key === 'Escape') {
            e.preventDefault();
            if (commentModalOpen) closeCommentModal();
            else if (notesModalOpen) closeNotesModal();
            else closeModal();
            return;
        }

        // 🔒 FIX: Don't trigger shortcuts when typing
        if (isTyping) {
            console.log('🚫 Shortcut blocked - user is typing');
            return;
        }

        // Navigation shortcuts (not in any modal)
        if (!diffModalOpen && !commentModalOpen && !notesModalOpen) {
            if (e.key === 'ArrowRight' || e.key === 'j') {
                e.preventDefault();
                navigateDiff(1);
            } else if (e.key === 'ArrowLeft' || e.key === 'k') {
                e.preventDefault();
                navigateDiff(-1);
            }
        }

        // 🔒 FIX: Only trigger shortcuts in diff modal (NOT comment modal)
        if (diffModalOpen && !commentModalOpen && !notesModalOpen) {
            if (e.key === 'Enter') {
                e.preventDefault();
                markDiff('accept');
            } else if (e.key === 'f' || (e.shiftKey && e.key === 'Enter')) {
                e.preventDefault();
                markDiff('flag');
            } else if (e.key === 's') {
                e.preventDefault();
                markDiff('skip');
            }
        }
    });
}

function showToast(message, type = 'info') {
    const container = Utils.getElement('toastContainer');
    if (!container) return;

    const existingToasts = container.querySelectorAll('.toast');
    if (existingToasts.length >= CONFIG.MAX_TOASTS) {
        existingToasts[0].remove();
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icon = type === 'success' ? '✓' : type === 'error' ? '✗' : 'ℹ';
    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span class="toast-message">${Utils.escapeHtml(message)}</span>
    `;

    container.appendChild(toast);
    state.toastQueue.push(toast);

    setTimeout(() => toast.classList.add('show'), 10);

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            toast.remove();
            const idx = state.toastQueue.indexOf(toast);
            if (idx > -1) state.toastQueue.splice(idx, 1);
        }, 300);
    }, CONFIG.TOAST_DURATION);
}

function resetUploadForm() {
    state.file1 = null;
    state.file2 = null;

    for (let i = 1; i <= 2; i++) {
        const fileInput = Utils.getElement(`file${i}`);
        const dropContent = Utils.getElement(`dropContent${i}`);
        const preview = Utils.getElement(`preview${i}`);

        if (fileInput) fileInput.value = '';
        if (dropContent) dropContent.style.display = 'block';
        if (preview) preview.style.display = 'none';
    }

    updateCompareButton();
}

function backToUpload() {
    const comparisonSection = Utils.getElement("comparisonSection");
    const uploadSection = Utils.getElement("uploadSection");

    if (comparisonSection) comparisonSection.style.display = "none";
    if (uploadSection) uploadSection.style.display = "block";

    resetUploadForm();

    // Reset state
    state.comparisonData = null;
    state.reportId = null;
    state.differences = [];
    state.currentDiffIndex = -1;
    state.userDecisions = {};
    state.userComments = {};
    state.globalNotes = "";
    state.sentences1 = [];
    state.sentences2 = [];
    state.sentenceCache.doc1 = null;
    state.sentenceCache.doc2 = null;
}

/* =========================
   PUBLIC API
========================= */
LDC.initialize = initialize;
LDC.removeFile = removeFile;
LDC.startComparison = startComparison;
LDC.closeModal = closeModal;
LDC.navigateDiff = navigateDiff;
LDC.navigateDiffInModal = navigateDiffInModal;
LDC.markDiff = markDiff;
LDC.backToUpload = backToUpload;
LDC.exportReport = exportReport;
LDC.openCommentModal = openCommentModal;
LDC.saveComment = saveComment;
LDC.closeCommentModal = closeCommentModal;
LDC.showGlobalNotesModal = showGlobalNotesModal;
LDC.saveGlobalNotes = saveGlobalNotes;
LDC.closeNotesModal = closeNotesModal;

/* =========================
   AUTO INIT
========================= */
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
} else {
    initialize();
}

})(window.LDC);

/* =========================
   LEGACY GLOBAL EXPOSURE
========================= */
window.removeFile = n => window.LDC.removeFile(n);
window.startComparison = () => window.LDC.startComparison();
window.closeModal = e => window.LDC.closeModal(e);
window.navigateDiff = d => window.LDC.navigateDiff(d);
window.navigateDiffInModal = d => window.LDC.navigateDiffInModal(d);
window.markDiff = a => window.LDC.markDiff(a);
window.backToUpload = () => window.LDC.backToUpload();
window.exportReport = () => window.LDC.exportReport(); // ✅ safe
window.openCommentModal = () => window.LDC.openCommentModal(); // ✅ safe
window.saveComment = () => window.LDC.saveComment(); // ✅ safe
window.closeCommentModal = e => window.LDC.closeCommentModal(e); // ✅ safe
window.showGlobalNotesModal = () => window.LDC.showGlobalNotesModal(); // ✅ safe
window.saveGlobalNotes = () => window.LDC.saveGlobalNotes(); // ✅ safe
window.closeNotesModal = e => window.LDC.closeNotesModal(e); // ✅ safe
