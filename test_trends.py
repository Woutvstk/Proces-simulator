#!/usr/bin/env python3
"""Quick test to verify trend windows work with updated parameter handling"""

from PyQt5.QtWidgets import QApplication
from gui.trendGraphWindow import TrendGraphManager
import sys
sys.path.insert(0, 'src')


# Create Qt application (required for GUI windows)
app = QApplication(sys.argv)

# Create trend manager
trend_manager = TrendGraphManager()

# Test 1: Show temperature trend window
print("Test 1: Creating temperature trend window...")
temp_window = trend_manager.show_temperature_trend(boiling_temp=100.0)
print(f"Temperature window created: {temp_window is not None}")

# Test 2: Show level trend window
print("\nTest 2: Creating level trend window...")
level_window = trend_manager.show_level_trend(y_max=200)
print(f"Level window created: {level_window is not None}")

# Test 3: Add data with new parameter names
print("\nTest 3: Adding temperature data with new parameter names...")
try:
    trend_manager.add_temperature(
        pv_value=50.0, setpoint_value=75.0, output_value=0.8)
    print("✓ add_temperature with new parameter names works")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 4: Add level data with new parameter names
print("\nTest 4: Adding level data with new parameter names...")
try:
    trend_manager.add_level(
        pv_value=100.0, setpoint_value=0.5, output_value=0.3)
    print("✓ add_level with new parameter names works")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 5: Add data with old parameter names (backwards compatibility)
print("\nTest 5: Adding temperature data with old parameter names...")
try:
    trend_manager.add_temperature(value=55.0, power_fraction=0.85)
    print("✓ add_temperature with old parameter names works (backwards compatible)")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 6: Add level data with old parameter names (backwards compatibility)
print("\nTest 6: Adding level data with old parameter names...")
try:
    trend_manager.add_level(
        value=105.0, valve_in_fraction=0.5, valve_out_fraction=0.3)
    print("✓ add_level with old parameter names works (backwards compatible)")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 7: Verify deques are being populated
print("\nTest 7: Verifying data collection...")
if temp_window:
    print(f"Temperature deque size: {len(temp_window.all_temperatures)}")
    print(f"Timestamps deque size: {len(temp_window.timestamps)}")

if level_window:
    print(f"Level deque size: {len(level_window.all_levels)}")
    print(f"Level timestamps deque size: {len(level_window.timestamps)}")

print("\n✓ All tests completed!")
print("\nNote: Windows will stay open. Close them manually to exit.")

# Keep windows open for manual inspection
sys.exit(app.exec_())
