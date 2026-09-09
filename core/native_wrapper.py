"""
Python-обертка для C++ модулей MarketMonitor
Предоставляет удобный интерфейс для работы с native bindings
"""

from typing import List, Dict, Optional, Tuple
import sys
import os

# Добавляем путь к native bindings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from core.native_bindings import (
        calculate_rsi as _cpp_rsi,
        calculate_sma as _cpp_sma,
        calculate_ema as _cpp_ema,
        calculate_macd as _cpp_macd,
        calculate_volatility as _cpp_volatility,
        find_extremums as _cpp_extremums,
        compare_numeric_arrays as _cpp_compare_num,
        compare_dictionaries as _cpp_compare_dict,
        detect_anomaly as _cpp_anomaly,
        calculate_change_percent as _cpp_change_pct,
        detect_pattern as _cpp_pattern,
        Candle as _Candle,
        MACDResult as _MACDResult,
        ExtremumResult as _ExtremumResult,
        ChangeResult as _ChangeResult,
        AnomalyResult as _AnomalyResult,
        PatternResult as _PatternResult,
        PatternType as _PatternType,
    )
    NATIVE_AVAILABLE = True
except ImportError as e:
    NATIVE_AVAILABLE = False
    print(f"Warning: Native C++ bindings not available. Falling back to Python implementation. Error: {e}")


class Candle:
    """Свеча OHLCV для передачи в C++ функции"""
    def __init__(self, open: float, high: float, low: float, close: float, 
                 volume: float, timestamp: int):
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.timestamp = timestamp
    
    def to_cpp(self) -> Optional[_Candle]:
        if not NATIVE_AVAILABLE:
            return None
        cpp_candle = _Candle()
        cpp_candle.open = self.open
        cpp_candle.high = self.high
        cpp_candle.low = self.low
        cpp_candle.close = self.close
        cpp_candle.volume = self.volume
        cpp_candle.timestamp = self.timestamp
        return cpp_candle


def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
    """
    Расчет RSI (Relative Strength Index)
    
    Args:
        prices: Список цен закрытия
        period: Период расчета (по умолчанию 14)
    
    Returns:
        Список значений RSI
    """
    if NATIVE_AVAILABLE:
        return _cpp_rsi(prices, period)
    else:
        # Fallback на Python реализацию
        return _python_rsi(prices, period)


def calculate_sma(prices: List[float], period: int) -> List[float]:
    """Расчет SMA (Simple Moving Average)"""
    if NATIVE_AVAILABLE:
        return _cpp_sma(prices, period)
    return _python_sma(prices, period)


def calculate_ema(prices: List[float], period: int) -> List[float]:
    """Расчет EMA (Exponential Moving Average)"""
    if NATIVE_AVAILABLE:
        return _cpp_ema(prices, period)
    return _python_ema(prices, period)


def calculate_macd(prices: List[float], fast_period: int = 12, 
                   slow_period: int = 26, signal_period: int = 9) -> Dict:
    """
    Расчет MACD
    
    Returns:
        Dict с ключами: macd_line, signal_line, histogram
    """
    if NATIVE_AVAILABLE:
        result = _cpp_macd(prices, fast_period, slow_period, signal_period)
        return {
            'macd_line': result.macd_line,
            'signal_line': result.signal_line,
            'histogram': result.histogram
        }
    return _python_macd(prices, fast_period, slow_period, signal_period)


def detect_anomaly(history: List[float], current_value: float,
                   lookback_period: int = 20, z_threshold: float = 3.0) -> Dict:
    """
    Обнаружение аномалий
    
    Returns:
        Dict с ключами: is_anomaly, z_score, deviation_percent, anomaly_type
    """
    if NATIVE_AVAILABLE:
        result = _cpp_anomaly(history, current_value, lookback_period, z_threshold)
        return {
            'is_anomaly': result.is_anomaly,
            'z_score': result.z_score,
            'deviation_percent': result.deviation_percent,
            'anomaly_type': result.anomaly_type
        }
    return _python_detect_anomaly(history, current_value, lookback_period, z_threshold)


def detect_pattern(prices: List[float], volumes: List[float], 
                   lookback_period: int = 14) -> Dict:
    """
    Определение паттернов на графике
    
    Returns:
        Dict с ключами: pattern, confidence, description
    """
    if NATIVE_AVAILABLE:
        result = _cpp_pattern(prices, volumes, lookback_period)
        pattern_map = {
            _PatternType.REVERSAL_UP: 'REVERSAL_UP',
            _PatternType.REVERSAL_DOWN: 'REVERSAL_DOWN',
            _PatternType.BREAKOUT_UP: 'BREAKOUT_UP',
            _PatternType.BREAKOUT_DOWN: 'BREAKOUT_DOWN',
            _PatternType.RANGE_BOUND: 'RANGE_BOUND',
            _PatternType.TRENDING_UP: 'TRENDING_UP',
            _PatternType.TRENDING_DOWN: 'TRENDING_DOWN',
            _PatternType.UNKNOWN: 'UNKNOWN'
        }
        return {
            'pattern': pattern_map.get(result.pattern, 'UNKNOWN'),
            'confidence': result.confidence,
            'description': result.description
        }
    return _python_detect_pattern(prices, volumes, lookback_period)


