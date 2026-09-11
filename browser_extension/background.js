// Background service worker for the extension
chrome.runtime.onInstalled.addListener(() => {
    console.log('Parser extension installed');
    
    // Create context menu items
    chrome.contextMenus.create({
        id: 'parseSelection',
        title: 'Parse Selection with AI',
        contexts: ['selection']
    });
    
    chrome.contextMenus.create({
        id: 'parsePage',
        title: 'Parse This Page',
        contexts: ['page']
    });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
    if (info.menuItemId === 'parseSelection') {
        // Send selected text to backend
        fetch('http://localhost:8000/api/parse', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: tab.url,
                selector: null,
                selected_text: info.selectionText
            })
        }).catch(err => console.error('Parse error:', err));
    }
    
    if (info.menuItemId === 'parsePage') {
        // Open popup or send message to content script
        chrome.tabs.sendMessage(tab.id, { action: 'parsePage' });
    }
});

// Keep service worker alive
setInterval(() => {
    console.log('Service worker active');
}, 20000);
