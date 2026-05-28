"""Allow `python -m defendablecloud_cli` to invoke the CLI."""
from .main import app

if __name__ == "__main__":
    app()
