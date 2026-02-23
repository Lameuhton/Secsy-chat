from common import network
import logging

# CONFIGURATION DU LOGGER
logging.basicConfig(
    filename="app_server.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger_client = logging.getLogger(__name__)

def main():

    sock = network.start_tcp_server("127.0.0.1", 4000)

    while True:


if __name__ == "__main__":
    main()
