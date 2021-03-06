from flask import Flask, jsonify, abort, make_response, request, url_for
import sqlite3
import comp_mqtt


OPEN = 1
CLOSE = 0


app = Flask(__name__)

conn = sqlite3.connect('devices.db')
cur = conn.cursor()


cur.execute('''
            CREATE TABLE IF NOT EXISTS devices(
            dev_id INTEGER PRIMARY KEY ASC,
            ip varchar(15) NOT NULL,
            status INTEGER NOT NULL,
            active BIT NOT NULL);
            ''')
conn.commit()

cur.execute('''
            SELECT name FROM sqlite_master WHERE type='table';
            ''')

print("Printing tables in 'devices.db':")
tabs = cur.fetchall()
for tab in tabs:
    print(tab[0])


cur.execute('''
            SELECT * FROM devices;
            ''')

print("Printing all data from 'devices':")
dats = cur.fetchall()
for dat in dats:
    print(dat[0])

print("Finished")


def checkDevID(dev_id):
    conn = sqlite3.connect('devices.db')
    curs = conn.cursor()

    curs.execute('''
                SELECT * FROM devices WHERE dev_id = {did};
                '''.format(did=dev_id))
    result = curs.fetchall()

    conn.close()

    return (len(result) > 0)


@app.route('/skylux/api/devices', methods=['GET'])
def get_devices():
    get_conn = sqlite3.connect('devices.db')
    get_cur = get_conn.cursor()

    get_cur.execute('''
              SELECT dev_id FROM devices;
              ''')
    dev_ids = get_cur.fetchall()
    if len(dev_ids) == 0:
        abort(404)

    get_conn.close()
    devs = []
    for id in dev_ids:
        devs.append(id[0])

    return jsonify({'devices': devs}, 200)


@app.route('/skylux/api/status/<int:device_id>', methods=['GET'])
def get_status(device_id):
    get_stat_conn = sqlite3.connect('devices.db')
    stat_cur = get_stat_conn.cursor()

    stat_cur.execute('''
                    SELECT status FROM devices WHERE dev_id = {did};
                    '''.format(did=device_id))
    res_status = stat_cur.fetchall()

    get_stat_conn.close()

    if len(res_status) == 0:
        abort(404)

    status = res_status[0]

    return jsonify({'Skylight Status': status}, 200)

@app.route('/skylux/api/schedule/<int:dev_id>', methods=['POST'])
def schedule_device(dev_id):
    if not checkDevID(dev_id):
        abort(404)

    if not request.json or not 'command' in request.json or not 'time' in request.json:
        abort(400)

    command = request.json['command']
    print(command)
    if command not in ('ON', 'OFF'):
       abort(400)

    time = request.json['time']
    print(time)

    datagram = [time, command]

    topic = "SKYLUX/{}/schedule".format(dev_id)
    result = comp_mqtt.quickPubMQTT(topic, datagram)

    print("Message sent| resp: {}, msg_num: {}".format(result[0], result[1]))

    return jsonify({'Request Result': result[0], 'Message ID': result[1]}, 200)

# Build a 'put' command allowing change of all values
@app.route('/skylux/api/status/<int:dev_id>', methods=['PUT'])
def update_values(dev_id):
    if not checkDevID(dev_id):
        abort(404)

    if not request.json:
        abort(400)

    conn = sqlite3.connect('device.db')
    curr = conn.cursor()

    if 'status' in request.json:
        print("Status type: {}".format(type(request.json['status'])))

        # curr.execute('''
        #                 UPDATE devices SET status = {status} WHERE dev_id = {did};
        #              '''.format(request.json['status'], did=dev_id))

    if 'active' in request.json:
        print("Status type: {}".format(type(request.json['active'])))

        # curr.execute('''
        #                 UPDATE devices SET status = {act} WHERE dev_id = {did};
        #              '''.format(act=request.json['active'], did=dev_id))

    if 'ip' in request.json:
        print("Status type: {}".format(type(request.json['ip'])))

        # curr.execute('''
        #                 UPDATE devices SET status = {ip} WHERE dev_id = {did};
        #              '''.format(ip=request.json['ip'], did=dev_id))

    curr.execute('''
                    SELECT * FROM devices WHERE dev_id = {did};
                 '''.format(dev_id))
    ret = curr.fetchall()
    print(ret)

    abort(501)


@app.route('/skylux/api/device/<int:dev_id>', methods=['POST'])
def operate_device(dev_id):
    if not checkDevID(dev_id):
        abort(404)

    if not request.json or not 'command' in request.json:
        abort(400)

    command = request.json['command']
    print(command)
    if command not in ('ON', 'OFF'):
       abort(400)

    topic = "SKYLUX/{}/command".format(dev_id)
    result = comp_mqtt.quickPubMQTT(topic, command)

    print("Message sent| resp: {}, msg_num: {}".format(result[0], result[1]))

    return jsonify({'Request Result': result[0], 'Message ID': result[1]}, 200)


def make_public(device):
    new_dev = {}
    for field in device:
        if field == 'id':
            new_dev['uri'] = url_for('get_devices', task_id=device['id'], _external=True)
        else:
            new_dev[field] = device[field]

    return new_dev


@app.errorhandler(501)
def not_impl(error):
    return make_response(jsonify({'error': 'Not Implemented'}), 501)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not Found'}), 404)

# Generic Comment WIth CHanges
@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'error': 'Bad Request'}), 400)


if __name__ == '__main__':
    # app.run(debug = True)
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=True)

