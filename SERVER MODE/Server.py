# Server.py
from pyModbusTCP.server import ModbusServer, DataBank
from time import sleep
from array import array

# arrays voor inputs/outputs
DI = array('I', [0]*16)  # Digitale inputs (server schrijft)
DO = array('I', [0]*16)  # Digitale outputs (server leest)
AI = array('I', [0]*16)  # Analoge inputs (server schrijft)
AO = array('I', [0]*16)  # Analoge outputs (server leest)

# Maak databank
databank = DataBank()

def StartServer(ip="0.0.0.0", port=502, no_block=True):#"""Start Modbus server"""  
    global server
    server = ModbusServer(ip, port=port, no_block=no_block, data_bank=databank)
    server.start()
    print(f"Modbus server gestart op {ip}:{port}")


def StopServer():#"""Stop Modbus server""" 
    global server
    if server:
        server.stop()
        print("Modbus server gestopt")


def SetDI(index, value):
    """Schrijf een digitale input (0/1) in de databank"""
    global DI, databank
    if 0 <= index < len(DI):
        DI[index] = int(bool(value))
        databank.set_discrete_inputs(index, [DI[index]])


def SetAI(index, value):
    """Schrijf een analoge input (0-65535) in de databank"""
    global AI, databank
    if 0 <= index < len(AI):
        AI[index] = int(value) & 0xFFFF  # mask voor 16-bit waarde
        databank.set_input_registers(index, [AI[index]])


def update_databank(): #"""Update databank en arrays"""
    global DI, DO, AI, AO
    
    # --- Server leest DO van PLC (coils) ---
    coils = databank.get_coils(0, 16)
    if coils:
        for i, val in enumerate(coils):
            DO[i] = int(val)

    # --- Server leest AO van PLC (holding registers) ---
    regs = databank.get_holding_registers(0, 16)
    if regs:
        for i, val in enumerate(regs):
            AO[i] = val

    # Debug
    print(f"DI={list(DI)}")
    print(f"DO={list(DO)}")
    print(f"AI={list(AI)}")
    print(f"AO={list(AO)}")
    print("-"*50)




