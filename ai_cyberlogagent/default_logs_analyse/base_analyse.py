"""Main module to run the complete log analysis pipeline."""

from log_analyzer import main as analyze_main
from log_collector import main as collect_main


def run_pipeline():
    """Runs the complete log analysis pipeline:
    1. Collect logs from source
    2. Analyze collected logs for incidents
    """
    print("=== Log Analysis Pipeline Started ===\n")

    # Step 1: Collect logs
    collect_main()

    print("\n")

    # Step 2: Analyze logs
    analyze_main()

    print("\n=== Log Analysis Pipeline Completed ===")


def main():
    """Entry point for the log analysis system."""
    run_pipeline()


if __name__ == "__main__":
    main()
