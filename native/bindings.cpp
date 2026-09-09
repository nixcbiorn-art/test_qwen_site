#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include "indicators.cpp"
#include "detector.cpp"

namespace py = pybind11;

PYBIND11_MODULE(market_native, m) {
    m.doc() = "High-performance C++ module for financial market analysis";

    // Indicators
    m.def("calculate_sma", &market_native::calculate_sma, 
          "Calculate Simple Moving Average",
          py::arg("prices"), py::arg("period"));
    
    m.def("calculate_ema", &market_native::calculate_ema, 
          "Calculate Exponential Moving Average",
          py::arg("prices"), py::arg("period"));
    
    m.def("calculate_rsi", &market_native::calculate_rsi, 
          "Calculate Relative Strength Index",
          py::arg("prices"), py::arg("period") = 14);
    
    // MACD Result struct binding
    py::class_<market_native::MACDResult>(m, "MACDResult")
        .def_readwrite("macd_line", &market_native::MACDResult::macd_line)
        .def_readwrite("signal_line", &market_native::MACDResult::signal_line)
        .def_readwrite("histogram", &market_native::MACDResult::histogram);
    
    m.def("calculate_macd", &market_native::calculate_macd, 
          "Calculate MACD indicator",
          py::arg("prices"), 
          py::arg("fast_period") = 12,
          py::arg("slow_period") = 26,
          py::arg("signal_period") = 9);

    // Detector
    py::class_<market_native::ChangeReport>(m, "ChangeReport")
        .def_readwrite("added_count", &market_native::ChangeReport::added_count)
        .def_readwrite("removed_count", &market_native::ChangeReport::removed_count)
        .def_readwrite("modified_count", &market_native::ChangeReport::modified_count)
        .def_readwrite("diff_score", &market_native::ChangeReport::diff_score);
    
    m.def("detect_numeric_changes", &market_native::detect_numeric_changes, 
          "Detect changes in numeric data snapshots",
          py::arg("old_data"), py::arg("new_data"), py::arg("threshold") = 0.001);
    
    m.def("detect_id_changes", &market_native::detect_id_changes, 
          "Detect changes in ID lists",
          py::arg("old_ids"), py::arg("new_ids"));
    
    m.def("detect_spike", &market_native::detect_spike, 
          "Detect sudden price spikes",
          py::arg("prices"), py::arg("lookback") = 5, py::arg("multiplier") = 3.0);
}
