#include "indicators.h"
#include <cmath>
#include <algorithm>
#include <numeric>

namespace market_monitor {
namespace native {

// Вспомогательная функция для расчета среднего
static double calculate_mean(const std::vector<double>& data, int start, int count) {
    if (count <= 0 || start < 0 || start + count > data.size()) {
        return 0.0;
    }
    double sum = 0.0;
    for (int i = start; i < start + count; ++i) {
        sum += data[i];
    }
    return sum / count;
}

std::vector<double> calculate_rsi(const std::vector<double>& prices, int period) {
    std::vector<double> result(prices.size(), 0.0);
    if (prices.size() < static_cast<size_t>(period + 1)) {
        return result;
    }

    std::vector<double> gains(period, 0.0);
    std::vector<double> losses(period, 0.0);

    // Расчет первых изменений
    for (size_t i = 1; i <= static_cast<size_t>(period); ++i) {
        double change = prices[i] - prices[i - 1];
        if (change > 0) {
            gains[i - 1] = change;
        } else {
            losses[i - 1] = std::abs(change);
        }
    }

    double avg_gain = std::accumulate(gains.begin(), gains.end(), 0.0) / period;
    double avg_loss = std::accumulate(losses.begin(), losses.end(), 0.0) / period;

    // Первый RSI
    if (avg_loss == 0.0) {
        result[period] = 100.0;
    } else {
        double rs = avg_gain / avg_loss;
        result[period] = 100.0 - (100.0 / (1.0 + rs));
    }

    // Последующие значения с использованием сглаживания Уайлдера
    for (size_t i = period + 1; i < prices.size(); ++i) {
        double change = prices[i] - prices[i - 1];
        double gain = (change > 0) ? change : 0.0;
        double loss = (change < 0) ? std::abs(change) : 0.0;

        avg_gain = ((avg_gain * (period - 1)) + gain) / period;
        avg_loss = ((avg_loss * (period - 1)) + loss) / period;

        if (avg_loss == 0.0) {
            result[i] = 100.0;
        } else {
            double rs = avg_gain / avg_loss;
            result[i] = 100.0 - (100.0 / (1.0 + rs));
        }
    }

    return result;
}

std::vector<double> calculate_sma(const std::vector<double>& prices, int period) {
    std::vector<double> result(prices.size(), 0.0);
    if (prices.size() < static_cast<size_t>(period)) {
        return result;
    }

    double current_sum = 0.0;
    for (int i = 0; i < period; ++i) {
        current_sum += prices[i];
    }
    result[period - 1] = current_sum / period;

    for (size_t i = period; i < prices.size(); ++i) {
        current_sum = current_sum - prices[i - period] + prices[i];
        result[i] = current_sum / period;
    }

    return result;
}

std::vector<double> calculate_ema(const std::vector<double>& prices, int period) {
    std::vector<double> result(prices.size(), 0.0);
    if (prices.size() < static_cast<size_t>(period)) {
        return result;
    }

    double multiplier = 2.0 / (period + 1.0);
    
    // Первая EMA равна SMA
    double sum = 0.0;
    for (int i = 0; i < period; ++i) {
        sum += prices[i];
    }
    result[period - 1] = sum / period;

    // Расчет последующих значений
    for (size_t i = period; i < prices.size(); ++i) {
        result[i] = (prices[i] - result[i - 1]) * multiplier + result[i - 1];
    }

    return result;
}

MACDResult calculate_macd(const std::vector<double>& prices, 
                          int fast_period, 
                          int slow_period, 
                          int signal_period) {
    MACDResult result;
    size_t size = prices.size();
    
    result.macd_line.resize(size, 0.0);
    result.signal_line.resize(size, 0.0);
    result.histogram.resize(size, 0.0);

    if (size < static_cast<size_t>(slow_period)) {
        return result;
    }

    std::vector<double> fast_ema = calculate_ema(prices, fast_period);
    std::vector<double> slow_ema = calculate_ema(prices, slow_period);

    // Расчет MACD линии
    for (size_t i = slow_period - 1; i < size; ++i) {
        result.macd_line[i] = fast_ema[i] - slow_ema[i];
    }

    // Извлечение значимых значений для расчета сигнальной линии
    std::vector<double> macd_values;
    for (size_t i = slow_period - 1; i < size; ++i) {
        macd_values.push_back(result.macd_line[i]);
    }

    std::vector<double> signal_ema = calculate_ema(macd_values, signal_period);

    // Заполнение сигнальной линии
    size_t offset = slow_period - 1 + signal_period - 1;
    for (size_t i = offset; i < size; ++i) {
        result.signal_line[i] = signal_ema[i - offset];
    }

    // Расчет гистограммы
    for (size_t i = offset; i < size; ++i) {
        result.histogram[i] = result.macd_line[i] - result.signal_line[i];
    }

    return result;
}

std::vector<double> calculate_volatility(const std::vector<double>& prices, int period) {
    std::vector<double> result(prices.size(), 0.0);
    if (prices.size() < static_cast<size_t>(period)) {
        return result;
    }

    for (size_t i = period - 1; i < prices.size(); ++i) {
        double mean = calculate_mean(prices, i - period + 1, period);
        double variance_sum = 0.0;
        
        for (int j = i - period + 1; j <= static_cast<int>(i); ++j) {
            double diff = prices[j] - mean;
            variance_sum += diff * diff;
        }
        
        result[i] = std::sqrt(variance_sum / period);
    }

    return result;
}

ExtremumResult find_extremums(const std::vector<Candle>& candles, int period) {
    ExtremumResult result;
    size_t size = candles.size();
    
    result.highs.resize(size, 0.0);
    result.lows.resize(size, 0.0);

    if (size < static_cast<size_t>(period)) {
        return result;
    }

    for (size_t i = period - 1; i < size; ++i) {
        double max_high = candles[i - period + 1].high;
        double min_low = candles[i - period + 1].low;

        for (int j = i - period + 1; j <= static_cast<int>(i); ++j) {
            if (candles[j].high > max_high) max_high = candles[j].high;
            if (candles[j].low < min_low) min_low = candles[j].low;
        }

        result.highs[i] = max_high;
        result.lows[i] = min_low;
    }

    return result;
}

} // namespace native
} // namespace market_monitor
