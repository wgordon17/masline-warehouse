# Standard library
# Third party library
# Local library
from warehouse.server import run_server
from warehouse.server.config import log


if __name__ == "__main__":
    log.initialize_logs()
    run_server()
