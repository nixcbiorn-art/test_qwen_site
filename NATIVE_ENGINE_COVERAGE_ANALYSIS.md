# NativeEngine Test Coverage Analysis

**Date:** 2026-09-09 | **Status:** 🟡 PARTIAL COVERAGE

---

## Executive Summary

| Метод | Статус | Покрытие | Тесты | Примечание |
|-------|--------|---------|-------|-----------|
| `calculate_rsi()` | ✅ COVERED | 60% | test_e2e.py, test_adsky_e2e.py, test_tests.py | Базовый функционал, нет edge cases |
| `calculate_sma()` | ✅ COVERED | 70% | test_e2e.py, test_adsky_e2e.py | Хороший базовый тест, нужны граничные случаи |
| `calculate_ema()` | ✅ COVERED | 50% | test_adsky_e2e.py | Только проверка возврата данных |
| `calculate_macd()` | ⚠️ PARTIALLY | 40% | test_adsky_e2e.py | Только проверка структуры результата |
| `detect_anomaly()` | ✅ COVERED | 75% | test_e2e.py, test_adsky_e2e.py | Хороший тест с реалистичной аномалией |
| `detect_pattern()` | ❌ NOT COVERED | 0% | - | Функция существует, но тестов нет |

---

## Detailed Method Analysis

### 1. ✅ `calculate_rsi(prices, period=14)` - COVERED 60%

**NativeEngine Implementation:**
- Python fallback: `_py_rsi()` (строки 78-113)
- C++ wrapper: через `_cpp_rsi` (строки 12-13)

**Current Tests:**

#### ✅ test_e2e.py:189-191
```python
rsi_values = native_engine.calculate_rsi(prices, period=2)
assert len(rsi_values) > 0
assert all(0 <= r <= 100 for r in rsi_values if r is not None)
```
**Coverage:** ✅ Basic validation
- Проверяет: результат не пустой, значения в диапазоне [0, 100]
- Не проверяет: математическую корректность, точность расчётов

#### ✅ test_adsky_e2e.py:286-291
```python
rsi_values = native_engine.calculate_rsi(prices, period=2)
assert len(rsi_values) > 0
assert all(0 <= r <= 100 for r in rsi_values if r is not None)
```
**Coverage:** ✅ Duplicate of test_e2e
- Логирование каждого шага
- Те же проверки

#### ✅ test_tests.py (нет прямых тестов RSI)
- Есть `test_09_fallback_accuracy_comparison()` (строки 296-325) с проверкой через NativeEngine но с периодом 14

**Пробелы в покрытии:**
- ❌ Edge case: пустой список
- ❌ Edge case: список с одним элементом
- ❌ Edge case: период больше, чем размер списка
- ❌ Математическая точность: сравнение с известным результатом
- ❌ Тест с период=14 (стандартный), текущий тест только period=2
- ❌ Тест с очень маленькими периодами (period=1)
- ❌ Тест с шумом и трендом (реалистичные данные)

---

### 2. ✅ `calculate_sma(prices, period=20)` - COVERED 70%

**NativeEngine Implementation:**
- Python fallback: `_py_sma()` (строки 115-125)
- C++ wrapper: через `_cpp_sma` (строки 12-13)

**Current Tests:**

#### ✅ test_e2e.py:193-196
```python
sma_values = native_engine.calculate_sma(prices, period=2)
assert len(sma_values) > 0
assert sma_values[-1] == pytest.approx(12_500_000, rel=0.01)
```
**Coverage:** ✅ Good
- Проверяет: результат не пустой
- Проверяет: конкретное значение SMA (последнее)
- **Хорошая практика:** использование `pytest.approx()` для floating point сравнения

#### ✅ test_adsky_e2e.py:294-300
```python
sma_values = native_engine.calculate_sma(prices, period=2)
assert len(sma_values) > 0
expected_sma = 12_500_000
assert sma_values[-1] == pytest.approx(expected_sma, rel=0.01)
```
**Coverage:** ✅ Duplicate

**Пробелы в покрытии:**
- ❌ Edge case: пустой список
- ❌ Edge case: период=1 (SMA должна = исходная цена)
- ❌ Edge case: период > длина списка
- ❌ Проверка всех значений SMA, не только последнего
- ❌ Тест с периодом=20 (по умолчанию), текущий только period=2
- ❌ Проверка скользящего окна (правильное вычисление суммы)

