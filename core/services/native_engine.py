"""
Обёртка для C++ ядра с fallback на Python.
"""
import sys
import os
from typing import List, Optional, Dict, Any

sys.path.insert(0, '/workspace')

try:
    from core.native_wrapper import NativeEngine as CppNativeEngine
    NATIVE_AVAILABLE = True
except ImportError:
    NATIVE_AVAILABLE = False
    CppNativeEngine = None

class NativeEngine:
    """
    Единый интерфейс к нативному ядру.
    Автоматически использует C++ версию если доступна, иначе Python.
    """
    
    def __init__(self):
        self.native_available = NATIVE_AVAILABLE
        if NATIVE_AVAILABLE and CppNativeEngine:
            self._engine = CppNativeEngine()
        else:
            self._engine = None
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> List[float]:
        """Рассчитать RSI"""
        if self._engine:
            return self._engine.calculate_rsi(prices, period)
        # Fallback на Python реализацию
        return self._py_rsi(prices, period)
    
    def calculate_sma(self, prices: List[float], period: int = 20) -> List[float]:
        """Рассчитать SMA"""
        if self._engine:
            return self._engine.calculate_sma(prices, period)
        return self._py_sma(prices, period)
    
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

__all__ = ["NativeEngine"]
