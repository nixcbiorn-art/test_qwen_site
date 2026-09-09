"""
Chaos Generator v2.0 - Realistic Fault Injection & Data Corruption
Генератор реалистичного хаоса для проверки устойчивости, а не просто рандомайзер.
"""
import random
import time
import math
from typing import Any, Dict, List, Optional, Tuple, Callable
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ChaosGenerator:
    """
    Генератор хаоса с фокусом на реалистичные сценарии отказа.
    """
    
    def __init__(self, seed: Optional[int] = None, error_rate: float = 0.05):
        """
        :param seed: Для воспроизводимости тестов.
        :param error_rate: Вероятность инъекции ошибки (0.0 - 1.0).
        """
        self.seed = seed
        if seed is not None:
            random.seed(seed)
        self.error_rate = max(0.0, min(1.0, error_rate))
        self._error_types = [
            ConnectionError, TimeoutError, ValueError, RuntimeError, KeyError
        ]
        
    def generate_realistic_timeseries(
        self, 
        length: int, 
        base_value: float = 100.0, 
        noise_sigma: float = 2.0,
        trend: float = 0.0
    ) -> List[float]:
        """
        Генерирует временной ряд с нормальным распределением шума (Gaussian).
        Не использует равномерный рандом, имитируя реальные рыночные данные.
        """
        data = []
        current = base_value
        for i in range(length):
            noise = random.gauss(0, noise_sigma)
            current = current + trend + noise
            # Возвращаем к базовому уровню, чтобы не улетало в бесконечность (mean reversion)
            if i > 10:
                current = current * 0.99 + base_value * 0.01
            data.append(current)
        return data

    def inject_subtle_anomaly(
        self, 
        data: List[float], 
        position: int, 
        sigma_multiplier: float = 3.0
    ) -> List[float]:
        """
        Внедряет аномалию, которую сложно обнаружить (на грани статистической значимости).
        :param sigma_multiplier: На сколько сигм отклонять значение (реалистично 2.5 - 4.0).
        """
        if not data or position < 0 or position >= len(data):
            raise ValueError("Invalid data or position")
            
        result = data.copy()
        base_val = result[position]
        # Вычисляем локальное стандартное отклонение (упрощенно)
        local_std = 2.0  # Предполагаем известную дисперсию шума
        
        anomaly_value = base_val + (local_std * sigma_multiplier * random.choice([-1, 1]))
        result[position] = anomaly_value
        return result

    def corrupt_data_structurally(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """
        Портит структуру данных так, как это делают реальные баги API.
        Возвращает кортеж: (испорченные данные, тип коррупции).
        """
        corruption_type = random.choice([
            'null_injection', 'type_swap', 'missing_key', 'extra_nested', 'encoding_error'
        ])
        
        corrupted = data.copy()
        
        if corruption_type == 'null_injection':
            key = random.choice(list(corrupted.keys()))
            corrupted[key] = None
            
        elif corruption_type == 'type_swap':
            key = random.choice(list(corrupted.keys()))
            if isinstance(corrupted[key], (int, float)):
                corrupted[key] = str(corrupted[key])  # Число стало строкой
            elif isinstance(corrupted[key], str):
                corrupted[key] = 12345  # Строка стала числом
                
        elif corruption_type == 'missing_key':
            key = random.choice(list(corrupted.keys()))
            del corrupted[key]
            
        elif corruption_type == 'extra_nested':
            key = random.choice(list(corrupted.keys()))
            corrupted[key] = {"unexpected": "nested_object"}
            
        elif corruption_type == 'encoding_error':
            key = random.choice(list(corrupted.keys()))
            if isinstance(corrupted[key], str):
                corrupted[key] = corrupted[key] + "\x00\xFF\xFE"  # Битые байты
                
        return corrupted, corruption_type

    def inject_failure(self, func: Callable, *args, **kwargs) -> Any:
        """
        Выполняет функцию, но с вероятностью error_rate выбрасывает исключение.
        Имитирует нестабильность сети или сервиса.
        """
        if random.random() < self.error_rate:
            exc_class = random.choice(self._error_types)
            raise exc_class(f"Chaos Injection: {exc_class.__name__}")
        return func(*args, **kwargs)

    def run_stress_test(
        self, 
        func: Callable, 
        iterations: int = 100, 
        expected_fail_rate: float = 0.0
    ) -> Dict[str, Any]:
        """
        Прогоняет функцию N раз с инъекцией ошибок и собирает статистику.
        Возвращает отчет о реальном проценте сбоев.
        """
        success = 0
        failures = 0
        errors = []
        
        start_time = time.time()
        
        for i in range(iterations):
            try:
                # Принудительно включаем инжект для теста
                old_rate = self.error_rate
                self.error_rate = self.error_rate if self.error_rate > 0 else 0.1
                self.inject_failure(func)
                self.error_rate = old_rate
                success += 1
            except Exception as e:
                failures += 1
                errors.append(type(e).__name__)
                
        duration = time.time() - start_time
        
        actual_fail_rate = failures / iterations if iterations > 0 else 0
        
        return {
            "total": iterations,
            "success": success,
            "failures": failures,
            "actual_fail_rate": actual_fail_rate,
            "expected_fail_rate": self.error_rate,
            "duration_sec": duration,
            "error_distribution": {e: errors.count(e) for e in set(errors)},
            "passed": abs(actual_fail_rate - self.error_rate) < 0.15  # Допуск 15% на рандом
        }
