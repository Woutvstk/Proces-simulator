import clr
clr.AddReference(r"C:\Program Files (x86)\Common Files\Siemens\PLCSIMADV\API\7.0\Siemens.Simatic.Simulation.Runtime.Api.x64.dll")
from Siemens.Simatic.Simulation.Runtime import SimulationRuntimeManager

# Verkrijg manager
manager = SimulationRuntimeManager()

# Verkrijg lijst van PLC's in de simulatie
plc_list = manager.GetPlcList()
print(f"Aantal PLC's in simulatie: {plc_list.Count}")

# Kies de eerste PLC
plc = plc_list[0]  # ISimulationRuntime object

# Start PLC als hij nog niet loopt
if not plc.Running:
    plc.Start()
    
# PEEK equivalent: lees byte 511 van output
value = plc.ReadByte(0x82, 0, 511)
print(f"Originele Q511: {value}")

# POKE equivalent: schrijf waarde terug
plc.WriteByte(0x82, 0, 511, (value+1)%256)
print(f"Nieuwe Q511: {(value+1)%256}")
