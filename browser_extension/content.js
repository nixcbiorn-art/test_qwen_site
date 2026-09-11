// Content script that runs on web pages
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'getPageContent') {
        try {
            const result = {
                url: window.location.href,
                title: document.title,
                content_length: document.body.innerHTML.length
            };
            
            // If selector provided, extract specific content
            if (request.selector) {
                const elements = document.querySelectorAll(request.selector);
                result.selected_content = Array.from(elements).map(el => el.textContent.trim());
                result.selected_html = Array.from(elements).map(el => el.outerHTML);
                result.found_elements = elements.length;
            }
            
            sendResponse(result);
        } catch (error) {
            sendResponse({ error: error.message });
        }
    }
});
