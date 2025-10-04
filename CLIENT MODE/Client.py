# Client.py
('''
DI DO AI en AO zijn arrays die de eerst volgende digitale/analoge ingangen EN digitale/analoge uitgangen van de PLC zullen bevatten.
Om bv een digitale uitgang in te lezen van Q1.2 zal je in de main PLC-IO.DI[10] moeten lezen (1*8 + 2 = 10)

DI schrijft data naar de ingangen van de plc
DO leest de status van de PLC uitgangen
AI schrijft data naar de analoge ingangen van de plc
AO leest de status van de PLC analoge uitgangen
''')

from pymodbus.client import ModbusTcpClient
from array import array

# arrays voor inputs/outputs
DI = array('I', [0]*16)
DO = array('I', [0]*16)
AI = array('I', [0]*16)
AO = array('I', [0]*16)

client = None

def connect(ip="192.168.0.1", port=502):
    global client
    client = ModbusTcpClient(ip, port=port)
    if client.connect():
        print("Connected to Modbus server")
        reset_registers()  # reset bij opstart
        return True
    return False

def disconnect():
    global client
    if client:
        client.close()
                
def SetDI(index, value):
    """Schrijf een digitale input (0/1) in de databank"""
    global DI, databank
    if 0 <= index < len(DI):
        DI[index] = int(bool(value))
        client.write_register(index, value)
        
def SetAI(index, value):
    """Schrijf een analoge input (0-65535) in de databank"""
    global AI, databank
    if 0 <= index < len(AI):
        AI[index] = int(value) & 0xFFFF  # mask voor 16-bit waarde
        client.write_register(index+16, value)       
        
def reset_registers():
    """Reset alle DI, DO, AI en AO registers naar 0"""
    global DI, DO, AI, AO, client

    # Arrays op nul zetten
    for i in range(16):
        DI[i] = 0
        DO[i] = 0
        AI[i] = 0
        AO[i] = 0

    # DI / AI naar server schrijven
    if client is not None and client.is_socket_open():
        # DI registers (0-15)
        for i in range(16):
            client.write_register(i, DI[i])
        for i in range(16):
            client.write_register(i+16, AI[i])
         
def update():
    """Vul DI, DO, AI, AO arrays"""
    global DI, DO, AI, AO, client

# maak connectie als die er niet meer is
    if client is None or not client.is_socket_open():
        try:
            client.connect()
        except Exception as e:
            print("can't find PLC", e)
            return

    # coils (DO lezen)
    for i in range(0, 16):
        rr = client.read_coils(i, count=1)
        DO[i] = int(rr.bits[0]) if not rr.isError() else -1

    #DI_schrijven
    for i in range(0, 16):
        value = DI[i]
        rr = client.write_register(i, value)
    
    # AI terugschrijven    
    for i in range(16, 32):
        value = AI[i-16]
        client.write_register(i, value)
        
    # holding registers (AO lezen)
    for i in range(32, 48):
        rr = client.read_holding_registers(i, count=1)
        AO[i-32] = rr.registers[0] if not rr.isError() else -1


        
    # Debug
    print(f"DI={list(DI)}")
    print(f"DO={list(DO)}")
    print(f"AI={list(AI)}")
    print(f"AO={list(AO)}")
    print("-"*50)
