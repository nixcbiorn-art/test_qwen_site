#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include "../include/indicators.h"
#include "../include/detector.h"

namespace py = pybind11;

PYBIND11_MODULE(native_bindings, m) {
    m.doc() = "Native C++ bindings for MarketMonitor - High performance financial calculations";

    // === Индикаторы ===
    
    m.def("calculate_rsi", 
          &market_monitor::native::calculate_rsi,
          "Calculate RSI (Relative Strength Index)",
          py::arg("prices"), 
          py::arg("period") = 14);

    m.def("calculate_sma", 
          &market_monitor::native::calculate_sma,
          "Calculate SMA (Simple Moving Average)",
          py::arg("prices"), 
          py::arg("period"));

    m.def("calculate_ema", 
          &market_monitor::native::calculate_ema,
          "Calculate EMA (Exponential Moving Average)",
          py::arg("prices"), 
          py::arg("period"));

    py::class_<market_monitor::native::MACDResult>(m, "MACDResult")
        .def_readwrite("macd_line", &market_monitor::native::MACDResult::macd_line)
        .def_readwrite("signal_line", &market_monitor::native::MACDResult::signal_line)
        .def_readwrite("histogram", &market_monitor::native::MACDResult::histogram);

    m.def("calculate_macd", 
          &market_monitor::native::calculate_macd,
          "Calculate MACD (Moving Average Convergence Divergence)",
          py::arg("prices"),
          py::arg("fast_period") = 12,
          py::arg("slow_period") = 26,
          py::arg("signal_period") = 9);

    m.def("calculate_volatility", 
          &market_monitor::native::calculate_volatility,
          "Calculate volatility (standard deviation)",
          py::arg("prices"), 
          py::arg("period"));

    py::class_<market_monitor::native::Candle>(m, "Candle")
        .def(py::init<>())
        .def_readwrite("open", &market_monitor::native::Candle::open)
        .def_readwrite("high", &market_monitor::native::Candle::high)
        .def_readwrite("low", &market_monitor::native::Candle::low)
        .def_readwrite("close", &market_monitor::native::Candle::close)
        .def_readwrite("volume", &market_monitor::native::Candle::volume)
        .def_readwrite("timestamp", &market_monitor::native::Candle::timestamp);

    py::class_<market_monitor::native::ExtremumResult>(m, "ExtremumResult")
        .def(py::init<>())
        .def_readwrite("highs", &market_monitor::native::ExtremumResult::highs)
        .def_readwrite("lows", &market_monitor::native::ExtremumResult::lows);

    m.def("find_extremums", 
          &market_monitor::native::find_extremums,
          "Find high/low extremums over a period",
          py::arg("candles"), 
          py::arg("period"));

    // === Детектор ===

    py::class_<market_monitor::native::ChangeResult>(m, "ChangeResult")
        .def(py::init<>())
        .def_readwrite("has_changes", &market_monitor::native::ChangeResult::has_changes)
        .def_readwrite("changed_fields", &market_monitor::native::ChangeResult::changed_fields)
        .def_readwrite("similarity_score", &market_monitor::native::ChangeResult::similarity_score)
        .def_readwrite("change_type", &market_monitor::native::ChangeResult::change_type);

    m.def("compare_numeric_arrays", 
          &market_monitor::native::compare_numeric_arrays,
          "Compare numeric arrays with threshold",
          py::arg("old_data"),
          py::arg("new_data"),
          py::arg("threshold") = 0.001);

    m.def("compare_dictionaries", 
          &market_monitor::native::compare_dictionaries,
          "Compare dictionaries with threshold",
          py::arg("old_dict"),
          py::arg("new_dict"),
          py::arg("threshold") = 0.001);

    py::class_<market_monitor::native::AnomalyResult>(m, "AnomalyResult")
        .def(py::init<>())
        .def_readwrite("is_anomaly", &market_monitor::native::AnomalyResult::is_anomaly)
        .def_readwrite("z_score", &market_monitor::native::AnomalyResult::z_score)
        .def_readwrite("deviation_percent", &market_monitor::native::AnomalyResult::deviation_percent)
        .def_readwrite("anomaly_type", &market_monitor::native::AnomalyResult::anomaly_type);

    m.def("detect_anomaly", 
          &market_monitor::native::detect_anomaly,
          "Detect anomalies in time series",
          py::arg("history"),
          py::arg("current_value"),
          py::arg("lookback_period") = 20,
          py::arg("z_threshold") = 3.0);

    m.def("calculate_change_percent", 
          &market_monitor::native::calculate_change_percent,
          "Calculate percentage change between two values",
          py::arg("old_value"),
          py::arg("new_value"));

    py::enum_<market_monitor::native::PatternType>(m, "PatternType")
        .value("REVERSAL_UP", market_monitor::native::PatternType::REVERSAL_UP)
        .value("REVERSAL_DOWN", market_monitor::native::PatternType::REVERSAL_DOWN)
        .value("BREAKOUT_UP", market_monitor::native::PatternType::BREAKOUT_UP)
        .value("BREAKOUT_DOWN", market_monitor::native::PatternType::BREAKOUT_DOWN)
        .value("RANGE_BOUND", market_monitor::native::PatternType::RANGE_BOUND)
        .value("TRENDING_UP", market_monitor::native::PatternType::TRENDING_UP)
        .value("TRENDING_DOWN", market_monitor::native::PatternType::TRENDING_DOWN)
        .value("UNKNOWN", market_monitor::native::PatternType::UNKNOWN)
        .export_values();

    py::class_<market_monitor::native::PatternResult>(m, "PatternResult")
        .def(py::init<>())
        .def_readwrite("pattern", &market_monitor::native::PatternResult::pattern)
        .def_readwrite("confidence", &market_monitor::native::PatternResult::confidence)
        .def_readwrite("description", &market_monitor::native::PatternResult::description);

    m.def("detect_pattern", 
          &market_monitor::native::detect_pattern,
          "Detect patterns in price data",
          py::arg("prices"),
          py::arg("volumes"),
          py::arg("lookback_period") = 14);
}
