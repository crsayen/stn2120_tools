from __future__ import print_function
import queue, socket, time, threading
import serial, sys, signal, time
import Adafruit_BBIO.UART as UART
import pysnooper

udpPort = int(sys.argv[2]) if len(sys.argv) > 2 else 13131
s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind(('0.0.0.0',udpPort))
print("\n\nlistening on port " + str(udpPort)+"...")
#while True:
#    initbytes,address = s.recvfrom(64)
#    print(initbytes.decode('utf-8'))
#    if initbytes == b'init':
#        break
    
awaitingPrompt = False
baudrate = 9600 # this must be 9600 initially
STNBAUD = 115200
SEND_TIME_OUT = 0.05
address = '0.0.0.0'
uartRx_threadQueue = queue.Queue()
udpRx_threadQueue = queue.Queue()
uartTx_threadQueue = queue.Queue()
udpTx_threadQueue = queue.Queue()


#@pysnooper.snoop('/var/lib/cloud9/stn2120_tools/log/file.log')
def setBaud(ser, rate):
    time.sleep(.1)
    baudrate = rate
    rate = 'ST SBR ' + str(rate)
    sendSerial(ser, 'ATVR')
    sendSerial(ser, 'ST BRT 300')
    sendSerial(ser, 'ST SBR 115200')
    sendSerial(ser, 'ST WBR')
    ser = serial.Serial(port = "/dev/ttyO1",baudrate=115200)
    sendSerial(ser, 'ATI')
    return ser

#@pysnooper.snoop('/var/lib/cloud9/stn2120_tools/log/file.log')
def sendSerial(ser, msg):
    start = time.time()
    global awaitingPrompt
    while awaitingPrompt:
        curr = time.time()
        if curr - start > SEND_TIME_OUT:
            break
    if not ser.isOpen():
        ser.open()
    ser.flushOutput()
    ser.write(bytes(msg + '\r', 'utf-8'))
    awaitingPrompt = True

#@pysnooper.snoop('/var/lib/cloud9/stn2120_tools/log/file.log')
def udpRx_thread(s):
    global address
    while True:
        dbytes = ''
        dbytes,address = s.recvfrom(64)
        data = dbytes.decode('utf-8')
        #data = data[:-1]
        uartTx_threadQueue.put(data)

#@pysnooper.snoop('/var/lib/cloud9/stn2120_tools/log/file.log')
def uartRx_thread(ser):
    global awaitingPrompt
    msg = ''
    while True:
        if not ser.isOpen():
            ser.open()
        char = ser.read().decode('utf-8')
        print(char)
        msg += char
        if char == '>':
            if awaitingPrompt:
                awaitingPrompt = False
        if char == '\r':
            udpTx_threadQueue.put(msg)
            msg = ''

#@pysnooper.snoop('/var/lib/cloud9/stn2120_tools/log/file.log')
def udpTx_thread(s):
    global address
    while True:
        msg = ''
        msg = udpTx_threadQueue.get()
        if len(msg) > 0:
            s.sendto(bytes(msg, 'utf-8'), address)

def uartTx_thread(ser):
    while True:
        msg = ''
        msg = uartTx_threadQueue.get()
        if len(msg)  > 0:
            sendSerial(ser, msg)

def main():
    UART.setup("UART1")
    ser = serial.Serial(port = "/dev/ttyO1", baudrate=9600)
    if not ser.isOpen():
        ser.open()
    time.sleep(.1)
    ser.flushInput()
    ser.flushOutput()
    ser = setBaud(ser, STNBAUD)
    try:
        udpRx_threadThread = threading.Thread(target = udpRx_thread, args = ([s]))
        udpRx_threadThread.start()
        uartRx_threadThread = threading.Thread(target = uartRx_thread, args=([ser]))
        uartRx_threadThread.start()
        udpTx_threadThread = threading.Thread(target = udpTx_thread, args = ([s]))
        udpTx_threadThread.start()
        uartTx_threadThread = threading.Thread(target = uartTx_thread, args=([ser]))
        uartTx_threadThread.start()
    except KeyboardInterrupt:
        s.close()
        ser.close()

if __name__ == "__main__":
    main()