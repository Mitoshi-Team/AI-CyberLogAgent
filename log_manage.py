import sys

from log_ai_agent.config import commands

# Dictionary of available commands
AVAILABLE_COMMANDS = {
    "collect_logs": "Collect system analyse_logs",
    "show_logs": "Show analyse_logs",
    "hide_logs": "Hide analyse_logs",
    "get_history": "Get incident history",
    "register": "Register a new user or modify an existing one",
}


def show_help():
    """Show console usage help."""
    print("\nAvailable commands:")
    print("-" * 50)
    for cmd, description in AVAILABLE_COMMANDS.items():
        print(f"{cmd:15} - {description}")
    print("\nUsage: python log_manage.py <command>")
    print("Example: python log_manage.py collect_logs\n")


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print("\nError: command not specified")
        show_help()
        sys.exit(1)

    command = sys.argv[1]

    if command == "collect_logs":
        commands.collect_logs()
    elif command == "show_logs":
        commands.show_logs()
    elif command == "hide_logs":
        commands.hide_logs()
    elif command == "get_history":
        commands.get_history()
    elif command == "register":
        commands.register()
    else:
        print(f"Error: unknown command '{command}'")
        show_help()
        sys.exit(1)
