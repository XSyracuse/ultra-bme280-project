import time
from ustruct import unpack, unpack_from
from array import array
from micropython import const
import ssd1306
import framebuf

def net():
    import network
    import usocket as socket
    import ntptime
    from machine import RTC

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect('rohr2', '0394747aHeKs')
        while not wlan.isconnected():
            pass
    print('network config:', wlan.ifconfig())
    
    rtc = RTC()
    ntp = ''
    try:
        ntptime.settime()
        ntp = rtc.datetime()
        print(ntp)
    except OSError:
        print('ntp time error')
        

 
    #send socket
    add = ("192.168.128.29",4445)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    #rx socket
    rsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rsock.bind(('0.0.0.0',4446))
    rsock.setblocking(False)

    _c=0

    def sendudp(data):
        #print ('send')
        t = rtc.datetime()
        data = '{0:02d}:{1:02d}UTC '.format(t[4],t[5]) + data
        sock.sendto(data,add)

    def rxudp(buf):
        try:
            buf,ad = rsock.recvfrom(64)
            print('rx:')
            print(_c)
            print(buf)
        except OSError:
            _c += 1
        return

    return rxudp,sendudp,ntp

def _bcd2bin(value):
    return (value or 0) - 6 * ((value or 0) >> 4)


def _bin2bcd(value):
    return (value or 0) + 6 * ((value or 0) // 10)

def dsrtc(iic,ntp=None):
    import struct

    #ds3132 = 0x68
    #eeprom = 0x57  
    bf = bytearray(7) #7 bytes for time related registers starting at 0 
    rb = iic.readfrom_mem_into
    #rb = iic.readfrom_mem
    # starting from 0, device snapshots time 
    # and date registers in user buffer
    # to prevent update errors
    
    if ntp is None:
        pass
    else:
        #ntp 
        #year/month/day/doweek/utchour/min/sec/yearday?
        bf[0] = _bin2bcd(ntp[6])   #seconds
        bf[1] = _bin2bcd(ntp[5])   #min
        bf[2] = _bin2bcd(ntp[4]-4) #hour 
        #day/date/month/year
        bf[3] = _bin2bcd(2)
        bf[4] = _bin2bcd(28)
        bf[5] = 0x80 | _bin2bcd(9) #century = 19+1
        bf[6] = _bin2bcd(20)
        iic.writeto_mem(0x68,0,bf)

 
    def dsrtc_rd():
        
        rb(0x68,0x00,bf)
        return bf
   
    def dsrtc_upk():     
        return list(map(_bcd2bin,bf))

      
    def dsrtc_alarm1(hr,minute):
        b=bytearray(4)
        b[0] = 0                 #A1M1=0 / alarm1 seconds
        b[1] = _bin2bcd(minute)  #A1M2=0 / alarm1 min
        b[2] = _bin2bcd(hr)      #A1M3=0
        b[3] = 0x80              #A1M4=1
        iic.writeto_mem(0x68,7,b)                
           

    def dsrtc_chk(c=None):
        
        if c is None:
            
            pass
        else:
            b=bytearray(1)
            b[0]=0
            iic.writeto_mem(0x68,15,b) 

        alm = iic.readfrom_mem(0x68,15,1)
        #print ('status: {}'.format(alm))   
        return alm
 
    return dsrtc_rd, dsrtc_upk, dsrtc_alarm1, dsrtc_chk

def ledEnclosed(blue):
  import machine
  p2 = machine.Pin(2, machine.Pin.OUT)
  on = p2.on
  off = p2.off

  def toggleLED():
    nonlocal blue
    if blue:
      off()
      blue = False
    else:
      on()
      blue = True

  return toggleLED

def bme_main():
    from machine import I2C
    from machine import Pin
    from machine import Timer
    from machine import freq
    from utime import sleep
    import math
    import bme280_float

    freq(160000000)
    led = ledEnclosed(True)
    tim = Timer(-1)
    tim.init(period=300,mode=Timer.PERIODIC,callback=lambda t:led())

    i2c=I2C(scl=Pin(4),sda=Pin(5),freq=400000)
    print(i2c.scan()) 
    oled = ssd1306.SSD1306_I2C(128,64,i2c)
    bme280 = bme280_float.BME280(i2c=i2c)

    ame = bytearray(b'\xe3\xf3\x33\x33\xb3\x33\x33\x33\xff\xff\x33\xb3\x33\x33\xf3\xf3\xff\xff\x00\x00\x08\x11\x22\x00\xff\xff\x00\x08\x51\x80\xc0\xff')
   
    hare = bytearray(b'\xfc\xfc\x0c\x0c\x0c\x0c\x0c\x0c\xfc\xfc\x00\x00\x00\x10\x10\x90\x90\xff\x90\x90\x10\x10\x00\x00\xff\xff\x18\x18\x18\x18\x18\x18\xff\xff\x00\x04\x04\xf4\x94\x94\x94\x97\x94\x94\xf4\x04\x04\x00\x7f\x7f\x30\x30\x30\x30\x30\x30\x7f\x7f\x00\x00\x00\x7f\x04\x04\x04\x04\x04\x24\x7f\x00\x00\x00')

    yuki = bytearray(b'\xf3\xf3\x33\xb3\xb3\xb3\x33\xb3\xb3\xb3\x33\xff\xff\x33\xb3\xb3\xb3\x33\xb3\xb3\xb3\x33\xf3\xf3\x0f\x0f\x00\x04\x04\x04\x20\x24\x24\x24\x20\x23\x2f\x20\x24\x24\x24\xe0\x04\x04\x04\x00\x0f\x0f\x00\x00\x00\x00\x00\x00\x22\x22\x22\x22\x22\x22\x22\x22\x22\x22\x22\x3f\x00\x00\x00\x00\x00\x00')

    kumori = bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x7f\x49\x49\x49\x49\x7f\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xfd\xfd\x05\x25\x25\x25\xb5\x25\x05\xff\xff\x05\x25\x25\x25\xb5\x25\x05\x05\xfd\x00\x00\x00\x00\x03\x03\x00\x01\x09\x09\x49\x49\x68\x5b\x4b\x48\x59\x69\x49\x89\x09\x08\x01\x03\x00\x00')

    f = framebuf.FrameBuffer(hare,24,24,framebuf.MONO_VLSB)
    f1 = framebuf.FrameBuffer(kumori,24,24,framebuf.MONO_VLSB)
    r,s,ntp = net()
    
    #get ds3231 device functions
    dsrtc_rd, dsrtc_upk, dsrtc_alarm1, dsrtc_chk = dsrtc(i2c)
    dsrtc_chk(c=1)
    dsrtc_alarm1(23,42)

    y=64
    oled.text('HI',0,64-16,1)
    oled.show()
    while True:
        x = dsrtc_rd()
        t,p,h=bme280.read_compensated_data()
        bme = bme280.values
        s(bme[0] + ' ' + bme[1] + ' ' + bme[2] + '\n') 
        t = '{:02x}:{:02x}:{:02x}'.format(x[2],x[1],x[0])
        oled.text(t,0,0,1)
        oled.text(bme[0],0,12,1)
        oled.text(bme[1],0,24,1)
        oled.text(bme[2],0,36,1)

        if p<100200:
            oled.blit(f1,96,y,0)
        else:
            oled.blit(f,96,y,0)

        oled.show()
        sleep(0.05)
  
        #blank out buffer no need to show
        oled.text(t,0,0,0)
        oled.text(bme[0],0,12,0)
        oled.text(bme[1],0,24,0)
        oled.text(bme[2],0,36,0)
        
        oled.fill_rect(96,y,24,24,0)

        if y>-24:
          y=y-2
        else:
          y=64

        a=dsrtc_chk()
        c = a[0] & 0x01  
        if c==1:
            print('alarm')
            oled.text('Alarm',0,64-8,1)
            dsrtc_chk(c=1)
        else:
            oled.text('Alarm',0,64-8,0) 
        


if __name__=='__main__':
    bme_main()

