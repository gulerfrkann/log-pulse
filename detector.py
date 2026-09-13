from collections import defaultdict, deque

class PredictiveAnomalyDetector:
    def __init__(self, window_size: int = 5, slope_threshold: float = 1.2, mem_critical_threshold: float = 75.0):
        self.window_size = window_size
        self.slope_threshold = slope_threshold
        self.mem_critical_threshold = mem_critical_threshold
        # Her servis için bağımsız kayan pencere
        self.windows = defaultdict(lambda: deque(maxlen=window_size))

    def calculate_slope(self, values: list) -> float:
        n = len(values)
        if n < 2:
            return 0.0
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        return numerator / denominator if denominator != 0 else 0.0

    def evaluate_telemetry(self, service: str, memory_usage: float) -> dict:
        """
        Gelen bellek metriğini pencereye ekler ve sızıntı eğilimini analiz eder.
        """
        window = self.windows[service]
        window.append(memory_usage)

        if len(window) < self.window_size:
            return {"is_anomaly": False, "reason": "Yetersiz pencere verisi"}

        slope = self.calculate_slope(list(window))
        current_mem = window[-1]

        # Pozitif eğim ve kritik seviye kontrolü
        if slope >= self.slope_threshold and current_mem >= self.mem_critical_threshold:
            # Tahmini OOM süresi (100%'e kaç adımda ulaşır?)
            remaining_capacity = max(0.0, 100.0 - current_mem)
            steps_to_oom = round(remaining_capacity / slope, 1) if slope > 0 else 999.0

            return {
                "is_anomaly": True,
                "slope": round(slope, 2),
                "current_memory": current_mem,
                "steps_to_oom": steps_to_oom,
                "history": list(window)
            }

        return {"is_anomaly": False, "slope": round(slope, 2)}