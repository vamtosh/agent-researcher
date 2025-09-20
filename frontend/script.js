// TCS Competitive Intelligence - Frontend JavaScript

const API_BASE_URL = 'http://localhost:8000';
let currentSessionId = null;
let progressInterval = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    loadCompetitors();
    loadCacheInfo();
    resetInterface();
});

// Load available competitors from API
async function loadCompetitors() {
    try {
        const response = await fetch(`${API_BASE_URL}/competitors`);
        const competitors = await response.json();

        const competitorsGrid = document.getElementById('competitorsGrid');
        competitorsGrid.innerHTML = '';

        competitors.forEach(competitor => {
            const card = document.createElement('div');
            card.className = 'competitor-card';
            card.onclick = () => toggleCompetitor(card, competitor);

            card.innerHTML = `
                <input type="checkbox" id="competitor-${competitor}" value="${competitor}" checked>
                <label for="competitor-${competitor}">${competitor}</label>
            `;

            competitorsGrid.appendChild(card);
        });

        // Mark all as selected initially
        document.querySelectorAll('.competitor-card').forEach(card => {
            card.classList.add('selected');
        });

    } catch (error) {
        console.error('Failed to load competitors:', error);
        showError('Failed to load competitors list');
    }
}

// Toggle competitor selection
function toggleCompetitor(card, competitor) {
    const checkbox = card.querySelector('input[type="checkbox"]');
    checkbox.checked = !checkbox.checked;
    card.classList.toggle('selected', checkbox.checked);
}

