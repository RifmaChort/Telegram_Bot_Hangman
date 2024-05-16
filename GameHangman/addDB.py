import logging
import psycopg2
from psycopg2 import Error

connection = None
try:
    connection = psycopg2.connect(user="postgres",
        password="Qq12345",
        host="192.168.56.109",
        port="5432",
        database="devops_db")
    cursor = connection.cursor()
    cursor.execute("INSERT INTO emails (email_id, name) VALUES"
                   "(1, 'devOops@mail.com'),"
                   "(2, 'teketeke@email.com');"
                   "INSERT INTO phones (phone_id, phone) VALUES"
                   "(1, '8(800)555-35-35'),"
                   "(2, '8(990)999-99-99');")
    connection.commit()
    logging.info("Команда успешно выполнена")
except (Exception, Error) as error:
    logging.error("Ошибка при работе с PostgreSQL: %s", error)
finally:
    if connection is not None:
        cursor.close()
        connection.close()