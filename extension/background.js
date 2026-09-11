// Background service worker for the extension
const API_BASE = 'http://localhost:8000';

chrome.runtime.onInstalled.addListener(() => {
  console.log('Weather Plugin installed');
  
  // Create context menu for scraping
  chrome.contextMenus.create({
    id: 'scrapePage',
    title: 'Scrape this page',
    contexts: ['page']
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'scrapePage') {
    scrapeCurrentPage(tab);
  }
});

async function scrapeCurrentPage(tab) {
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        return {
          title: document.title,
          url: window.location.href,
          text: document.body.innerText,
          links: Array.from(document.querySelectorAll('a')).map(a => ({
            text: a.textContent,
            href: a.href
          })).slice(0, 50)
        };
      }
    });
    
    const scrapedData = results[0].result;
    
    // Send to Python backend
    const response = await fetch(`${API_BASE}/api/scrape`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(scrapedData)
    });
    
    if (response.ok) {
      alert('Page scraped successfully!');
    } else {
      alert('Failed to send data to backend. Make sure the server is running.');
    }
  } catch (error) {
    console.error('Scraping error:', error);
    alert('Error scraping page: ' + error.message);
  }
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getWeather') {
    fetch(`${API_BASE}/api/weather`)
      .then(r => r.json())
      .then(data => sendResponse({ success: true, data }))
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true; // Keep message channel open for async response
  }
  
  if (request.action === 'getAnalytics') {
    fetch(`${API_BASE}/api/analytics`)
      .then(r => r.json())
      .then(data => sendResponse({ success: true, data }))
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true;
  }
});
