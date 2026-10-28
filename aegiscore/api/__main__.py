"""Run the API through its loopback-validated local launcher."""

import os

import uvicorn

from aegiscore.api.app import app


def main() -> None:
    try:
        port = int(os.environ.get("AEGISCORE_API_PORT", "8000"))
    except ValueError:
        raise SystemExit("AEGISCORE_API_PORT must be an integer from 1 through 65535.") from None
    if not 1 <= port <= 65535:
        raise SystemExit("AEGISCORE_API_PORT must be an integer from 1 through 65535.")
    uvicorn.run(app, host=app.state.api_host, port=port)


if __name__ == "__main__":
    main()
