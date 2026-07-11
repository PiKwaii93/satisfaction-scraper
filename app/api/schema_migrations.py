import argparse
import json

from app.api.database import (
    ensure_product_schema,
    get_schema_revision,
    run_schema_downgrade,
)


def main():
    parser = argparse.ArgumentParser(description="Manage product database migrations.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("upgrade", help="Upgrade or safely baseline to head.")
    subparsers.add_parser("current", help="Show current and head revisions.")

    downgrade_parser = subparsers.add_parser(
        "downgrade", help="Downgrade the product schema. This can destroy data."
    )
    downgrade_parser.add_argument("--revision", default="-1")
    downgrade_parser.add_argument("--yes", action="store_true")

    args = parser.parse_args()
    if args.command == "upgrade":
        ensure_product_schema(max_attempts=30, delay_seconds=2)
        print(json.dumps(get_schema_revision()))
        return
    if args.command == "current":
        print(json.dumps(get_schema_revision()))
        return
    if not args.yes:
        parser.error("downgrade requires --yes because it can destroy product data")
    run_schema_downgrade(args.revision)
    print(json.dumps(get_schema_revision()))


if __name__ == "__main__":
    main()
