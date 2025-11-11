import logging
import snap7
import time 

 #https://medium.com/@biero-llagas/setup-exploit-and-harden-a-physical-ics-lab-s7comm-part2-e75ddf52ef70

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)
"""
Local Properties (Server)
TSAP: 02.00 (0x0200)
Connect with an Operator Panel (OP): true
Accept all connection requests: true

Remote Properties (Client)
TSAP: 03.00 (0x0300)
"""
plc = snap7.logo.Logo()

### <ip_address, tsap_snap7 (client) 03.00 = 0x0300, tsap_logo (server) 02.00 = 0x0200>
plc.connect("192.168.0.2", 0x0300, 0x0200)

if plc.get_connected():
    logger.info("connected")

### 64 memory bits M1-64
m1_8 = {'m1':'V1104.0','m2':'V1104.1','m3':'V1104.2','m4':'V1104.3','m5':'V1104.4','m6':'V1104.5','m7':'V1104.6','m8':'V1104.7'}
m9_16 = {'m9':'V1105.0','m10':'V1105.1','m11':'V1105.2','m12':'V1105.3','m13':'V1105.4','m14':'V1105.5','m15':'V1105.6','m16':'V1105.7'}
m17_24 = {'m17':'V1106.0','m18':'V1106.1','m19':'V1106.2','m20':'V1106.3','m21':'V1106.4','m22':'V1106.5','m23':'V1106.6','m24':'V1106.7'}
m25_32 = {'m25':'V1107.0','m26':'V1107.1','m27':'V1107.2','m28':'V1107.3','m29':'V1107.4','m30':'V1107.5','m31':'V1107.6','m32':'V1107.7'}
m33_40 = {'m33':'V1108.0','m34':'V1108.1','m35':'V1108.2','m36':'V1108.3','m37':'V1108.4','m38':'V1108.5','m39':'V1108.6','m40':'V1108.7'}
m41_48 = {'m41':'V1109.0','m42':'V1109.1','m43':'V1109.2','m44':'V1109.3','m45':'V1109.4','m46':'V1109.5','m47':'V1109.6','m48':'V1109.7'}
m49_56 = {'m49':'V1110.0','m50':'V1110.1','m51':'V1110.2','m52':'V1110.3','m53':'V1110.4','m54':'V1110.5','m55':'V1110.6','m56':'V1110.7'}
m57_64 = {'m57':'V1111.0','m58':'V1111.1','m59':'V1111.2','m60':'V1111.3','m61':'V1111.4','m62':'V1111.5','m63':'V1111.6','m64':'V1111.7'}

### 4 analog inputs AM1-4
am1_4 = {'am1':'VW1118','am2':'VW1120','am3':'VW1122','am4':'VW1124'}
### 8 analog outputs AQ1-8
aq1_8 = {'aq1':'VW1072','aq2':'VW1074','aq3':'VW1076','aq4':'VW1078','aq5':'VW1080','aq6':'VW1082','aq7':'VW1084','aq8':'VW1086'}

vm_address = m1_8['m1']
m1 = str(plc.read(vm_address))
print(f"M1: {m1}")

plc.write(vm_address, 1)
m1 = str(plc.read(vm_address))
print(f"M1: {m1}")

time.sleep(10) # sleep 10 seconds

plc.write(vm_address, 0) # set memory bit m1 to 0
m1 = str(plc.read(vm_address))
print(f"M1: {m1}")

time.sleep(5)

plc.write(m25_32['m29'], 1)

time.sleep(5)

plc.write(m25_32['m29'], 0) # write 0 to M29
m29 = str(plc.read(m25_32['m29']))
print(f"m29: {m29}")

time.sleep(5)

plc.write(am1_4['am1'], 250) # write 250 to AM1
aq1 = str(plc.read(aq1_8['aq1'])) # read output of AQ1
print(f"AQ1: {aq1}")

time.sleep(5)

### Trigger Q2 when analog value is 50
plc.write(am1_4['am1'], 50) # write 50 to AM1, ex. analog diffierential trigger with diffierential of 5 %
q2 = plc.read('V1064.1')
print(f"Q2: {q2}")

time.sleep(5)

plc.write(am1_4['am1'], 0) # write 0 to AM1
aq1 = str(plc.read(aq1_8['aq1'])) # read output of AQ1
print(f"AQ1: {aq1}")
q1 = plc.read('V1064.0')
print(f"Q1: {q1}")
q2 = plc.read('V1064.1')
print(f"Q2: {q2}")
