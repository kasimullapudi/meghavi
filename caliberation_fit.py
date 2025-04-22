# calibrate_fit.py

import json
import numpy as np
from scipy.optimize import curve_fit

def model(area, a, b):
    return a * (area ** b)

with open("calibration.json", "r") as f:
    calib_data = json.load(f)

area_values = np.array([point["area"] for point in calib_data["data"]])
distance_values = np.array([point["distance"] for point in calib_data["data"]])

params, _ = curve_fit(model, area_values, distance_values)
a, b = params

predicted = model(area_values, a, b)
rmse = np.sqrt(np.mean((distance_values - predicted) ** 2))

print(f"a = {a}")
print(f"b = {b}")
print(f"RMSE = {rmse:.2f}")
