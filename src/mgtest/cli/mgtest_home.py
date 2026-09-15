import argparse
import logging

from mgtest.home.home import Home

logger = logging.getLogger(__name__)

COMMAND = "home"


def populate_parser(parser: argparse.ArgumentParser):
    parser.set_defaults(func=run)


def run(args):
    home = Home()
    logging.info(f"{home.base}")
    logging.info("TODO: Add cache clearing, tooling clearing, more details on home!")
    return 0


def main():
    from mgtest.internal.logging import setup_logging

    setup_logging()

    parser = argparse.ArgumentParser(prog="mgtest_home")
    populate_parser(parser)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    main()