def compare_numeric_arrays(old_data: List[float], new_data: List[float], 
                           threshold: float = 0.001) -> Dict:
    """Сравнение числовых массивов"""
    if NATIVE_AVAILABLE:
        result = _cpp_compare_num(old_data, new_data, threshold)
        return {
            'has_changes': result.has_changes,
            'changed_fields': result.changed_fields,
            'similarity_score': result.similarity_score,
            'change_type': result.change_type
        }
    return {'has_changes': old_data != new_data, 'changed_fields': [], 
            'similarity_score': 1.0 if old_data == new_data else 0.5}


# === Python fallback реализации (если native bindings недоступны) ===

def _python_rsi(prices: List[float], period: int = 14) -> List[float]:
    """Python реализация RSI для fallback"""
    if len(prices) < period + 1:
        return [0.0] * len(prices)
    
    result = [0.0] * len(prices)
    gains = []
    losses = []
    
    for i in range(1, period + 1):
        change = prices[i] - prices[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0:
        result[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        result[period] = 100.0 - (100.0 / (1.0 + rs))
    
    for i in range(period + 1, len(prices)):
        change = prices[i] - prices[i - 1]
        gain = max(change, 0)
        loss = max(-change, 0)
        
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period
        
        if avg_loss == 0:
            result[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i] = 100.0 - (100.0 / (1.0 + rs))
    
    return result


def _python_sma(prices: List[float], period: int) -> List[float]:
    """Python реализация SMA"""
    if len(prices) < period:
        return [0.0] * len(prices)
    
    result = [0.0] * len(prices)
    current_sum = sum(prices[:period])
    result[period - 1] = current_sum / period
    
    for i in range(period, len(prices)):
        current_sum = current_sum - prices[i - period] + prices[i]
        result[i] = current_sum / period
    
    return result


def _python_ema(prices: List[float], period: int) -> List[float]:
    """Python реализация EMA"""
    if len(prices) < period:
        return [0.0] * len(prices)
    
    result = [0.0] * len(prices)
    multiplier = 2.0 / (period + 1.0)
    
    result[period - 1] = sum(prices[:period]) / period
    
    for i in range(period, len(prices)):
        result[i] = (prices[i] - result[i - 1]) * multiplier + result[i - 1]
    
    return result


def _python_macd(prices: List[float], fast_period: int = 12,
                 slow_period: int = 26, signal_period: int = 9) -> Dict:
    """Python реализация MACD"""
    size = len(prices)
    macd_line = [0.0] * size
    signal_line = [0.0] * size
    histogram = [0.0] * size
    
    if size < slow_period:
        return {'macd_line': macd_line, 'signal_line': signal_line, 'histogram': histogram}
    
    fast_ema = _python_ema(prices, fast_period)
    slow_ema = _python_ema(prices, slow_period)
    
    for i in range(slow_period - 1, size):
        macd_line[i] = fast_ema[i] - slow_ema[i]
    
    macd_values = macd_line[slow_period - 1:]
    signal_ema = _python_ema(macd_values, signal_period)
    
    offset = slow_period - 1 + signal_period - 1
    for i in range(offset, size):
        signal_line[i] = signal_ema[i - offset]
        histogram[i] = macd_line[i] - signal_line[i]
    
    return {'macd_line': macd_line, 'signal_line': signal_line, 'histogram': histogram}


def _python_detect_anomaly(history: List[float], current_value: float,
                           lookback_period: int = 20, z_threshold: float = 3.0) -> Dict:
    """Python реализация детектирования аномалий"""
    if not history:
        return {'is_anomaly': False, 'z_score': 0.0, 'deviation_percent': 0.0, 'anomaly_type': 'none'}
    
    recent = history[-lookback_period:] if len(history) > lookback_period else history
    mean = sum(recent) / len(recent)
    variance = sum((x - mean) ** 2 for x in recent) / len(recent)
    stddev = variance ** 0.5
    
    if stddev == 0:
        is_anomaly = current_value != mean
        return {
            'is_anomaly': is_anomaly,
            'z_score': 999.0 if is_anomaly else 0.0,
            'deviation_percent': 100.0 if is_anomaly else 0.0,
            'anomaly_type': 'spike' if is_anomaly else 'none'
        }
    
    z_score = (current_value - mean) / stddev
    deviation_percent = abs((current_value - mean) / mean) * 100.0 if mean != 0 else 0.0
    
    is_anomaly = abs(z_score) > z_threshold
    anomaly_type = 'spike' if z_score > 0 else 'drop' if is_anomaly else 'none'
    
    return {
        'is_anomaly': is_anomaly,
        'z_score': z_score,
        'deviation_percent': deviation_percent,
        'anomaly_type': anomaly_type
    }


def _python_detect_pattern(prices: List[float], volumes: List[float],
                           lookback_period: int = 14) -> Dict:
    """Python реализация определения паттернов"""
    if len(prices) < lookback_period:
        return {'pattern': 'UNKNOWN', 'confidence': 0.0, 'description': 'Insufficient data'}
    
    recent_prices = prices[-lookback_period:]
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
