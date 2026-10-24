import os
import mysql.connector


class Database:

    def __init__(self):
        host = os.getenv("DB_HOST", "localhost")
        port = int(os.getenv("DB_PORT", "3306"))
        user = os.getenv("DB_USER", "root")
        password = os.getenv("DB_PASSWORD", "Patil@203")
        database = os.getenv("DB_NAME", "inventory_management")

        self.connection = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )

        self.cursor = self.connection.cursor()

        if self.connection.is_connected():
            print("Database Connected Successfully!")

    def close(self):

        self.cursor.close()
        self.connection.close()
