import argparse

from backend.simulation.report import format_report, run_baseline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AI-is-LOVE baseline simulation")
    parser.add_argument("--days", type=int, default=3, choices=range(1, 8))
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    report = format_report(run_baseline(args.days))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(report)
    else:
        print(report, end="")


if __name__ == "__main__":
    main()
