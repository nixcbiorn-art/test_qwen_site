// Основной JavaScript для MarketMonitor

document.addEventListener('DOMContentLoaded', () => {
    console.log('MarketMonitor UI загружен');
});

// Утилита для форматирования даты
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('ru-RU', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Утилита для форматирования чисел
function formatNumber(num, decimals = 2) {
    return Number(num).toFixed(decimals);
}

// AJAX запрос с обработкой ошибок
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Ошибка запроса');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        alert(`❌ ${error.message}`);
        throw error;
    }
}

// Показ уведомления
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 2rem;
        background: ${type === 'success' ? '#2ecc71' : type === 'error' ? '#e74c3c' : '#3498db'};
        color: white;
        border-radius: 5px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        z-index: 3000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Подтверждение действия
function confirmAction(message) {
    return confirm(message);
}

// Автообновление страницы
let autoRefreshInterval;

function startAutoRefresh(seconds, callback) {
    stopAutoRefresh();
    autoRefreshInterval = setInterval(callback, seconds * 1000);
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

// Экспорт данных в CSV
function exportToCSV(data, filename) {
    const csv = data.map(row => Object.values(row).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

// LocalStorage утилиты
const storage = {
    get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch {
            return defaultValue;
        }
    },
    
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (error) {
            console.error('LocalStorage error:', error);
        }
    },
    
    remove(key) {
        localStorage.removeItem(key);
    }
};

// Анимация загрузки
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '<div class="loading">⏳ Загрузка...</div>';
    }
}

function hideLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        const loading = element.querySelector('.loading');
        if (loading) loading.remove();
    }
}

// Валидация форм
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    const inputs = form.querySelectorAll('input[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.style.borderColor = '#e74c3c';
            isValid = false;
        } else {
            input.style.borderColor = '#ddd';
        }
    });
    
    return isValid;
}

// Дебаунс для поиска
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Тёмная тема
function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    storage.set('darkMode', isDark);
    
    if (isDark) {
        document.documentElement.style.setProperty('--bg-color', '#1a1a2e');
        document.documentElement.style.setProperty('--text-color', '#eee');
    } else {
        document.documentElement.style.setProperty('--bg-color', '#f5f6fa');
        document.documentElement.style.setProperty('--text-color', '#333');
    }
}

// Инициализация при загрузке
if (storage.get('darkMode')) {
    toggleDarkMode();
}

console.log('MarketMonitor JS готов к работе');