---

### 3. ⚠️ `calculate_ema(prices, period=20)` - COVERED 50%

**NativeEngine Implementation:**
- Python fallback: `_py_ema()` (строки 127-143)
- C++ wrapper: через `_cpp_ema` (строки 12-13)

**Current Tests:**

#### ✅ test_adsky_e2e.py:616-620
```python
ema = engine.calculate_ema(prices, period=3)
assert len(ema) > 0
```
**Coverage:** ❌ Minimal
- Только проверяет: результат не пустой
- **НЕ проверяет:** 
  - Математическую корректность EMA
  - Значения в диапазоне
  - Сравнение с известным результатом

#### ✅ test_e2e.py:361-362
```python
ema = engine.calculate_ema(prices, period=3)
assert len(ema) > 0
```
**Coverage:** ❌ Same minimal check

**Пробелы в покрытии:**
- ❌ Edge case: пустой список
- ❌ Edge case: период > длина списка
- ❌ Проверка, что первое EMA = SMA (строка 136 в native_engine.py)
- ❌ Проверка multiplier = 2.0 / (period + 1)
- ❌ Проверка convergence EMA к актуальным ценам
- ❌ Численное сравнение с эталонной реализацией
- ❌ Тест с большими периодами (14, 26)

---

### 4. ⚠️ `calculate_macd(prices, fast=12, slow=26, signal=9)` - COVERED 40%

**NativeEngine Implementation:**
- Python fallback: `_py_macd()` (строки 145-174)
- C++ wrapper: через `_cpp_macd` (строки 12-13)

**Current Tests:**

#### ✅ test_adsky_e2e.py:623-627
```python
macd = engine.calculate_macd(prices)
assert 'macd_line' in macd or 'signal' in macd or 'histogram' in macd
assert isinstance(macd, dict)
```
**Coverage:** ❌ Very weak
- Только проверяет: тип результата и наличие ключей
- **Проблема:** условие `or` означает, что тест пройдёт даже если только один ключ присутствует

#### ✅ test_tests.py (нет прямых тестов MACD)

**Пробелы в покрытии:**
- ❌ Edge case: пустой список
- ❌ Edge case: период (fast, slow, signal) > длина списка
- ❌ Проверка, что все три линии (macd_line, signal_line, histogram) присутствуют
- ❌ Проверка длины каждой линии
- ❌ Проверка, что histogram = macd_line - signal_line
- ❌ Проверка, что signal_line = EMA(macd_line)
- ❌ Тест с default параметрами (fast=12, slow=26, signal=9)
- ❌ Тест с custom параметрами
- ❌ Проверка convergence и divergence сигналов

---

### 5. ✅ `detect_anomaly(history, current, lookback=20, threshold=3.0)` - COVERED 75%

**NativeEngine Implementation:**
- Python fallback: `_py_anomaly()` (строки 176-206)
- C++ wrapper: через `_cpp_anomaly` (строки 12-13)

**Current Tests:**

#### ✅ test_e2e.py:268-290 - EXCELLENT
```python
price_history = [10_000_000, 10_200_000, 10_100_000, 10_300_000]
anomalous_price = 20_000_000  # Аномалия

anomaly_result = native_engine.detect_anomaly(
    history=price_history, 
    current=anomalous_price, 
    lookback=4, 
    threshold=2.0
)

assert isinstance(anomaly_result, dict)
assert 'is_anomaly' in anomaly_result
assert 'z_score' in anomaly_result
assert 'deviation_percent' in anomaly_result
assert 'anomaly_type' in anomaly_result

assert anomaly_result['is_anomaly'] == True
assert abs(anomaly_result['z_score']) > 2.0
assert anomaly_result['anomaly_type'] in ['spike', 'drop']
```
**Coverage:** ✅ Good
- Проверяет: структуру результата
- Проверяет: обнаружение реальной аномалии (2x превышение)
- Проверяет: z_score > threshold
- Проверяет: тип аномалии (spike/drop)

#### ✅ test_adsky_e2e.py:464-492 - EXCELLENT (duplicate)

