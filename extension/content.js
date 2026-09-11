// Content script for page interaction
console.log('Weather Plugin content script loaded');

// Listen for messages from background/popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getPageContent') {
    const content = {
      title: document.title,
      url: window.location.href,
      text: document.body.innerText,
      links: Array.from(document.querySelectorAll('a')).map(a => ({
        text: a.textContent.trim(),
        href: a.href
      })).slice(0, 100)
    };
    sendResponse(content);
  }
  return true;
});
