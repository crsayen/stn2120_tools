from __future__ import print_function
import queue, socket, time, threading
import serial, sys, signal
import Adafruit_BBIO.UART as UART

udpPort = int(sys.argv[2]) if len(sys.argv) > 2 else 11000
s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind(('0.0.0.0',udpPort))
print("\n\nlistening on port " + str(udpPort)+"...")
while True:
    initbytes,address = s.recvfrom(64)
    if initbytes == b'init':
        break
    
awaitingPrompt = False
baudrate = 9600 # this must be 9600 initially
STNBAUD = 115200
uartRxQueue = queue.Queue()
udpRxQueue = queue.Queue()
uartTxQueue = queue.Queue()
udpTxQueue = queue.Queue()

def setBaud(ser, rate):
    global baudrate
    baudrate = rate
    rateBytes = bytes('STBR ' + str(rate),'utf-8')
    ser.close()
    ser.open()   
    if ser.isOpen():
        ser.write(rateBytes)
    ser.close()
    ser = serial.Serial(port = "/dev/ttyO1",baudrate=baudrate)
    ser.close()
    ser.open()
    if ser.isOpen():   
        ser.write(b'ATI\r')

def send(ser, msg):
    global awaitingPrompt
    while awaitingPrompt:
        pass
    ser.write(bytes(msg + '\r', 'utf-8'))
    awaitingPrompt = True

def udpRx(s,):
    while True:
        dbytes,addr = s.recvfrom(64)
        data = dbytes.decode('utf-8')
        uartTxQueue.put(data)

def uartRx(ser):
    global awaitingPrompt
    msg = ''
    while True:
        char = ser.read().decode('utf-8')
        msg += char
        if char == '>':
            if awaitingPrompt:
                awaitingPrompt = False
        if char == '\r':
            udpRxQueue.put(msg)
            msg = ''

def udpTx(s):
    msg = udpTxQueue.get()
    s.sendto(msg.encode('utf-8'), (address, udpPort))

def uartTx(ser):
    msg = uartTxQueue.get()
    send(ser, msg)

def main():
    UART.setup("UART1")
    ser = serial.Serial(port = "/dev/ttyO1", baudrate=baudrate)
    setBaud(ser, STNBAUD)
    try:
        udpRxThread = threading.Thread(target = udpRx, args = ([s]))
        udpRxThread.start()
        uartRxThread = threading.Thread(target = uartRx, args=([ser]))
        uartRxThread.start()
        udpTxThread = threading.Thread(target = udpTx, args = ([s]))
        udpTxThread.start()
        uartTxThread = threading.Thread(target = uartTx, args=([ser]))
        uartTxThread.start()
    except KeyboardInterrupt:
        s.close()
        ser.close()

if __name__ == "__main__":
    main()