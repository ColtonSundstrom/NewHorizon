import sqlite3

conn = sqlite3.connect('example.db')

c = conn.cursor()
c.execute('''
          CREATE TABLE person
          (id INTEGER PRIMARY KEY ASC, name VARCHAR(250) NOT NULL)
          ''')
c.execute('''
          CREATE TABLE address
          (id INTEGER PRIMARY KEY ASC, street_name VARCHAR(250), street_number VARCHAR(250),
           post_code VARCHAR(250) NOT NULL, person_id INTEGER NOT NULL,
           FOREIGN KEY(person_id) REFERENCES person(id))
          ''')

c.execute('''
          INSERT INTO person VALUES(1, 'pythoncentral')
          ''')
c.execute('''
          INSERT INTO address VALUES(1, 'python road', '1', '00000', 1)
          ''')

conn.commit()
conn.close()