// Detection triggers for async LLM analysis
// =====================================

// Volume spike detection (3x average)
// NATR spike detection (2x average) - from correlation study, NATR is predictive
// Oscillator extreme detection (RSI > 70 or < 30)
// Gap up/down detection (> 2%)

// Each trigger writes to alert_queue and sends Discord notification