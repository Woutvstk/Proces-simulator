# mainClient.py
from time import sleep
import Client  # importeer je server module

try:
    Client.connect()  # server starten

    while True:
        Client.update()  # arrays bijwerken (schrijven en lezen PLC)

        '''voorbeeld, schrijf wat waarden naar DI en AI van de PLC'''
        Client.SetDI(0, 1)   # zet digitale input 0 op True (I0.0)
        Client.SetDI(15, 1)   # zet digitale input 0 op True (I1.7)
        Client.SetAI(0, 150)  # zet analoge input 0 op waarde 150 (QW2)
        Client.SetAI(15, 150)   # zet analoge input 15 op waarde 150 (QW32)
        '''voorbeeld, lees wat waarden van DO en AO van de PLC'''
       # Server.DO[1] /digitale output van PLC (Q0.1)
       # Server.AO[0] /analoge output van PLC (IW2)

        sleep(1)


except KeyboardInterrupt:
    Client.disconnect()
