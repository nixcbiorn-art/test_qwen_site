// Popup script
document.addEventListener('DOMContentLoaded', loadWeather);

document.getElementById('refreshBtn').addEventListener('click', loadWeather);
document.getElementById('analyticsBtn').addEventListener('click', toggleAnalytics);

async function loadWeather() {
  const statusEl = document.getElementById('status');
  const citiesEl = document.getElementById('cities');
  
  statusEl.textContent = 'Loading...';
  
  try {
    chrome.runtime.sendMessage({ action: 'getWeather' }, (response) => {
      if (chrome.runtime.lastError) {
        statusEl.textContent = 'Error: Cannot connect to background script';
        return;
      }
      
      if (response && response.success) {
        const data = response.data;
        statusEl.textContent = 'Last update: ' + (data.last_update || '--:--:--');
        
        if (data.cities && data.cities.length > 0) {
          citiesEl.innerHTML = data.cities.map(city => `
            <div class="city">
              <strong>${city.city}</strong><br>
              <span class="temp">${city.temp}°C</span><br>
              <span class="wind">Wind: ${city.wind} km/h</span>
            </div>
          `).join('');
        } else {
          citiesEl.innerHTML = '<p>No data yet. Wait for next update...</p>';
        }
      } else {
        statusEl.textContent = 'Server not running. Start Python backend first.';
        citiesEl.innerHTML = '';
      }
    });
  } catch (error) {
    statusEl.textContent = 'Error: ' + error.message;
  }
}

async function toggleAnalytics() {
  const analyticsEl = document.getElementById('analytics');
  
  if (analyticsEl.style.display === 'none') {
    analyticsEl.style.display = 'block';
    analyticsEl.textContent = 'Loading analytics...';
    
    chrome.runtime.sendMessage({ action: 'getAnalytics' }, (response) => {
      if (response && response.success) {
        const data = response.data;
        if (data.error) {
          analyticsEl.textContent = data.error;
        } else {
          analyticsEl.innerHTML = Object.entries(data).map(([city, stats]) => `
            <div class="city">
              <strong>${city}</strong><br>
              Avg: ${stats.avg_temp.toFixed(1)}°C | 
              Min: ${stats.min_temp}°C | 
              Max: ${stats.max_temp}°C
            </div>
          `).join('');
        }
      } else {
        analyticsEl.textContent = 'No analytics data available yet.';
      }
    });
  } else {
    analyticsEl.style.display = 'none';
  }
}
