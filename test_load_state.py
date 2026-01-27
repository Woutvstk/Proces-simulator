#!/usr/bin/env python
import sys
sys.path.insert(0, 'src')
from core.load_save import load_application_state
from core.configuration import configuration
from core.simulationManager import SimulationManager
from simulations.PIDtankValve.simulation import PIDTankSimulation
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

mainConfig = configuration()
simulationManager = SimulationManager()
simulationManager.register_simulation('PIDtankValve', PIDTankSimulation)

logger.info('Loading state from testSaveStateV10.json...')
success = load_application_state(
    main_config=mainConfig,
    simulation_manager=simulationManager,
    io_config_output_path='src/IO/IO_configuration_loaded.json',
    load_file_path='c:/Users/jarne/Downloads/testSaveStateV10.json'
)

if success:
    sim = simulationManager.get_active_simulation()
    if sim:
        print('\n--- CONFIG LOADED ---')
        print(f'ambientTemp: {sim.config.ambientTemp}')
        print(f'heaterMaxPower: {sim.config.heaterMaxPower}')
        print(f'tankHeatLoss: {sim.config.tankHeatLoss}')
        print(f'liquidVolumeTimeDelay: {getattr(sim.config, "liquidVolumeTimeDelay", "NOT FOUND")}')
        print(f'liquidTempTimeDelay: {getattr(sim.config, "liquidTempTimeDelay", "NOT FOUND")}')
        print(f'liquidSpecificHeatCapacity: {sim.config.liquidSpecificHeatCapacity}')
        print(f'liquidSpecificWeight: {sim.config.liquidSpecificWeight}')
        print(f'liquidBoilingTemp: {sim.config.liquidBoilingTemp}')
        print('\n--- STATUS LOADED ---')
        print(f'tankColor: {sim.status.tankColor}')
        print(f'displayLevelSwitches: {sim.status.displayLevelSwitches}')
        print(f'displayTemperature: {sim.status.displayTemperature}')
        print('\nAll values loaded successfully from state file!')
else:
    print('Load failed')
