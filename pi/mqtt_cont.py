# MQTT handler for the skylux syystem

import paho.mqtt.client as mqtt
import motor_driver
import logger
import time

SERVER = 'coltonsundstrom.net'
PORT = 1883
KEEPALIVE = 60

DEV_ID = 2

#globals
motorDriver = None
Logger = None

#comment
def on_connect(client, userdata, flags, rc):
    print("Connected with result code: " + str(rc))
    client.subscribe("SKYLUX/{}/command".format(DEV_ID))


def on_message(client, userdata, msg):
    print("Topic: {}, MSG: {}".format(msg.topic, msg.payload))
    status = Logger.readLog()
    print("Status: " + str(status))

    if b"ON" in msg.payload:
        if status < 15:
            # Add five seconds to log file.
            print("Turn device on")
            Logger.writeLog(str(status + 5))

            motorDriver.enable_motor()
            motorDriver.set_duty_cycle(100)

            time.sleep(5)

            motorDriver.set_duty_cycle(0)
        else:
            print("Device Limit already reached")

    elif b"OFF" in msg.payload:
        if status >= 5:
            print("Close Device")
            # Subtract five seconds from log file.
            Logger.writeLog(str(status - 5))

            motorDriver.enable_motor()
            motorDriver.set_duty_cycle(-100)

            time.sleep(4.75)

            motorDriver.set_duty_cycle(0)
        else:
            print("Cannot close any further.")

    else:
        print("Unknown command")


def initMQTT():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(SERVER, PORT, KEEPALIVE)

    return client


def main():
    global motorDriver
    global Logger
    motorDriver = motor_driver.MotorDriver(25, 24, 23)
    Logger = logger.Logger("log.txt")

    client = initMQTT()

    client.loop_forever()


