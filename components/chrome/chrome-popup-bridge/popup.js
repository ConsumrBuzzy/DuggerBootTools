/**
 * Convoso Insight Lens - Popup Script
 * Opens overlay dashboard on Convoso page
 */

document.addEventListener('DOMContentLoaded', () => {
    // Check current status
    checkStatus();

    // Open Dashboard button
    document.getElementById('openDashboard').addEventListener('click', () => {
        sendToContent('openOverlay', (response) => {
            if (response && response.status === 'ok') {
                window.close(); // Close popup after opening overlay
            }
        });
    });
});

/**
 * Check status from content script
 */
function checkStatus() {
    const statusText = document.getElementById('statusText');
    const statusDot = document.getElementById('statusDot');

    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (!tabs[0]) {
            showError('No active tab');
            return;
        }

        if (!tabs[0].url.includes('convoso.com')) {
            showError('Not on Convoso');
            return;
        }

        chrome.tabs.sendMessage(tabs[0].id, { action: 'getStatus' }, (response) => {
            if (chrome.runtime.lastError) {
                showError('Refresh page');
                return;
            }

            if (response && response.status === 'ok') {
                updateUI(response.enabled, response.columnsInjected);
            }
        });
    });
}

/**
 * Send message to content script
 */
function sendToContent(action, callback) {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (!tabs[0]) return;
        
        chrome.tabs.sendMessage(tabs[0].id, { action }, (response) => {
            if (callback) callback(response);
        });
    });
}

/**
 * Update UI based on status
 */
function updateUI(enabled, columnsInjected) {
    const statusText = document.getElementById('statusText');
    const statusDot = document.getElementById('statusDot');

    statusText.textContent = 'Ready - Click to open dashboard';
    statusDot.className = 'status-dot active';
}

/**
 * Show error state
 */
function showError(message) {
    const statusText = document.getElementById('statusText');
    const statusDot = document.getElementById('statusDot');
    const btn = document.getElementById('openDashboard');

    statusText.textContent = message;
    statusDot.className = 'status-dot error';
    btn.disabled = true;
    btn.textContent = 'Unavailable';
}

