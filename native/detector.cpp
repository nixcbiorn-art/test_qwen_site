#include <vector>
#include <algorithm>
#include <cmath>

namespace market_native {

struct ChangeReport {
    int added_count;
    int removed_count;
    int modified_count;
    double diff_score; // 0.0 to 1.0 (1.0 = completely different)
};

// Detect changes between two snapshots of numeric data
ChangeReport detect_numeric_changes(const std::vector<double>& old_data, 
                                    const std::vector<double>& new_data,
                                    double threshold = 0.001) {
    ChangeReport report{0, 0, 0, 0.0};
    
    size_t old_size = old_data.size();
    size_t new_size = new_data.size();
    
    // Count additions and removals based on size difference
    if (new_size > old_size) {
        report.added_count = static_cast<int>(new_size - old_size);
    } else if (old_size > new_size) {
        report.removed_count = static_cast<int>(old_size - new_size);
    }
    
    // Compare overlapping elements
    size_t compare_len = std::min(old_size, new_size);
    int modified = 0;
    double total_diff = 0.0;
    
    for (size_t i = 0; i < compare_len; ++i) {
        double diff = std::abs(new_data[i] - old_data[i]);
        double relative_diff = (old_data[i] != 0.0) ? 
                               diff / std::abs(old_data[i]) : diff;
        
        if (relative_diff > threshold) {
            modified++;
            total_diff += relative_diff;
        }
    }
    
    report.modified_count = modified;
    
    // Calculate overall difference score
    if (compare_len > 0) {
        report.diff_score = total_diff / compare_len;
        // Normalize to 0-1 range (cap at 1.0)
        if (report.diff_score > 1.0) report.diff_score = 1.0;
    }
    
    // If sizes differ significantly, increase diff score
    if (old_size != new_size && old_size > 0) {
        double size_factor = std::abs(static_cast<double>(new_size) - old_size) / old_size;
        report.diff_score = std::min(1.0, (report.diff_score + size_factor) / 2.0);
    }
    
    return report;
}

// Detect changes in string identifiers (e.g., stock symbols, IDs)
ChangeReport detect_id_changes(const std::vector<std::string>& old_ids,
                               const std::vector<std::string>& new_ids) {
    ChangeReport report{0, 0, 0, 0.0};
    
    std::vector<std::string> old_sorted = old_ids;
    std::vector<std::string> new_sorted = new_ids;
    std::sort(old_sorted.begin(), old_sorted.end());
    std::sort(new_sorted.begin(), new_sorted.end());
    
    // Find added IDs
    for (const auto& id : new_sorted) {
        if (std::find(old_sorted.begin(), old_sorted.end(), id) == old_sorted.end()) {
            report.added_count++;
        }
    }
    
    // Find removed IDs
    for (const auto& id : old_sorted) {
        if (std::find(new_sorted.begin(), new_sorted.end(), id) == new_sorted.end()) {
            report.removed_count++;
        }
    }
    
    // No "modified" for IDs, only added/removed
    report.modified_count = 0;
    
    // Diff score based on Jaccard distance
    size_t intersection = old_sorted.size() + new_sorted.size() - 
                          (report.added_count + report.removed_count);
    size_t union_size = old_sorted.size() + report.added_count;
    
    if (union_size > 0) {
        report.diff_score = 1.0 - (static_cast<double>(intersection) / union_size);
    } else {
        report.diff_score = (old_sorted.empty() && new_sorted.empty()) ? 0.0 : 1.0;
    }
    
    return report;
}

// Fast pattern detection: check for sudden spikes
bool detect_spike(const std::vector<double>& prices, int lookback = 5, double multiplier = 3.0) {
    if (prices.size() < static_cast<size_t>(lookback) + 1) {
        return false;
    }
    
    double current = prices.back();
    double sum = 0.0;
    double sq_sum = 0.0;
    
    // Calculate mean and std dev of lookback period
    for (int i = 1; i <= lookback; ++i) {
        double val = prices[prices.size() - i];
        sum += val;
        sq_sum += val * val;
    }
    
    double mean = sum / lookback;
    double variance = (sq_sum / lookback) - (mean * mean);
    double std_dev = std::sqrt(variance);
    
    if (std_dev == 0.0) return false;
    
    double z_score = std::abs(current - mean) / std_dev;
    
    return z_score > multiplier;
}

} // namespace market_native
