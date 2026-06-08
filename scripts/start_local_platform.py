from __future__ import annotations

import uvicorn

from src.local_platform.config import resolve_platform_config


def main() -> None:
    config = resolve_platform_config()
    uvicorn.run(
        "src.local_platform.api:app",
        host=config.host,
        port=config.port,
        reload=True,
    )


if __name__ == "__main__":
    main()
