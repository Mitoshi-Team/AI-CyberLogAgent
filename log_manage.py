import sys

from config import commands

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "collect_logs":
        commands.collect_logs()
    if len(sys.argv) > 1 and sys.argv[1] == "show_logs":
        commands.show_logs()
    if len(sys.argv) > 1 and sys.argv[1] == "hide_logs":
        commands.hide_logs()
    if len(sys.argv) > 1 and sys.argv[1] == "get_history":
        commands.get_history()
    if len(sys.argv) > 1 and sys.argv[1] == "edit_pass":
        commands.edit_pass()
