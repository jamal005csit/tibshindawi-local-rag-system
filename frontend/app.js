/**
 * Zero Cost Local RAG PDF System - Frontend JavaScript
 * Handles chat interface, API calls, and UI interactions
 */

// Configuration
const API_BASE_URL = 'http://localhost:8000';

// DOM Elements
const chatContainer = document.getElementById('chatContainer');
const questionInput = document.getElementById('questionInput');
const sendButton = document.getElementById('sendButton');
const loadingOverlay = document.getElementById('loadingOverlay');
const buttonText = document.getElementById('buttonText');

// State
let isProcessing = false;

/**
 * Initialize the application
 */
function init() {
    // Event listeners
    sendButton.addEventListener('click', handleSendMessage);
    questionInput.addEventListener('keydown', handleKeyDown);
    questionInput.addEventListener('input', autoResizeTextarea);
    
    // Check API health on load
    checkAPIHealth();
}

/**
 * Auto-resize textarea based on content
 */
function autoResizeTextarea() {
    questionInput.style.height = 'auto';
    questionInput.style.height = questionInput.scrollHeight + 'px';
}

/**
 * Handle keyboard events
 */
function handleKeyDown(event) {
    // Send on Enter (without Shift)
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        handleSendMessage();
    }
}

/**
 * Check API health status
 */
async function checkAPIHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        
        if (data.status === 'healthy') {
            console.log('API is healthy:', data);
        } else {
            showError('API is not healthy. Check server status.');
        }
    } catch (error) {
        console.error('Failed to connect to API:', error);
        showError('Cannot connect to server. Make sure the backend is running on port 8000.');
    }
}

/**
 * Handle send message button click
 */
async function handleSendMessage() {
    const question = questionInput.value.trim();
    
    // Validation
    if (!question) {
        return;
    }
    
    if (isProcessing) {
        return;
    }
    
    // Update state
    isProcessing = true;
    
    // Show user message
    addUserMessage(question);
    
    // Clear input
    questionInput.value = '';
    questionInput.style.height = 'auto';
    
    // Disable input
    setInputEnabled(false);
    
    // Show loading
    showLoading(true);
    
    try {
        // Call API
        const result = await askQuestion(question);
        
        // Hide loading
        showLoading(false);
        
        // Show AI response
        addAIMessage(result);
        
    } catch (error) {
        console.error('Error:', error);
        showLoading(false);
        showError(error.message || 'Failed to get response from server');
    } finally {
        // Reset state
        isProcessing = false;
        setInputEnabled(true);
        questionInput.focus();
    }
}

/**
 * Call the /ask API endpoint
 */
async function askQuestion(question) {
    const response = await fetch(`${API_BASE_URL}/ask`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question }),
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'API request failed');
    }
    
    return await response.json();
}

/**
 * Add user message to chat
 */
function addUserMessage(text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message user-message';
    
    messageDiv.innerHTML = `
        <div class="message-content">
            <p>${escapeHtml(text)}</p>
        </div>
    `;
    
    chatContainer.appendChild(messageDiv);
    scrollToBottom();
}

/**
 * Add AI message with sources to chat
 */
function addAIMessage(result) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message ai-message';
    
    // Format answer text (handles markdown and escaping)
    const answerHtml = formatAnswerText(escapeHtml(result.answer));
    
    // Build sources HTML (only if sources exist and are relevant)
    const sourcesHtml = buildSourcesHtml(result.sources);
    
    messageDiv.innerHTML = `
        <div class="message-content">
            ${answerHtml}
            ${sourcesHtml}
        </div>
    `;
    
    chatContainer.appendChild(messageDiv);
    
    // Add click handler for sources toggle if sources exist
    const sourcesHeader = messageDiv.querySelector('.sources-header');
    if (sourcesHeader) {
        sourcesHeader.addEventListener('click', toggleSources);
    }
    
    scrollToBottom();
}

/**
 * Format answer text with proper markdown-like rendering
 */
function formatAnswerText(text) {
    // Convert markdown-style formatting to HTML
    let html = text;
    
    // Bold text: **text** -> <strong>text</strong>
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    
    // Italic text: _text_ -> <em>text</em>
    html = html.replace(/(?<!\\)_(.+?)_(?!_)/g, '<em>$1</em>');
    
    // Blockquotes: > text -> <blockquote>text</blockquote>
    html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
    html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');
    
    // Split into paragraphs
    const paragraphs = html.split('\n\n').filter(p => p.trim());
    
    // Wrap each paragraph in <p> tags (except blockquotes)
    const formatted = paragraphs.map(para => {
        para = para.trim();
        if (para.startsWith('<blockquote>')) {
            return para;
        }
        // Handle single line breaks within paragraphs
        para = para.replace(/\n/g, '<br>');
        return `<p>${para}</p>`;
    });
    
    return formatted.join('');
}

/**
 * Build sources HTML section - minimal and collapsible
 */
function buildSourcesHtml(sources) {
    if (!sources || sources.length === 0) {
        return '';
    }
    
    // Show source if reasonably relevant
    if (sources[0].similarity_score < 0.3) {
        return '';
    }
    
    const source = sources[0];
    
    return `
        <div class="sources-section">
            <div class="sources-header">
                <span>📄 View Source</span>
                <span class="sources-toggle">▼</span>
            </div>
            <div class="sources-list">
                <div class="source-item">
                    <div class="source-header">
                        <span class="source-pdf">${escapeHtml(source.pdf_name)}</span>
                        <span class="source-similarity">${(source.similarity_score * 100).toFixed(0)}% match</span>
                    </div>
                    <div class="source-text">${escapeHtml(source.text_preview)}</div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Toggle sources visibility
 */
function toggleSources(event) {
    const header = event.currentTarget;
    const sourcesList = header.nextElementSibling;
    const toggle = header.querySelector('.sources-toggle');
    
    if (sourcesList.classList.contains('expanded')) {
        sourcesList.classList.remove('expanded');
        toggle.textContent = '▼ Expand';
    } else {
        sourcesList.classList.add('expanded');
        toggle.textContent = '▲ Collapse';
    }
}

/**
 * Show error message
 */
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'message ai-message';
    
    errorDiv.innerHTML = `
        <div class="message-content error-message">
            <strong>Error</strong>
            <p>${escapeHtml(message)}</p>
        </div>
    `;
    
    chatContainer.appendChild(errorDiv);
    scrollToBottom();
}

/**
 * Show/hide loading overlay
 */
function showLoading(show) {
    if (show) {
        loadingOverlay.classList.add('visible');
    } else {
        loadingOverlay.classList.remove('visible');
    }
}

/**
 * Enable/disable input controls
 */
function setInputEnabled(enabled) {
    questionInput.disabled = !enabled;
    sendButton.disabled = !enabled;
    
    if (enabled) {
        buttonText.textContent = 'Send';
    } else {
        buttonText.textContent = 'Processing...';
    }
}

/**
 * Scroll chat to bottom
 */
function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', init);
