import math
import datetime
from config import Config

def get_seasonal_lux_average():
    """
    Returns an estimated average lux value for Northern Italy
    based on the current month.
    """
    month = datetime.datetime.now().month

    # Mapping months to average indoor/ambient lux values
    # Winter: ~250, Spring/Fall: ~450, Summer: ~600
    # -100 for all months
    seasonal_averages = Config.get('window.light_average', {
        12: 150, 1: 150, 2: 200,  # Winter
        3: 300, 4: 400, 5: 450,   # Spring
        6: 500, 7: 500, 8: 500,   # Summer
        9: 400, 10: 300, 11: 200  # Fall
    })

    return seasonal_averages.get(str(month), 400)

def convert_lux_to_range(lux_input, lux_average=0, lux_max=15000, use_logarithmic=False):
    """
    Normalizes a lux reading into a scale from -128 to 128.

    Args:
        lux_input (float): Current sensor reading.
        lux_average (float): Reference value (0 in the output domain).
        lux_max (float): Maximum expected value (128 in the output domain).
        use_logarithmic (bool): If True, uses a logarithmic scale to mimic human perception.
    """
    if lux_average == 0:
        lux_average = get_seasonal_lux_average()

    # 1. Constrain input to [0.1, lux_max] to avoid log(0) errors
    lux_input = max(0.1, min(lux_input, lux_max))
    lux_average = max(0.1, lux_average)

    # --- LOGARITHMIC MAPPING ---
    if use_logarithmic:
        # We calculate the log of input, average and max
        log_input = math.log10(lux_input)
        log_avg = math.log10(lux_average)
        log_max = math.log10(lux_max)
        log_min = math.log10(0.1) # Representing "darkness" floor

        if log_input < log_avg:
            # Map [log_min, log_avg] -> [-128, 0]
            result = ((log_input - log_avg) / (log_avg - log_min)) * 128
        else:
            # Map [log_avg, log_max] -> [0, 128]
            result = ((log_input - log_avg) / (log_max - log_avg)) * 128

    # --- LINEAR MAPPING ---
    else:
        if lux_input < lux_average:
            # Map [0, lux_average] -> [-128, 0]
            result = (lux_input / lux_average) * 128 - 128
        else:
            # Map [lux_average, lux_max] -> [0, 128]
            result = ((lux_input - lux_average) / (lux_max - lux_average)) * 128

    return int(result)
