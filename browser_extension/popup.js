// Popup script for browser extension
const API_BASE = 'http://localhost:8000';

document.addEventListener('DOMContentLoaded', () => {
    const parseBtn = document.getElementById('parseBtn');
    const parseUrlBtn = document.getElementById('parseUrlBtn');
    const weatherBtn = document.getElementById('weatherBtn');
    const copyBtn = document.getElementById('copyBtn');
    const selectorInput = document.getElementById('selector');
    const customUrlInput = document.getElementById('customUrl');
    const customSelectorInput = document.getElementById('customSelector');
    const resultCard = document.getElementById('resultCard');
    const resultContent = document.getElementById('resultContent');
    const statusMessage = document.getElementById('statusMessage');

    let lastResult = null;

    // Show status message
    function showStatus(message, type = 'info') {
        statusMessage.textContent = message;
        statusMessage.className = `status ${type}`;
        statusMessage.classList.remove('hidden');
        setTimeout(() => {
            statusMessage.classList.add('hidden');
        }, 5000);
    }

    // Display result
    function displayResult(data) {
        lastResult = data;
        resultCard.classList.remove('hidden');
        
        let html = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
        if (data.selected_content && data.selected_content.length > 0) {
            html += '<hr style="margin: 10px 0; border: none; border-top: 1px solid #ddd;"><strong>Selected Content:</strong><br>';
            data.selected_content.forEach((item, index) => {
                html += `<div style="margin-top: 5px; padding: 5px; background: white; border-radius: 3px;">${index + 1}. ${item}</div>`;
            });
        }
        resultContent.innerHTML = html;
    }

    // Parse current page
    parseBtn.addEventListener('click', async () => {
        const selector = selectorInput.value.trim();
        
        try {
            showStatus('Parsing current page...', 'info');
            
            // Send message to content script
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            
            const response = await chrome.tabs.sendMessage(tab.id, {
                action: 'getPageContent',
                selector: selector
            });
            
            if (response.error) {
                throw new Error(response.error);
            }
            
            // Send to backend for processing
            const backendResponse = await fetch(`${API_BASE}/api/parse`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: response.url,
                    selector: selector || null
                })
            });
            
            if (!backendResponse.ok) {
                throw new Error(`Server error: ${backendResponse.status}`);
            }
            
            const data = await backendResponse.json();
            displayResult(data);
            showStatus('Page parsed successfully!', 'success');
            
        } catch (error) {
            console.error('Parse error:', error);
            showStatus(`Error: ${error.message}`, 'error');
            displayResult({ error: error.message });
        }
    });

    // Parse custom URL
    parseUrlBtn.addEventListener('click', async () => {
        const url = customUrlInput.value.trim();
        const selector = customSelectorInput.value.trim();
        
        if (!url) {
            showStatus('Please enter a URL', 'error');
            return;
        }
        
        try {
            showStatus('Parsing URL...', 'info');
            
            const response = await fetch(`${API_BASE}/api/parse`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: url,
                    selector: selector || null
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }
            
            const data = await response.json();
            displayResult(data);
            showStatus('URL parsed successfully!', 'success');
            
        } catch (error) {
            console.error('Parse URL error:', error);
            showStatus(`Error: ${error.message}`, 'error');
            displayResult({ error: error.message });
        }
    });

    // Get weather data
    weatherBtn.addEventListener('click', async () => {
        try {
            showStatus('Fetching weather data...', 'info');
            
            const response = await fetch(`${API_BASE}/api/weather`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            displayResult(data);
            showStatus(`Weather data received for ${Object.keys(data.cities).length} cities`, 'success');
            
        } catch (error) {
            console.error('Weather error:', error);
            showStatus(`Error: ${error.message}. Is server running?`, 'error');
            displayResult({ error: error.message, hint: 'Make sure the Python server is running on localhost:8000' });
        }
    });

    // Copy to clipboard
    copyBtn.addEventListener('click', () => {
        if (lastResult) {
            navigator.clipboard.writeText(JSON.stringify(lastResult, null, 2))
                .then(() => showStatus('Copied to clipboard!', 'success'))
                .catch(err => showStatus('Failed to copy', 'error'));
        }
    });
});
