"""Console script entry point — runs the uvicorn dev server."""


def cli() -> None:
    import uvicorn

    uvicorn.run("hoshi_api.app:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    cli()
