#ifndef INDICATORS_H
#define INDICATORS_H

#include <vector>
#include <string>

namespace market_monitor {
namespace native {

// Структура для свечи OHLCV
struct Candle {
    double open;
    double high;
    double low;
    double close;
    double volume;
    long long timestamp;
};

// Расчет RSI (Relative Strength Index)
std::vector<double> calculate_rsi(const std::vector<double>& prices, int period = 14);

// Расчет SMA (Simple Moving Average)
std::vector<double> calculate_sma(const std::vector<double>& prices, int period);

// Расчет EMA (Exponential Moving Average)
std::vector<double> calculate_ema(const std::vector<double>& prices, int period);

// Расчет MACD (Moving Average Convergence Divergence)
struct MACDResult {
    std::vector<double> macd_line;
    std::vector<double> signal_line;
    std::vector<double> histogram;
};
MACDResult calculate_macd(const std::vector<double>& prices, 
                          int fast_period = 12, 
                          int slow_period = 26, 
                          int signal_period = 9);

// Расчет волатильности (Standard Deviation)
std::vector<double> calculate_volatility(const std::vector<double>& prices, int period);

// Оптимизированный поиск экстремумов (High/Low за период)
struct ExtremumResult {
    std::vector<double> highs;
    std::vector<double> lows;
};
ExtremumResult find_extremums(const std::vector<Candle>& candles, int period);

} // namespace native
} // namespace market_monitor

#endif // INDICATORS_H
