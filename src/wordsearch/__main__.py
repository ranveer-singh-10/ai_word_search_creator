"""Start the web server: `python -m wordsearch` or the `wordsearch` command."""
import argparse

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Run the word search web app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="restart when the code changes")
    args = parser.parse_args()

    uvicorn.run("wordsearch.api:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
