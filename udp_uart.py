from __future__ import print_function
import queue, socket, time, threading
import serial, sys, signal, time
import Adafruit_BBIO.UART as UART
import pysnooper

for arg in sys.argv:
    DEBUG = True if arg == 'd' else False
    udpPort = int(arg) if arg.isnumeric() else 11000
    MONITOR = True if arg == 'm' else False

s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind(('0.0.0.0',udpPort))
print('\n\nlistening on port ' + str(udpPort)+'...')
    
LOG_PATH = 'debug.log'
if DEBUG:
    open(LOG_PATH, 'w').close()

awaitingPrompt = False
baudrate = 9600 # this must be 9600 initially
STNBAUD = 115200
SEND_TIMEOUT = 0.05
address = ('0.0.0.0',udpPort)
uartRx_threadQueue = queue.Queue()
udpRx_threadQueue = queue.Queue()
uartTx_threadQueue = queue.Queue()
udpTx_threadQueue = queue.Queue()

def debug_(dec, condition):
    def decorator(func):
        if not condition:
            return func
        return dec(func)
    return decorator

@debug_(pysnooper.snoop(LOG_PATH), DEBUG)
def init(ser, rate):
    time.sleep(.1)
    baudrate = rate
    rate = 'ST SBR ' + str(rate)
    sendSerial(ser, 'ATVR')
    sendSerial(ser, 'ST BRT 300')
    sendSerial(ser, rate)
    sendSerial(ser, 'ST WBR')
    ser = serial.Serial(
        port = '/dev/ttyO1',
        baudrate = baudrate
    )

    sendSerial(ser, 'ATI')
    return ser

@debug_(pysnooper.snoop(LOG_PATH), DEBUG)
def sendSerial(ser, msg):
    start = time.time()
    global awaitingPrompt
    while awaitingPrompt:
        curr = time.time()
        if curr - start > SEND_TIMEOUT:
            break
    if not ser.isOpen():
        ser.open()
    #ser.flushOutput()
    ser.write(bytes(msg + '\r', 'utf-8'))
    awaitingPrompt = True

@debug_(pysnooper.snoop(LOG_PATH), DEBUG)
def udpRx_thread(s):
    global address
    while True:
        dbytes = ''
        dbytes,address = s.recvfrom(64)
        data = dbytes.decode('utf-8')
        uartTx_threadQueue.put(data)


@debug_(pysnooper.snoop(LOG_PATH), DEBUG)
def uartRx_thread(ser):
    global awaitingPrompt
    msg = ''
    while True:
        if not ser.isOpen():
            ser.open()
        char = ser.read().decode('utf-8')
        msg += char
        if char == '>':
            if awaitingPrompt:
                awaitingPrompt = False
        if char == '\r':
            if MONITOR:
                udpTx_threadQueue.put(msg)
            else:
                print(msg)
            if msg == 'KILLBB\r':
                s.close()
                ser.close()
            msg = ''

@debug_(pysnooper.snoop(LOG_PATH), DEBUG)
def udpTx_thread(s):
    global address
    while True:
        msg = ''
        msg = udpTx_threadQueue.get()
        if len(msg) > 0:
            pass
            s.sendto(bytes(msg, 'utf-8'), address)

def uartTx_thread(ser):
    while True:
        msg = ''
        msg = uartTx_threadQueue.get()
        if len(msg)  > 0:
            sendSerial(ser, msg)

def main():
    UART.setup('UART1')
    ser = serial.Serial(
        port = '/dev/ttyO1', 
        baudrate = 9600
    )

    if not ser.isOpen():
        ser.open()
    time.sleep(.1)
    ser.flushInput()
    ser.flushOutput()
    
    while data not 'init':
        dbytes = ''
        dbytes,address = s.recvfrom(64)
        data = dbytes.decode('utf-8')

    ser = init(ser, STNBAUD)
    #sendSerial(ser, 'AT SP2')
    #sendSerial(ser, 'AT H1')
    #sendSerial(ser, 'AT MA')
    
    try:
        udpRx_threadThread = threading.Thread(
            target = udpRx_thread, 
            args = ([s])
        )
        udpRx_threadThread.start()

        uartRx_threadThread = threading.Thread(
            target = uartRx_thread, 
            args = ([ser])
        )
        uartRx_threadThread.start()
        
        if MONITOR:
            udpTx_threadThread = threading.Thread(
                target = udpTx_thread, 
                args = ([s])
            )
            udpTx_threadThread.start()

        uartTx_threadThread = threading.Thread(
            target = uartTx_thread, 
            args = ([ser])
        )
        uartTx_threadThread.start()
        
        s.sendto(bytes('ready', 'utf-8'), address)

    except KeyboardInterrupt:
        s.close()
        ser.close()

if __name__ == '__main__':
    main()