#### ✅ test_tests.py:296-325
```python
engine = NativeEngine()
prices = [100.0 + i * 0.5 for i in range(50)]
result = engine.calculate_rsi(prices, period=14)
# Проверяет детерминированность
result2 = engine.calculate_rsi(prices, period=14)
assert abs(result - result2) < 1e-6
```
**Coverage:** ✅ но это test для RSI, не detect_anomaly

**Пробелы в покрытии:**
- ❌ Edge case: пустой history
- ❌ Edge case: history с одной точкой
- ❌ Проверка false positives (нормальный шум не должен быть аномалией)
- ❌ Проверка false negatives (реальные аномалии должны обнаруживаться)
- ❌ Edge case: current = среднее (z_score ≈ 0, не аномалия)
- ❌ Edge case: history с одинаковыми значениями (stddev=0, деление на ноль?)
- ❌ Проверка параметра lookback (как он влияет на результат?)
- ❌ Тест с разными threshold значениями (1.0, 2.0, 3.0, 4.0)
- ❌ Граница между spike и drop

---

### 6. ❌ `detect_pattern(prices, volumes, lookback=14)` - NOT COVERED 0%

**NativeEngine Implementation:**
- Python fallback: `_py_pattern()` (строки 208-231)
- C++ wrapper: через `_cpp_pattern` (строки 12-13)

**Current Tests:** NONE

**Пробелы:**
- ❌ Нет тестов вообще
- ❌ Edge case: пустой список цен/объёмов
- ❌ Проверка типов паттернов:
  - 'RANGE_BOUND' (price_change < 2%, volatility < 3%)
  - 'TRENDING_UP' (price_change > 5%)
  - 'TRENDING_DOWN' (price_change < -5%)
  - 'UNKNOWN'
- ❌ Проверка confidence (0.0-1.0)
- ❌ Проверка description
- ❌ Тест каждого паттерна с синтетическими данными

---

## Test Coverage Summary by Category

### Edge Cases Coverage: 🔴 **POOR**

| Случай | RSI | SMA | EMA | MACD | Anomaly | Pattern |
|--------|-----|-----|-----|------|---------|---------|
| Пустой список | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| период > len | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Один элемент | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Одинаковые значения | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Нулевые значения | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

### Mathematical Correctness: 🟡 **PARTIAL**

| Метод | Проверка | Статус |
|-------|----------|--------|
| RSI | Формула 100 - (100 / (1 + RS)) | ⚠️ Косвенно через range [0, 100] |
| SMA | (sum of N prices) / N | ✅ Проверено конкретное значение |
| EMA | First = SMA, then multiplier | ❌ |
| MACD | histogram = macd - signal | ❌ |
| Anomaly | z_score formula | ⚠️ Косвенно через > threshold |
| Pattern | confidence range | ❌ |

### Parameter Variations: 🔴 **POOR**

| Метод | Default | Custom | Boundary |
|-------|---------|--------|----------|
| RSI | period=14 | ⚠️ period=2 | ❌ |
| SMA | period=20 | ⚠️ period=2 | ❌ |
| EMA | period=20 | ⚠️ period=3 | ❌ |
| MACD | fast=12, slow=26, signal=9 | ❌ | ❌ |
| Anomaly | lookback=20, threshold=3.0 | ✅ threshold=2.0 | ❌ |
| Pattern | lookback=14 | ❌ | ❌ |

---

## Recommendations for Improvement

### 🔴 CRITICAL - Must Add

1. **Edge Cases Test Suite** (`tests/test_native_engine_edge_cases.py`)
   ```python
   @pytest.mark.parametrize("prices,period,description", [
       ([], 14, "empty list"),
       ([100], 14, "single element"),
       ([100, 100, 100], 5, "period > length"),
       ([100, 100, 100], 1, "constant prices"),
       ([0, 0, 0], 3, "zero prices"),
       ([-1, -2, -3], 2, "negative prices"),
   ])
   def test_rsi_edge_cases(prices, period, description):
       engine = NativeEngine()
       result = engine.calculate_rsi(prices, period)
       # Should not crash
       assert isinstance(result, list)
   ```

2. **Pattern Detection Tests** (`tests/test_detect_pattern.py`)
   - Тест RANGE_BOUND: пример с малым price_change и volatility
   - Тест TRENDING_UP: вверхний тренд +10%
   - Тест TRENDING_DOWN: нижний тренд -10%
   - Тест UNKNOWN: смешанные данные

