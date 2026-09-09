#ifndef DETECTOR_H
#define DETECTOR_H

#include <vector>
#include <string>
#include <map>

namespace market_monitor {
namespace native {

// Результат сравнения данных
struct ChangeResult {
    bool has_changes;
    std::vector<std::string> changed_fields;
    double similarity_score; // 0.0 - 1.0 (1.0 = идентичны)
    std::string change_type; // "primitive", "dictionary", "list", "complex"
};

// Быстрое сравнение числовых массивов с порогом
ChangeResult compare_numeric_arrays(const std::vector<double>& old_data,
                                    const std::vector<double>& new_data,
                                    double threshold = 0.001);

// Сравнение словарей (ключ-значение)
ChangeResult compare_dictionaries(const std::map<std::string, double>& old_dict,
                                  const std::map<std::string, double>& new_dict,
                                  double threshold = 0.001);

// Обнаружение аномалий в временных рядах
struct AnomalyResult {
    bool is_anomaly;
    double z_score;
    double deviation_percent;
    std::string anomaly_type; // "spike", "drop", "volatility"
};
AnomalyResult detect_anomaly(const std::vector<double>& history,
                             double current_value,
                             int lookback_period = 20,
                             double z_threshold = 3.0);

// Расчет процента изменения
double calculate_change_percent(double old_value, double new_value);

// Поиск паттернов в данных (разворот, пробой, флэт)
enum class PatternType {
    REVERSAL_UP,
    REVERSAL_DOWN,
    BREAKOUT_UP,
    BREAKOUT_DOWN,
    RANGE_BOUND,
    TRENDING_UP,
    TRENDING_DOWN,
    UNKNOWN
};

struct PatternResult {
    PatternType pattern;
    double confidence; // 0.0 - 1.0
    std::string description;
};
PatternResult detect_pattern(const std::vector<double>& prices,
                             const std::vector<double>& volumes,
                             int lookback_period = 14);

} // namespace native
} // namespace market_monitor

#endif // DETECTOR_H
