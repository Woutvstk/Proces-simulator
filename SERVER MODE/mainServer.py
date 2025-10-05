# mainServer.py
from time import sleep
import Server  # importeer je server module

try:
    Server.StartServer()  # server starten

    while True:
        Server.update_databank()  # arrays bijwerken (schrijven en lezen PLC)

        '''voorbeeld, schrijf wat waarden naar DI en AI van de PLC'''
        Server.SetDI(0, 1)   # zet digitale input 0 op True (I0.0)
        Server.SetDI(5, 1)   # zet digitale input 0 op True (I0.0)
        Server.SetAI(3, 150)  # zet analoge input 3 op waarde 123 (QW6)

        '''voorbeeld, lees wat waarden van DO en AO van de PLC'''
       # Server.DO[1] /digitale output van PLC (Q0.1)
       # Server.AO[0] /analoge output van PLC (IW0)

        sleep(1)
except KeyboardInterrupt:
    Server.StopServer()
