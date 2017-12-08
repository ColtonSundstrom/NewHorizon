import paho.mqtt.client as mqtt
import sqlite3

SERVER = 'coltonsundstrom.net'
PORT = 1883
KEEPALIVE = 60

subscriptions = ['SKYLUX/newDevs']

conn = sqlite3.connect('skylux.db')
cur = conn.cursor()

cur.execute('''
                SELECT dev_id FROM devices;
            ''')
dev_ids = cur.fetchall()
devs = []
for ids in dev_ids:
    devs.append(ids[0])

print(devs)
for device in devs:
    subscriptions.append('SKYLUX/{}/status'.format(device))

print(subscriptions)


def on_connect(client, userdata, flags, rc):
    print("Connected to server with result code: " + str(rc))
    for sub in subscriptions:
        client.subscribe(sub)
        print("added subscription: {}".format(sub))


def on_message(client, userdata ,msg):
    print("Topic: {}, MSG: {}".format(msg.topic, msg.payload))
    for id in devs:

        if "SKYLUX/{}/status".format(id) in msg.topic:
            print("Changing status {} of device {}".format(msg.payload, id))
            stat_conn = sqlite3.connect('skylux.db')
            stat_cur = stat_conn.cursor()

            stat_cur.execute('''
                                UPDATE devices SET status = '{status}' WHERE dev_id = {did};
                            '''.format(status=msg.payload, did=id))
            stat_conn.commit()
            stat_conn.close()
            break



# other comment
def initSubMQTT():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message


    client.connect(SERVER, PORT, 60)

    return client


def quickPubMQTT(topic, payload):
    client = mqtt.Client()
    client.connect(SERVER, PORT, 60)
    ret = client.publish(topic, payload=payload, qos=0, retain=0)

    client.disconnect()

    return ret


if __name__ == "__main__":
    Client = initSubMQTT()

    while True:
        Client.loop_forever()