// Start research workflow
async function startResearch() {
    const selectedCompetitors = getSelectedCompetitors();
    const researchFocus = document.getElementById('researchFocus').value;
    const maxAge = parseInt(document.getElementById('maxAge').value);
    const minSources = parseInt(document.getElementById('minSources').value);

    // Validation
    if (selectedCompetitors.length === 0) {
        alert('Please select at least one competitor');
        return;
    }

    if (!researchFocus.trim()) {
        alert('Please enter a research focus');
        return;
    }

    try {
        // Show loading state
        const startBtn = document.getElementById('startResearchBtn');
        startBtn.innerHTML = '<span class="spinner"></span>Starting...';
        startBtn.disabled = true;

        // Prepare request
        const requestBody = {
            competitors: selectedCompetitors,
            research_focus: researchFocus,
            max_age_days: maxAge,
            min_sources_per_competitor: minSources
        };

        // Start research
        const response = await fetch(`${API_BASE_URL}/research/start`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        currentSessionId = result.session_id;

        // Show progress panel
        showProgressPanel();
        document.getElementById('sessionId').textContent = currentSessionId;
        document.getElementById('sessionStatus').textContent = result.status;

        // Start progress monitoring
        startProgressMonitoring();

    } catch (error) {
        console.error('Failed to start research:', error);
        showError(`Failed to start research: ${error.message}`);

        // Reset button
        const startBtn = document.getElementById('startResearchBtn');
        startBtn.innerHTML = 'Start Research';
        startBtn.disabled = false;
    }
}

// Get selected competitors
function getSelectedCompetitors() {
    const checkboxes = document.querySelectorAll('#competitorsGrid input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(cb => cb.value);
}

// Show progress panel
function showProgressPanel() {
    document.getElementById('researchPanel').style.display = 'none';
    document.getElementById('progressPanel').style.display = 'block';
    document.getElementById('resultsPanel').style.display = 'none';
    document.getElementById('errorPanel').style.display = 'none';
}

// Start progress monitoring
function startProgressMonitoring() {
    if (progressInterval) {
        clearInterval(progressInterval);
    }

    progressInterval = setInterval(async () => {
        try {
            await updateProgress();
        } catch (error) {
            console.error('Progress monitoring error:', error);
            clearInterval(progressInterval);
            showError('Progress monitoring failed');
        }
    }, 1500); // Poll every 1.5 seconds for more responsive updates
}

// Update progress display
async function updateProgress() {
    if (!currentSessionId) return;

    try {
        const response = await fetch(`${API_BASE_URL}/research/${currentSessionId}/status`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const status = await response.json();

        // Update session status
        document.getElementById('sessionStatus').textContent = status.status;

        // Update agent progress
        if (status.agents_state) {
            updateAgentProgress('deepResearch', status.agents_state.deep_research);
            updateAgentProgress('synthesizer', status.agents_state.synthesizer);
        }

        // Update messages
        if (status.messages) {
            updateProgressMessages(status.messages);
        }

        // Check for completion or failure
        if (status.status === 'completed') {
            clearInterval(progressInterval);
            await loadExecutiveReport();
        } else if (status.status === 'failed') {
            clearInterval(progressInterval);
            const errorMsg = status.error_messages ? status.error_messages.join('; ') : 'Research workflow failed';
            showError(errorMsg);
        }

    } catch (error) {
        console.error('Failed to update progress:', error);
    }
}


// Update progress messages
function updateProgressMessages(messages) {
    const container = document.getElementById('progressMessages');
    container.innerHTML = '';

    messages.slice(-10).forEach(message => { // Show last 10 messages
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message';
        messageDiv.textContent = `[${message.role}] ${message.content}`;
        container.appendChild(messageDiv);
    });

    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
}

// Load and display executive report
async function loadExecutiveReport() {
    try {
        const response = await fetch(`${API_BASE_URL}/research/${currentSessionId}/report`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const report = await response.json();
        displayExecutiveReport(report);

    } catch (error) {
        console.error('Failed to load executive report:', error);
        showError('Failed to load executive report');
    }
}

// Display executive report
function displayExecutiveReport(report) {
    // Show results panel
    document.getElementById('progressPanel').style.display = 'none';
    document.getElementById('resultsPanel').style.display = 'block';

    // Report metadata
    document.getElementById('reportDate').textContent = new Date(report.generation_timestamp).toLocaleString();
    document.getElementById('sourcesCount').textContent = report.data_sources_count;

    // Executive summary
    document.getElementById('executiveSummary').textContent = report.executive_summary;

    // Key insights
    displayInsights(report.key_insights);

    // Market opportunities
    displayOpportunities(report.market_opportunities);

    // Strategic recommendations
    displayRecommendations(report.strategic_recommendations);

    // Competitor analysis
    displayCompetitorAnalysis(report.competitor_analysis);
}

// Display insights
function displayInsights(insights) {
    const grid = document.getElementById('insightsGrid');
    grid.innerHTML = '';

    insights.forEach(insight => {
        const card = document.createElement('div');
        card.className = `insight-card ${insight.priority}-priority`;

        card.innerHTML = `
            <div class="insight-title">${insight.title}</div>
            <div class="insight-description">${insight.description}</div>
            <div class="insight-impact"><strong>Impact:</strong> ${insight.business_impact}</div>
            <div class="insight-action"><strong>Action:</strong> ${insight.recommended_action}</div>
            <div class="insight-tags">
                <span class="insight-priority ${insight.priority}">${insight.priority}</span>
                <span class="insight-timeline">${insight.timeline}</span>
            </div>
        `;

        grid.appendChild(card);
    });
}

// Display opportunities
function displayOpportunities(opportunities) {
    const list = document.getElementById('opportunitiesList');
    list.innerHTML = '';

    opportunities.forEach(opportunity => {
        const li = document.createElement('li');
        li.textContent = opportunity;
        list.appendChild(li);
    });
}

// Display recommendations
function displayRecommendations(recommendations) {
    const list = document.getElementById('recommendationsList');
    list.innerHTML = '';

    recommendations.forEach(recommendation => {
        const li = document.createElement('li');
        li.textContent = recommendation;
        list.appendChild(li);
    });
}

// Display competitor analysis
function displayCompetitorAnalysis(competitorData) {
    const table = document.getElementById('competitorsTable');
    table.innerHTML = '';

    competitorData.forEach(data => {
        const row = document.createElement('div');
        row.className = 'competitor-row';

        const initiatives = data.key_initiatives.map(initiative =>
            `<span class="initiative-tag">${initiative}</span>`
        ).join('');

        row.innerHTML = `
            <div class="competitor-name">${data.competitor}</div>
            <div class="competitor-narrative">${data.ai_narrative}</div>
            <div class="competitor-initiatives">${initiatives}</div>
            <div class="competitor-meta">
                <small>Sources: ${data.sources.length} | Confidence: ${(data.confidence_score * 100).toFixed(0)}%</small>
            </div>
        `;

        table.appendChild(row);
    });
}

// Export report
async function exportReport(format) {
    if (!currentSessionId) {
        alert('No report available for export');
        return;
    }

    try {
        if (format === 'json') {
            // Export as JSON
            const response = await fetch(`${API_BASE_URL}/research/${currentSessionId}/report`);
            const report = await response.json();

            const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `tcs-competitive-intelligence-${currentSessionId}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

        } else if (format === 'pdf') {
            // For PDF export, we would integrate with a PDF library
            // For now, show a placeholder message
            alert('PDF export feature coming soon. Please use JSON export for now.');
        }

    } catch (error) {
        console.error('Export failed:', error);
        alert('Export failed. Please try again.');
    }
}

// Show error
function showError(message) {
    document.getElementById('researchPanel').style.display = 'none';
    document.getElementById('progressPanel').style.display = 'none';
    document.getElementById('resultsPanel').style.display = 'none';
    document.getElementById('errorPanel').style.display = 'block';
    document.getElementById('errorMessage').textContent = message;

    // Clear progress monitoring
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
}

// Reset interface
function resetInterface() {
    // Clear session
    currentSessionId = null;

    // Clear progress monitoring
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }

    // Show research panel
    document.getElementById('researchPanel').style.display = 'block';
    document.getElementById('progressPanel').style.display = 'none';
    document.getElementById('resultsPanel').style.display = 'none';
    document.getElementById('errorPanel').style.display = 'none';

    // Reset button
    const startBtn = document.getElementById('startResearchBtn');
    startBtn.innerHTML = 'Start Research';
    startBtn.disabled = false;

    // Clear progress bars
    document.getElementById('deepResearchProgress').style.width = '0%';
    document.getElementById('synthesizerProgress').style.width = '0%';
    document.getElementById('deepResearchTask').textContent = 'Initializing...';
    document.getElementById('synthesizerTask').textContent = 'Waiting...';
}

// Health check
async function checkAPIHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        return response.ok;
    } catch (error) {
        return false;
    }
}

// Cache Management Functions
async function loadCacheInfo() {
    try {
        const response = await fetch(`${API_BASE_URL}/cache/info`);
        const cacheInfo = await response.json();

        displayCacheInfo(cacheInfo);
    } catch (error) {
        console.error('Failed to load cache info:', error);
        document.getElementById('cacheInfo').innerHTML = '<p>Failed to load cache information</p>';
    }
}

function displayCacheInfo(cacheInfo) {
    const container = document.getElementById('cacheInfo');

    if (cacheInfo.total_cached === 0) {
        container.innerHTML = '<p>No cached research data</p>';
        return;
    }

    let html = `
        <div class="cache-summary">
            <strong>Cache Summary:</strong> ${cacheInfo.total_cached} entries
            ${cacheInfo.expired_count > 0 ? `(${cacheInfo.expired_count} expired)` : ''}
        </div>
    `;

    if (cacheInfo.cache_entries.length > 0) {
        html += '<div class="cache-entries">';

        cacheInfo.cache_entries.slice(0, 5).forEach(entry => { // Show latest 5
            const isExpired = entry.is_expired;
            const cachedDate = new Date(entry.cached_at).toLocaleDateString();
            const expiredClass = isExpired ? 'expired' : '';

            html += `
                <div class="cache-entry ${expiredClass}">
                    <div>
                        <strong>${entry.competitor}</strong>
                        <span class="data-source-indicator ${isExpired ? 'expired' : 'cached'}">
                            ${isExpired ? 'Expired' : 'Cached'}
                        </span>
                    </div>
                    <div class="cache-meta">
                        ${entry.sources_count} sources • ${cachedDate} • ${(entry.confidence_score * 100).toFixed(0)}% confidence
                    </div>
                </div>
            `;
        });

        if (cacheInfo.cache_entries.length > 5) {
            html += `<div class="cache-meta">... and ${cacheInfo.cache_entries.length - 5} more entries</div>`;
        }

        html += '</div>';
    }

    container.innerHTML = html;
}

async function clearAllCache() {
    if (!confirm('Are you sure you want to clear all cached research data?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/cache/clear`, {
            method: 'DELETE'
        });

        const result = await response.json();
        alert(result.message);
        await loadCacheInfo(); // Refresh display
    } catch (error) {
        console.error('Failed to clear cache:', error);
        alert('Failed to clear cache');
    }
}

async function cleanupExpiredCache() {
    try {
        const response = await fetch(`${API_BASE_URL}/cache/cleanup`, {
            method: 'POST'
        });

        const result = await response.json();
        alert(result.message);
        await loadCacheInfo(); // Refresh display
    } catch (error) {
        console.error('Failed to cleanup cache:', error);
        alert('Failed to cleanup expired cache');
    }
}

// Update progress to show cache indicators
function updateAgentProgress(agentKey, agentState) {
    if (!agentState) return;

    const progressBar = document.getElementById(`${agentKey}Progress`);
    const taskElement = document.getElementById(`${agentKey}Task`);

    if (progressBar) {
        progressBar.style.width = `${agentState.progress_percentage}%`;
        progressBar.textContent = `${agentState.progress_percentage}%`;
    }

    if (taskElement) {
        let taskText = agentState.current_task || 'Waiting...';

        // Add data source indicator
        let sourceIndicator = '';
        if (taskText.includes('Used cached data')) {
            sourceIndicator = '<span class="data-source-indicator cached">Cached</span>';
        } else if (taskText.includes('Completed fresh research')) {
            sourceIndicator = '<span class="data-source-indicator fresh">Fresh</span>';
        }

        const now = new Date().toLocaleTimeString();
        taskElement.innerHTML = `
            <div class="task-text">${taskText} ${sourceIndicator}</div>
            <div class="task-timestamp">Last updated: ${now}</div>
        `;
    }

    // Update progress bar color based on status
    if (progressBar) {
        progressBar.className = 'progress-fill';
        if (agentState.status === 'completed') {
            progressBar.style.backgroundColor = '#27ae60';
        } else if (agentState.status === 'failed') {
            progressBar.style.backgroundColor = '#e74c3c';
        } else if (agentState.status === 'in_progress') {
            progressBar.style.backgroundColor = '#3498db';

            if (taskText.includes('Calling GPT-5') || taskText.includes('web search')) {
                progressBar.classList.add('pulsing');
            }
        }
    }
}

// Initialize health monitoring
setInterval(async () => {
    const isHealthy = await checkAPIHealth();
    if (!isHealthy) {
        console.warn('API health check failed');
    }
}, 30000); // Check every 30 seconds