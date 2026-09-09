#include "detector.h"
#include <cmath>
#include <algorithm>
#include <numeric>
#include <set>

namespace market_monitor {
namespace native {

// Вспомогательная функция для расчета среднего и стандартного отклонения
static void calculate_stats(const std::vector<double>& data, 
                            double& mean, 
                            double& stddev) {
    if (data.empty()) {
        mean = 0.0;
        stddev = 0.0;
        return;
    }
    
    mean = std::accumulate(data.begin(), data.end(), 0.0) / data.size();
    
    double variance_sum = 0.0;
    for (double val : data) {
        double diff = val - mean;
        variance_sum += diff * diff;
    }
    stddev = std::sqrt(variance_sum / data.size());
}

ChangeResult compare_numeric_arrays(const std::vector<double>& old_data,
                                    const std::vector<double>& new_data,
                                    double threshold) {
    ChangeResult result;
    result.has_changes = false;
    result.similarity_score = 1.0;
    result.change_type = "numeric_array";

    if (old_data.size() != new_data.size()) {
        result.has_changes = true;
        result.changed_fields.push_back("size");
        result.similarity_score = 0.0;
        return result;
    }

    if (old_data.empty()) {
        return result;
    }

    int changed_count = 0;
    double total_diff = 0.0;

    for (size_t i = 0; i < old_data.size(); ++i) {
        double old_val = old_data[i];
        double new_val = new_data[i];
        
        if (old_val == 0.0) {
            if (new_val != 0.0) {
                changed_count++;
                result.changed_fields.push_back("index_" + std::to_string(i));
            }
        } else {
            double rel_diff = std::abs((new_val - old_val) / old_val);
            if (rel_diff > threshold) {
                changed_count++;
                if (result.changed_fields.size() < 10) { // Ограничим количество полей
                    result.changed_fields.push_back("index_" + std::to_string(i));
                }
                total_diff += rel_diff;
            }
        }
    }

    if (changed_count > 0) {
        result.has_changes = true;
        result.similarity_score = 1.0 - (static_cast<double>(changed_count) / old_data.size());
    }

    return result;
}

ChangeResult compare_dictionaries(const std::map<std::string, double>& old_dict,
                                  const std::map<std::string, double>& new_dict,
                                  double threshold) {
    ChangeResult result;
    result.has_changes = false;
    result.similarity_score = 1.0;
    result.change_type = "dictionary";

    std::set<std::string> all_keys;
    for (const auto& pair : old_dict) all_keys.insert(pair.first);
    for (const auto& pair : new_dict) all_keys.insert(pair.first);

    int changed_count = 0;
    int total_count = all_keys.size();

    for (const std::string& key : all_keys) {
        auto old_it = old_dict.find(key);
        auto new_it = new_dict.find(key);

        bool old_exists = (old_it != old_dict.end());
        bool new_exists = (new_it != new_dict.end());

        if (old_exists != new_exists) {
            changed_count++;
            result.changed_fields.push_back(key + " (added/removed)");
        } else if (old_exists && new_exists) {
            double old_val = old_it->second;
            double new_val = new_it->second;
            
            double diff = std::abs(new_val - old_val);
            double rel_diff = (old_val != 0.0) ? (diff / std::abs(old_val)) : diff;
            
            if (rel_diff > threshold) {
                changed_count++;
                if (result.changed_fields.size() < 10) {
                    result.changed_fields.push_back(key);
                }
            }
        }
    }

    if (changed_count > 0 && total_count > 0) {
        result.has_changes = true;
        result.similarity_score = 1.0 - (static_cast<double>(changed_count) / total_count);
    }

    return result;
}

AnomalyResult detect_anomaly(const std::vector<double>& history,
                             double current_value,
                             int lookback_period,
                             double z_threshold) {
    AnomalyResult result;
    result.is_anomaly = false;
    result.z_score = 0.0;
    result.deviation_percent = 0.0;
    result.anomaly_type = "none";

    if (history.empty()) {
        return result;
    }

    // Берем последние lookback_period значений
    size_t start_idx = (history.size() > static_cast<size_t>(lookback_period)) 
                       ? (history.size() - lookback_period) 
                       : 0;
    
    std::vector<double> recent_history(history.begin() + start_idx, history.end());
    
    double mean, stddev;
    calculate_stats(recent_history, mean, stddev);

    if (stddev == 0.0) {
        // Если нет вариации, проверяем точное совпадение
        result.is_anomaly = (current_value != mean);
        result.z_score = result.is_anomaly ? 999.0 : 0.0;
        result.deviation_percent = result.is_anomaly ? 100.0 : 0.0;
        result.anomaly_type = result.is_anomaly ? "spike" : "none";
        return result;
    }

    result.z_score = (current_value - mean) / stddev;
    result.deviation_percent = std::abs((current_value - mean) / mean) * 100.0;

    if (std::abs(result.z_score) > z_threshold) {
        result.is_anomaly = true;
        if (result.z_score > 0) {
            result.anomaly_type = "spike";
        } else {
            result.anomaly_type = "drop";
        }
    }

    return result;
}

double calculate_change_percent(double old_value, double new_value) {
    if (old_value == 0.0) {
        return (new_value == 0.0) ? 0.0 : 100.0;
    }
    return ((new_value - old_value) / std::abs(old_value)) * 100.0;
}

PatternResult detect_pattern(const std::vector<double>& prices,
                             const std::vector<double>& volumes,
                             int lookback_period) {
    PatternResult result;
    result.pattern = PatternType::UNKNOWN;
    result.confidence = 0.0;
    result.description = "Insufficient data";

    if (prices.size() < static_cast<size_t>(lookback_period)) {
        return result;
    }

    // Берем последние данные
    auto price_start = prices.end() - lookback_period;
    std::vector<double> recent_prices(price_start, prices.end());
    
    // Расчет тренда
    double first_price = recent_prices.front();
    double last_price = recent_prices.back();
    double price_change = last_price - first_price;
    double price_change_pct = (first_price != 0.0) ? (price_change / first_price) : 0.0;

    // Расчет волатильности
    double mean, stddev;
    calculate_stats(recent_prices, mean, stddev);
    double volatility = (mean != 0.0) ? (stddev / mean) : 0.0;

    // Анализ объемов
    double avg_volume = 0.0;
    if (!volumes.empty() && volumes.size() >= static_cast<size_t>(lookback_period)) {
        auto vol_start = volumes.end() - lookback_period;
        std::vector<double> recent_vols(vol_start, volumes.end());
        avg_volume = std::accumulate(recent_vols.begin(), recent_vols.end(), 0.0) / recent_vols.size();
    }

    double current_volume = volumes.empty() ? 0.0 : volumes.back();
    bool volume_spike = (avg_volume > 0.0) && (current_volume > avg_volume * 1.5);

    // Определение паттерна
    if (std::abs(price_change_pct) < 0.02 && volatility < 0.03) {
        result.pattern = PatternType::RANGE_BOUND;
        result.confidence = 0.8;
        result.description = "Price moving in range (flat)";
    } else if (price_change_pct > 0.05) {
        if (volume_spike) {
            result.pattern = PatternType::BREAKOUT_UP;
            result.confidence = 0.9;
            result.description = "Strong upward breakout with volume";
        } else {
            result.pattern = PatternType::TRENDING_UP;
            result.confidence = 0.7;
            result.description = "Upward trend";
        }
    } else if (price_change_pct < -0.05) {
        if (volume_spike) {
            result.pattern = PatternType::BREAKOUT_DOWN;
            result.confidence = 0.9;
            result.description = "Strong downward breakout with volume";
        } else {
            result.pattern = PatternType::TRENDING_DOWN;
            result.confidence = 0.7;
            result.description = "Downward trend";
        }
    } else if (std::abs(price_change_pct) >= 0.03 && volatility > 0.05) {
        // Проверка на разворот
        bool is_reversal_up = (prices[prices.size() - lookback_period] > prices[prices.size() - lookback_period/2]) 
                              && (last_price > prices[prices.size() - lookback_period/2]);
        bool is_reversal_down = (prices[prices.size() - lookback_period] < prices[prices.size() - lookback_period/2]) 
                                && (last_price < prices[prices.size() - lookback_period/2]);
        
        if (is_reversal_up) {
            result.pattern = PatternType::REVERSAL_UP;
            result.confidence = 0.75;
            result.description = "Potential upward reversal";
        } else if (is_reversal_down) {
            result.pattern = PatternType::REVERSAL_DOWN;
            result.confidence = 0.75;
            result.description = "Potential downward reversal";
        }
    }

    return result;
}

} // namespace native
} // namespace market_monitor
