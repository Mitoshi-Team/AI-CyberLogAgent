import bcrypt

BD = []  # ЗАГЛУШКА вместо бд>>>
SALT = bcrypt.gensalt(rounds=12)


def collect_logs():
    """Collect logs from the specified directory."""
    print("Logs collected\n")  # ЗАГЛУШКА >>>


def hide_logs():
    """Hide the logs from view."""
    print("Logs hidden\n")


def show_logs():
    """Display the logs."""
    print("Logs shown\n")  # ЗАГЛУШКА >>>


def get_history():
    """Retrieve the incident history."""
    print("Incidents history shown\n")  # ЗАГЛУШКА >>>


def register():
    """Register a new user or change password for existing user.

    Prompts for login and password, hashes the password using bcrypt,
    and stores the login and hashed password in the database (simulated by BD list).
    If user exists, allows password change after verifying current password.

    Note:
        This is a placeholder implementation. In production, use proper
        database operations and environment variables for security.

    """
    print(
        "\nTo cancel registration at any time, simply press Enter without typing anything"
    )

    login = input("Login: ")
    if login.lower() == "":
        print("Registration process cancelled.")
        return

    password = input("Password: ")
    if password.lower() == "":
        print("Registration process cancelled.")
        return

    # Check if user exists
    user_exists = False
    for user in BD:
        if user["login"] == login:
            user_exists = True
            # Verify current password before allowing change
            if bcrypt.checkpw(password.encode("utf-8"), user["hashed_password"]):
                new_password = input(
                    "Enter new password (or just press Enter to cancel): "
                )
                if new_password.lower() == "":
                    print("Password change cancelled.")
                    return
                user["hashed_password"] = bcrypt.hashpw(
                    new_password.encode("utf-8"), SALT
                )
                print(f"Password changed successfully for user: {login}")
            else:
                print("Incorrect password")
            break

    # Register new user
    if not user_exists:
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), SALT)
        BD.append({"login": login, "hashed_password": hashed_password})
        print(f"User registered successfully: {login}")

    # ЗАГЛУШКА: Сохранение в БД (реализация зависит от используемой базы данных)
