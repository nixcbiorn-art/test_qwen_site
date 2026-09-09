#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>

namespace market_native {

// Simple Moving Average (SMA)
std::vector<double> calculate_sma(const std::vector<double>& prices, int period) {
    std::vector<double> result;
    if (prices.size() < static_cast<size_t>(period)) {
        return result;
    }

    double sum = 0.0;
    for (int i = 0; i < period; ++i) {
        sum += prices[i];
    }
    result.push_back(sum / period);

    for (size_t i = period; i < prices.size(); ++i) {
        sum += prices[i] - prices[i - period];
        result.push_back(sum / period);
    }
    return result;
}

// Exponential Moving Average (EMA)
std::vector<double> calculate_ema(const std::vector<double>& prices, int period) {
    std::vector<double> result;
    if (prices.empty() || period <= 0) {
        return result;
    }

    double multiplier = 2.0 / (period + 1.0);
    result.reserve(prices.size());

    // First EMA is SMA
    double sum = 0.0;
    int count = std::min(static_cast<int>(prices.size()), period);
    for (int i = 0; i < count; ++i) {
        sum += prices[i];
    }
    double ema = sum / count;
    result.push_back(ema);

    for (size_t i = 1; i < prices.size(); ++i) {
        ema = (prices[i] - ema) * multiplier + ema;
        result.push_back(ema);
    }
    return result;
}

// Relative Strength Index (RSI)
std::vector<double> calculate_rsi(const std::vector<double>& prices, int period = 14) {
    std::vector<double> result;
    if (prices.size() < static_cast<size_t>(period) + 1) {
        return result;
    }

    std::vector<double> gains;
    std::vector<double> losses;

    for (size_t i = 1; i < prices.size(); ++i) {
        double change = prices[i] - prices[i - 1];
        gains.push_back(change > 0 ? change : 0.0);
        losses.push_back(change < 0 ? -change : 0.0);
    }

    // Initial average gain/loss
    double avg_gain = 0.0;
    double avg_loss = 0.0;
    for (int i = 0; i < period; ++i) {
        avg_gain += gains[i];
        avg_loss += losses[i];
    }
    avg_gain /= period;
    avg_loss /= period;

    // First RSI
    double rs = (avg_loss == 0.0) ? 100.0 : avg_gain / avg_loss;
    result.push_back(100.0 - (100.0 / (1.0 + rs)));

    // Subsequent RSI values using smoothed averages
    for (size_t i = period; i < gains.size(); ++i) {
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period;
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period;
        
        rs = (avg_loss == 0.0) ? 100.0 : avg_gain / avg_loss;
        result.push_back(100.0 - (100.0 / (1.0 + rs)));
    }

    return result;
}

// MACD (Moving Average Convergence Divergence)
struct MACDResult {
    std::vector<double> macd_line;
    std::vector<double> signal_line;
    std::vector<double> histogram;
};

MACDResult calculate_macd(const std::vector<double>& prices, 
                          int fast_period = 12, 
                          int slow_period = 26, 
                          int signal_period = 9) {
    MACDResult result;
    
    auto fast_ema = calculate_ema(prices, fast_period);
    auto slow_ema = calculate_ema(prices, slow_period);

    // Align EMAs
    size_t start_idx = slow_ema.size() < fast_ema.size() ? 
                       (fast_ema.size() - slow_ema.size()) : 0;
    
    std::vector<double> macd_raw;
    for (size_t i = 0; i < slow_ema.size(); ++i) {
        macd_raw.push_back(fast_ema[start_idx + i] - slow_ema[i]);
    }
    result.macd_line = macd_raw;

    // Calculate Signal Line (EMA of MACD line)
    if (!macd_raw.empty()) {
        result.signal_line = calculate_ema(macd_raw, signal_period);
        
        // Calculate Histogram
        size_t hist_start = result.signal_line.size() < result.macd_line.size() ?
                            (result.macd_line.size() - result.signal_line.size()) : 0;
        
        for (size_t i = 0; i < result.signal_line.size(); ++i) {
            result.histogram.push_back(result.macd_line[hist_start + i] - result.signal_line[i]);
        }
    }

    return result;
}

} // namespace market_native
