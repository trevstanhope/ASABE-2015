s = serial.Serial('/dev/ttyACM0', 9600)
while True
    try:
        c = raw_input('Enter command: ')
        s.write(c)
        r = s.readline()
        print r
    except KeyboardInterrupt:
        break
