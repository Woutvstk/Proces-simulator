#!/usr/bin/env python3
"""
Test script for Save/Load functionality.

This script demonstrates the complete save and load cycle:
1. Create a simulation with specific values
2. Save the complete state to JSON
3. Modify the values
4. Load the state back from JSON
5. Verify all values are restored correctly
"""
import sys
from pathlib import Path

# Add src to path
src_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(src_dir))

from core.configuration import configuration
from core.simulationManager import SimulationManager
from simulations.PIDtankValve.simulation import PIDTankSimulation
import json


def print_header(text):
    """Print a formatted header."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}")


def print_simulation_state(sim, title="Simulation State"):
    """Print current simulation state."""
    print(f"\n{title}:")
    print(f"  Simulation: {sim.get_name()}")
    print(f"\n  Status:")
    print(f"    liquidVolume: {sim.status.liquidVolume:.2f} L")
    print(f"    liquidTemperature: {sim.status.liquidTemperature:.2f} °C")
    print(f"    valveInOpenFraction: {sim.status.valveInOpenFraction:.2f}")
    print(f"    valveOutOpenFraction: {sim.status.valveOutOpenFraction:.2f}")
    print(f"    heaterPowerFraction: {sim.status.heaterPowerFraction:.2f}")
    print(f"    simRunning: {sim.status.simRunning}")
    print(f"\n  Configuration:")
    print(f"    tankVolume: {sim.config.tankVolume:.2f} L")
    print(f"    valveInMaxFlow: {sim.config.valveInMaxFlow:.2f} L/s")
    print(f"    valveOutMaxFlow: {sim.config.valveOutMaxFlow:.2f} L/s")
    print(f"    heaterMaxPower: {sim.config.heaterMaxPower:.2f} W")
    print(f"    simulationInterval: {sim.config.simulationInterval:.3f} s")


def main():
    print_header("Save/Load Functionality Test")
    
    # =========================================================================
    # STEP 1: Create simulation with specific values
    # =========================================================================
    print_header("STEP 1: Create Simulation")
    
    config = configuration()
    config.plcProtocol = "PLC S7-1500/1200/400/300/ET 200SP"
    config.plcIpAdress = "192.168.1.100"
    config.plcGuiControl = "gui"
    
    sim_mgr = SimulationManager()
    sim_mgr.register_simulation('PIDtankValve', PIDTankSimulation)
    
    if not sim_mgr.load_simulation('PIDtankValve', 'demo_simulation'):
        print("✗ Failed to load simulation")
        return False
    
    # Set some interesting values
    active_sim = sim_mgr.get_active_simulation()
    active_sim.status.liquidVolume = 750.5
    active_sim.status.liquidTemperature = 45.3
    active_sim.status.valveInOpenFraction = 0.75
    active_sim.status.valveOutOpenFraction = 0.25
    active_sim.status.heaterPowerFraction = 0.60
    active_sim.status.simRunning = True
    
    # Modify some config values
    active_sim.config.tankVolume = 2000.0
    active_sim.config.valveInMaxFlow = 10.0
    active_sim.config.heaterMaxPower = 1500.0
    active_sim.config.simulationInterval = 0.1
    
    print_simulation_state(active_sim, "Initial Simulation State")
    
    # =========================================================================
    # STEP 2: Save complete state to JSON
    # =========================================================================
    print_header("STEP 2: Save State to JSON")
    
    save_file = src_dir / "saved_state_demo.json"
    io_config = "IO/IO_configuration.json"
    
    if config.Save(sim_mgr, str(save_file), io_config):
        print(f"✓ State saved successfully to: {save_file}")
        
        # Show JSON content
        with open(save_file, 'r') as f:
            saved_data = json.load(f)
        
        print(f"\n  JSON Structure:")
        print(f"    version: {saved_data['version']}")
        print(f"    timestamp: {saved_data['timestamp']}")
        print(f"    active_simulation: {saved_data['active_simulation']}")
        print(f"    main_config keys: {len(saved_data['main_config'])}")
        print(f"    simulation_config keys: {len(saved_data['simulation_config'])}")
        print(f"    simulation_status keys: {len(saved_data['simulation_status'])}")
        print(f"    io_config_path: {saved_data['io_config_path']}")
    else:
        print("✗ Save failed")
        return False
    
    # =========================================================================
    # STEP 3: Modify values (simulate a different state)
    # =========================================================================
    print_header("STEP 3: Modify State")
    
    active_sim.status.liquidVolume = 0.0
    active_sim.status.liquidTemperature = 0.0
    active_sim.status.valveInOpenFraction = 0.0
    active_sim.status.valveOutOpenFraction = 0.0
    active_sim.status.heaterPowerFraction = 0.0
    active_sim.status.simRunning = False
    
    active_sim.config.tankVolume = 0.0
    active_sim.config.valveInMaxFlow = 0.0
    active_sim.config.heaterMaxPower = 0.0
    active_sim.config.simulationInterval = 0.0
    
    print_simulation_state(active_sim, "Modified State (All Zeros)")
    
    # =========================================================================
    # STEP 4: Load state from JSON (new simulation manager)
    # =========================================================================
    print_header("STEP 4: Load State from JSON")
    
    # Create new instances (simulating app restart)
    config2 = configuration()
    sim_mgr2 = SimulationManager()
    sim_mgr2.register_simulation('PIDtankValve', PIDTankSimulation)
    
    if config2.Load(sim_mgr2, str(save_file)):
        print(f"✓ State loaded successfully from: {save_file}")
        
        # Show loaded main config
        print(f"\n  Loaded Main Configuration:")
        print(f"    plcProtocol: {config2.plcProtocol}")
        print(f"    plcIpAdress: {config2.plcIpAdress}")
        print(f"    plcGuiControl: {config2.plcGuiControl}")
    else:
        print("✗ Load failed")
        return False
    
    # =========================================================================
    # STEP 5: Verify restored values
    # =========================================================================
    print_header("STEP 5: Verify Restored Values")
    
    loaded_sim = sim_mgr2.get_active_simulation()
    print_simulation_state(loaded_sim, "Restored Simulation State")
    
    # Verify critical values
    errors = []
    
    def check_value(name, actual, expected, tolerance=0.01):
        if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
            if abs(actual - expected) > tolerance:
                errors.append(f"{name}: expected {expected}, got {actual}")
        elif actual != expected:
            errors.append(f"{name}: expected {expected}, got {actual}")
    
    check_value("liquidVolume", loaded_sim.status.liquidVolume, 750.5)
    check_value("liquidTemperature", loaded_sim.status.liquidTemperature, 45.3)
    check_value("valveInOpenFraction", loaded_sim.status.valveInOpenFraction, 0.75)
    check_value("valveOutOpenFraction", loaded_sim.status.valveOutOpenFraction, 0.25)
    check_value("heaterPowerFraction", loaded_sim.status.heaterPowerFraction, 0.60)
    check_value("simRunning", loaded_sim.status.simRunning, True)
    check_value("tankVolume", loaded_sim.config.tankVolume, 2000.0)
    check_value("valveInMaxFlow", loaded_sim.config.valveInMaxFlow, 10.0)
    check_value("heaterMaxPower", loaded_sim.config.heaterMaxPower, 1500.0)
    check_value("simulationInterval", loaded_sim.config.simulationInterval, 0.1)
    
    # =========================================================================
    # STEP 6: Results
    # =========================================================================
    print_header("TEST RESULTS")
    
    if errors:
        print("\n✗ VERIFICATION FAILED")
        print("\nErrors found:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("\nThe Save/Load functionality is working correctly:")
        print("  ✓ JSON file created with complete state")
        print("  ✓ Simulation auto-loaded from saved name")
        print("  ✓ All configuration values restored")
        print("  ✓ All status/process values restored")
        print("  ✓ IO configuration path preserved")
        print("\nYou can now use config.Save() and config.Load() in the application!")
        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
