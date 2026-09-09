"""
Обёртка для C++ ядра с fallback на Python.
"""
import sys
import os
from typing import List, Optional, Dict, Any

# Добавляем корневую директорию в path для импорта core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.native_wrapper import (
        calculate_rsi as _cpp_rsi,
        calculate_sma as _cpp_sma,
        calculate_ema as _cpp_ema,
        calculate_macd as _cpp_macd,
        detect_anomaly as _cpp_anomaly,
        detect_pattern as _cpp_pattern,
    )
    NATIVE_AVAILABLE = True
except ImportError as e:
    NATIVE_AVAILABLE = False
    print(f"Warning: Native C++ bindings not available. Falling back to Python implementation. Error: {e}")
    _cpp_rsi = None
    _cpp_sma = None
    _cpp_ema = None
    _cpp_macd = None
    _cpp_anomaly = None
    _cpp_pattern = None

class NativeEngine:
    """
    Единый интерфейс к нативному ядру.
    Автоматически использует C++ версию если доступна, иначе Python.
    """
    
    def __init__(self):
        self.native_available = NATIVE_AVAILABLE
        self.use_cpp = NATIVE_AVAILABLE  # Добавляем атрибут для тестов
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> List[float]:
        """Рассчитать RSI"""
        if NATIVE_AVAILABLE and _cpp_rsi:
            return _cpp_rsi(prices, period)
        # Fallback на Python реализацию
        return self._py_rsi(prices, period)
    
    def calculate_sma(self, prices: List[float], period: int = 20) -> List[float]:
        """Рассчитать SMA"""
        if NATIVE_AVAILABLE and _cpp_sma:
            return _cpp_sma(prices, period)
        return self._py_sma(prices, period)
    
    def calculate_ema(self, prices: List[float], period: int = 20) -> List[float]:
        """Рассчитать EMA"""
        if NATIVE_AVAILABLE and _cpp_ema:
            return _cpp_ema(prices, period)
        return self._py_ema(prices, period)
    
    def calculate_macd(self, prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """Рассчитать MACD"""
        if NATIVE_AVAILABLE and _cpp_macd:
            return _cpp_macd(prices, fast, slow, signal)
        return self._py_macd(prices, fast, slow, signal)
    
    def detect_anomaly(self, history: List[float], current: float, lookback: int = 20, threshold: float = 3.0) -> Dict:
        """Детектировать аномалии"""
        if NATIVE_AVAILABLE and _cpp_anomaly:
            return _cpp_anomaly(history, current, lookback, threshold)
        return self._py_anomaly(history, current, lookback, threshold)
    
    def detect_pattern(self, prices: List[float], volumes: List[float], lookback: int = 14) -> Dict:
        """Определить паттерн"""
        if NATIVE_AVAILABLE and _cpp_pattern:
            return _cpp_pattern(prices, volumes, lookback)
        return self._py_pattern(prices, volumes, lookback)
    
    def _py_rsi(self, prices: List[float], period: int = 14) -> List[float]:
        """Python реализация RSI (fallback)"""
        if len(prices) < period + 1:
            return []
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            diff = prices[i] - prices[i-1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))
        
        if len(gains) < period:
            return []
        
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        result = []
        for i in range(period, len(gains) + 1):
            if avg_loss == 0:
                result.append(100)
            else:
                rs = avg_gain / avg_loss
                result.append(100 - (100 / (1 + rs)))
            
            if i < len(gains):
                avg_gain = (avg_gain * (period - 1) + gains[i]) / period
                avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        return result
    
    def _py_sma(self, prices: List[float], period: int = 20) -> List[float]:
        """Python реализация SMA (fallback)"""
        if len(prices) < period:
            return []
        
        result = []
        for i in range(period, len(prices) + 1):
            sma = sum(prices[i-period:i]) / period
            result.append(sma)
        
        return result
    
    def _py_ema(self, prices: List[float], period: int = 20) -> List[float]:
        """Python реализация EMA (fallback)"""
        if len(prices) < period:
            return []
        
        multiplier = 2.0 / (period + 1.0)
        result = []
        
        # First EMA is SMA
        first_ema = sum(prices[:period]) / period
        result.append(first_ema)
        
        for i in range(period, len(prices)):
            ema = (prices[i] - result[-1]) * multiplier + result[-1]
            result.append(ema)
        
        return result
    
    def _py_macd(self, prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """Python реализация MACD (fallback)"""
        if len(prices) < slow:
            return {'macd_line': [], 'signal_line': [], 'histogram': []}
        
        fast_ema = self._py_ema(prices, fast)
        slow_ema = self._py_ema(prices, slow)
        
        # MACD line = Fast EMA - Slow EMA
        macd_line = []
        offset = slow - fast
        for i in range(offset, len(fast_ema)):
            macd_line.append(fast_ema[i] - slow_ema[i - offset])
        
        # Signal line = EMA of MACD line
        if len(macd_line) < signal:
            return {'macd_line': macd_line, 'signal_line': [], 'histogram': []}
        
        signal_line = self._py_ema(macd_line, signal)
        
        # Histogram = MACD line - Signal line
        histogram = []
        for i in range(len(signal_line)):
            histogram.append(macd_line[i + signal - 1] - signal_line[i])
        
        return {
            'macd_line': macd_line,
            'signal_line': signal_line,
            'histogram': histogram
        }
    
    def _py_anomaly(self, history: List[float], current: float, lookback: int = 20, threshold: float = 3.0) -> Dict:
        """Python реализация детектирования аномалий (fallback)"""
        if not history:
            return {'is_anomaly': False, 'z_score': 0.0, 'deviation_percent': 0.0, 'anomaly_type': 'none'}
        
        recent = history[-lookback:] if len(history) > lookback else history
        mean = sum(recent) / len(recent)
        variance = sum((x - mean) ** 2 for x in recent) / len(recent)
        stddev = variance ** 0.5
        
        if stddev == 0:
            is_anomaly = current != mean
            return {
                'is_anomaly': is_anomaly,
                'z_score': 999.0 if is_anomaly else 0.0,
                'deviation_percent': 100.0 if is_anomaly else 0.0,
                'anomaly_type': 'spike' if is_anomaly else 'none'
            }
        
        z_score = (current - mean) / stddev
        deviation_percent = abs((current - mean) / mean) * 100.0 if mean != 0 else 0.0
        
        is_anomaly = abs(z_score) > threshold
        anomaly_type = 'spike' if z_score > 0 else 'drop' if is_anomaly else 'none'
        
        return {
            'is_anomaly': is_anomaly,
            'z_score': z_score,
            'deviation_percent': deviation_percent,
            'anomaly_type': anomaly_type
        }
    
    def _py_pattern(self, prices: List[float], volumes: List[float], lookback: int = 14) -> Dict:
        """Python реализация определения паттернов (fallback)"""
        if len(prices) < lookback:
            return {'pattern': 'UNKNOWN', 'confidence': 0.0, 'description': 'Insufficient data'}
        
        recent_prices = prices[-lookback:]
        first_price = recent_prices[0]
        last_price = recent_prices[-1]
        price_change_pct = (last_price - first_price) / abs(first_price) if first_price != 0 else 0
        
        mean = sum(recent_prices) / len(recent_prices)
        variance = sum((x - mean) ** 2 for x in recent_prices) / len(recent_prices)
        stddev = variance ** 0.5
        volatility = abs(stddev / mean) if mean != 0 else 0
        
        # Упрощенная логика определения паттерна
        if abs(price_change_pct) < 0.02 and volatility < 0.03:
            return {'pattern': 'RANGE_BOUND', 'confidence': 0.8, 'description': 'Price moving in range (flat)'}
        elif price_change_pct > 0.05:
            return {'pattern': 'TRENDING_UP', 'confidence': 0.7, 'description': 'Upward trend'}
        elif price_change_pct < -0.05:
            return {'pattern': 'TRENDING_DOWN', 'confidence': 0.7, 'description': 'Downward trend'}
        
        return {'pattern': 'UNKNOWN', 'confidence': 0.5, 'description': 'No clear pattern'}

__all__ = ["NativeEngine"]
