from django.db import connection


# all crud operations related to user table will be defined here as static methods,
# so that they can be easily called from
# views or other parts of the application without needing to create an instance of the class.
class UserDB:
    @staticmethod
    def get_all_users():
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM user")
            columns = [col[0] for col in cursor.description]  # Extract all column names
            rows = cursor.fetchall()

            # Convert each row to a dictionary
            return [dict(zip(columns, row)) for row in rows]

    @staticmethod
    def get_user_by_id(user_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM user WHERE user_id = %s", [user_id])
            columns = [col[0] for col in cursor.description]  # Extract all column names
            row = cursor.fetchone()

            return (
                dict(zip(columns, row)) if row else None
            )  # Return None if user not found

    @staticmethod
    def create_user(name, email, password):
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO user(name, email, password) VALUES (%s, %s, %s)",
                [name, email, password],
            )
            return {
                "message": "User created successfully!",
                "user_id": cursor.lastrowid,
            }

    @staticmethod
    def update_user(user_id, name, email, password):
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE user SET name = %s, email = %s, password = %s WHERE user_id = %s",
                [name, email, password, user_id],
            )
            return {"message": "User updated successfully!"}

    @staticmethod
    def delete_user(user_id):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM user WHERE user_id = %s", [user_id])
            return {"message": "User deleted successfully!"}

    @staticmethod
    def get_user_by_email(email):
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM user WHERE email = %s", [email])
            columns = [col[0] for col in cursor.description]  # Extract all column names
            row = cursor.fetchone()

            return (
                dict(zip(columns, row)) if row else None
            )  # Return None if user not found

    @staticmethod
    def update_password(email, hashed_password):
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE user SET password = %s WHERE email = %s",
                [hashed_password, email],
            )
            return {"message": "Password updated successfully!"}