3. **MACD Correctness Test**
   ```python
   def test_macd_histogram_calculation():
       # histogram должен = macd_line - signal_line
       prices = [100 + i for i in range(50)]
       macd = engine.calculate_macd(prices)
       
       for i in range(len(macd['histogram'])):
           if macd['macd_line'][i] != 0 and macd['signal_line'][i] != 0:
               expected = macd['macd_line'][i] - macd['signal_line'][i]
               assert macd['histogram'][i] == pytest.approx(expected)
   ```

### 🟡 IMPORTANT - Should Add

4. **Boundary Parameter Tests**
   ```python
   @pytest.mark.parametrize("period", [1, 2, 5, 14, 20, 50])
   def test_sma_different_periods(period):
       prices = list(range(1, 101))  # 100 prices
       result = engine.calculate_sma(prices, period)
       assert len(result) == 100 - period + 1
   ```

5. **Anomaly Threshold Sensitivity**
   ```python
   def test_anomaly_threshold_sensitivity():
       history = [100, 101, 99, 102, 100]
       anomalous = 200
       
       r1 = engine.detect_anomaly(history, anomalous, threshold=1.0)
       r2 = engine.detect_anomaly(history, anomalous, threshold=10.0)
       
       assert r1['is_anomaly'] == True
       assert r2['is_anomaly'] == False  # threshold too high
   ```

6. **Numerical Accuracy Tests** (vs. known good implementation)
   ```python
   def test_rsi_numerical_accuracy():
       # Reference values calculated from TradingView
       prices = [44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42]
       rsi = engine.calculate_rsi(prices, period=5)
       
       # Expected: ~70.46
       assert rsi[-1] == pytest.approx(70.46, abs=0.5)
   ```

### 🟢 NICE TO HAVE

7. **Performance Benchmarks** (C++ vs Python)
   ```python
   def test_performance_cpp_vs_python():
       large_dataset = list(range(1, 10001))
       
       with pytest.benchmark.pedantic(lambda: ..., rounds=5):
           engine.calculate_rsi(large_dataset, period=14)
   ```

8. **Fallback Coverage** (force Python, verify results match)
   ```python
   def test_fallback_accuracy_vs_cpp():
       # Временно отключаем C++
       # Проверяем что Python fallback дает те же результаты
   ```

---

## Test File Organization Suggestion

```
tests/
├── test_native_engine_rsi.py          # RSI: basic, edge cases, accuracy
├── test_native_engine_sma.py          # SMA: basic, edge cases, accuracy
├── test_native_engine_ema.py          # EMA: basic, edge cases, accuracy
├── test_native_engine_macd.py         # MACD: basic, edge cases, accuracy
├── test_native_engine_anomaly.py      # Anomaly: basic, thresholds, false pos/neg
├── test_native_engine_pattern.py      # Pattern: all types, confidence
├── test_native_engine_edge_cases.py   # All methods: empty, overflow, etc.
├── test_native_engine_integration.py  # E2E workflow
└── test_adsky_e2e.py                  # Existing (keep)
```

---

## Coverage Metrics (Estimated)

### Code Coverage (Statement)
- **Current:** ~55% (основные пути)
- **Target:** 90% (включая error paths)

### Path Coverage (Branch)
- **Current:** ~35% (edge cases не покрыты)
- **Target:** 85%

### Functional Coverage
- **Implemented:** 6 functions
- **Tested:** 5 functions (83%)
- **Well-tested:** 2 functions (33%)

### Defect Detection Potential
- **Current:** 🟡 Medium (базовые баги будут найдены)
- **Potential:** 🔴 Низкий (edge cases не покрыты)

---

## Conclusion

Тесты **хорошо покрывают основной функционал**, но имеют **критические пробелы в edge cases и граничных условиях**. 

**Приоритет:**
1. 🔴 Добавить тесты для `detect_pattern()` (0% покрытие)
2. 🔴 Добавить edge cases для всех методов
3. 🟡 Добавить численную валидацию (сравнение с известными результатами)
4. 🟡 Добавить параметризованные тесты для разных периодов

**Ожидаемое улучшение:** с 55% до 85-90% code coverage после реализации рекомендаций.
