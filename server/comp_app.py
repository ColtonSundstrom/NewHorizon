from flask import Flask, jsonify, abort, make_response, request, url_for
import sqlite3
import comp_mqtt
import datetime
import jwt

SECRET_KEY = b"This is a secret key"


OPEN = 1
CLOSE = 0


app = Flask(__name__)

conn = sqlite3.connect('skylux.db')
cur = conn.cursor()


cur.execute('''
            CREATE TABLE IF NOT EXISTS devices(
            dev_id INTEGER PRIMARY KEY ASC,
            mac_addr varchar(17) NOT NULL,
            status INTEGER NOT NULL,
            active BIT NOT NULL);
            ''')
conn.commit()

cur.execute('''
            CREATE TABLE IF NOT EXISTS users(
            dev_id INTEGER,
            username varchar(255) NOT NULL,
            password varchar(255) NOT NULL);
            ''')
conn.commit()

cur.execute('''
            SELECT name FROM sqlite_master WHERE type='table';
            ''')

print("Printing tables in 'skylux.db':")
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


def encode_auth_token(dev_id):
    payload = {
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=0, seconds=60),
        'iat': datetime.datetime.utcnow(),
        'sub': dev_id
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    print("token: {}".format(token))
    return token


def decode_auth_token(auth_token):
    """
    Decodes the auth token
    :param auth_token:
    :return: integer|string
    """
    try:
        payload = jwt.decode(auth_token, app.config.get('SECRET_KEY'))
        return payload['sub']
    except jwt.ExpiredSignatureError:
        return 'Signature expired. Please log in again.'
    except jwt.InvalidTokenError:
        return 'Invalid token. Please log in again.'


def checkMAC(mac):
    conn = sqlite3.connect('skylux.db')
    curs = conn.cursor()

    curs.execute('''
                SELECT dev_id FROM devices WHERE mac_addr = "{mid}";
                '''.format(mid=mac))
    result = curs.fetchall()

    if len(result) > 0:
        ret = result[0][0]
    else:
        ret = -1

    conn.close()

    return ret


def checkDevID(dev_id):
    conn = sqlite3.connect('skylux.db')
    curs = conn.cursor()

    curs.execute('''
                SELECT * FROM devices WHERE dev_id = {did};
                '''.format(did=dev_id))
    result = curs.fetchall()

    conn.close()

    return len(result) > 0


def checkCred(username, password):
    conn = sqlite3.connect('skylux.db')
    curs = conn.cursor()

    curs.execute('''
                    SELECT dev_id FROM users WHERE username = '{un}' and password = '{pw}';
                    '''.format(un=username, pw=password))
    result = curs.fetchall()

    conn.close()

    if len(result) > 0:
        ret = result[0][0]
    else:
        ret = -1

    return ret


@app.route('/skylux/api/login', methods=['POST'])
def login_user():
    if not request.json:
        abort(400)

    if 'username' not in request.json or 'password' not in request.json:
        abort(400)

    username = request.json['username']
    password = request.json['password']

    valid = checkCred(username, password)

    if valid < 0:
        abort(401)

    return jsonify({'token': encode_auth_token(valid)}, 200)

@app.route('/skylux/api/test', methods=['POST'])
def test_login():
    if not request.json:
        abort(400)

    if 'token' not in request.json:
        abort(400)

    token = request.json['token']
    dev_id = decode_auth_token(token)

    print(dev_id)

    return jsonify({'device': dev_id}, 200)


@app.route('/skylux/api/register', methods=['POST'])
def register_user():
    if not request.json:
        abort(400)

    if 'username' not in request.json or 'mac' not in request.json or 'password' not in request.json:
        abort(400)

    username = request.json['username']
    password = request.json['password']
    mt = request.json['mac']
    mac = "{}{}:{}{}:{}{}:{}{}:{}{}:{}{}".format(mt[0], mt[1], mt[2], mt[3], mt[4], mt[5], mt[6], mt[7], mt[8], mt[9],
                                                 mt[10], mt[11])

    mac_check = checkMAC(mac)

    if mac_check < 0:
        print("Mac {} not found.".format(mac))
        abort(400)

    conn = sqlite3.connect('skylux.db')
    cur = conn.cursor()

    cur.execute("INSERT INTO users (dev_id, username, password) VALUES ('{did}', '{un}', '{pw}');".format(did=mac_check,
                                                                                                    un=username,
                                                                                                    pw=password))
    conn.commit()
    conn.close()

    return jsonify({'device id': mac_check}, 200)


@app.route('/skylux/api/devices', methods=['GET'])
def get_devices():
    get_conn = sqlite3.connect('skylux.db')
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
    get_stat_conn = sqlite3.connect('skylux.db')
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

    conn = sqlite3.connect('skylux.db')
    curr = conn.cursor()

    if 'status' in request.json:
        print("Status: {}".format(request.json['status']))

        curr.execute('''
                        UPDATE devices SET status = '{status}' WHERE dev_id = '{did}';
                     '''.format(status=request.json['status'], did=dev_id))

    if 'active' in request.json:
        print("active type: {}".format(type(request.json['active'])))

        # curr.execute('''
        #                 UPDATE devices SET status = {act} WHERE dev_id = {did};
        #              '''.format(act=request.json['active'], did=dev_id))

    if 'mac' in request.json:
        print("mac type: {}".format(type(request.json['mac'])))

        # curr.execute('''
        #                 UPDATE devices SET status = {ip} WHERE dev_id = {did};
        #              '''.format(ip=request.json['ip'], did=dev_id))

    conn.commit()

    curr.execute('''
                    SELECT * FROM devices WHERE dev_id = '{did}';
                 '''.format(did=dev_id))
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

@app.errorhandler(401)
def forbid_request(error):
    return make_response(jsonify({'error': 'Unauthorized'}), 401)

# Generic Comment WIth CHanges
@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'error': 'Bad Request'}), 400)


if __name__ == '__main__':
    # app.run(debug = True)
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=True)

