# Standard library
from logging import getLogger
from importlib import import_module
from mimetypes import add_type
from socket import gethostname
# Third party library
from tornado import ioloop, web
# Local library
from warehouse.server import config
from warehouse.server import handlers
from warehouse.server.config.globals import M
from warehouse.server.database import DbManager


def run_server():
    log = getLogger(__name__)
    log.debug("BASE_DIR set to " + config.BASE_DIR)
    set_globals()  # Set any necessary runtime global variables
    log.debug("Dynamic global variables set")
    set_modules()  # Import the "INSTALLED_APPS" specified in config.settings
    log.debug("Modules installed and loaded")
    initialize_db()  # Connect to the necessary database, debug vs production
    log.debug("Database connected")
    begin_application()  # Begin listening to port
    log.info("Server listening at port " + config.SERVER["port"])
    initiate_websocket_pings()  # Send ping to websockets every few seconds
    log.debug("Beginning periodic pings to all websocket clients")
    ioloop.IOLoop.instance().start()  # Begin tornado loop


def set_globals():
    if gethostname() == "production":
        M.icon_type = gethostname()
    else:
        M.icon_type = "testing"


def set_modules():
    log = getLogger(__name__)
    for module in config.INSTALLED_APPS:
        try:
            curr_module = import_module(module)
        except ImportError:
            log.exception("Ensure your modules are structured with an __init__.py file. Within the "
                                          "__init__.py file, ensure there is one line with `from .<module> import *`.")
        except NotImplementedError as e:
            log.critical(e)
            exit()
        else:
            try:
                # Add class from module to M.mods
                class_name = curr_module.__name__.split(".")[-1].title()
                M.mods[class_name] = getattr(curr_module, class_name)
                log.debug("{0} module installed".format(class_name))
            except AttributeError:
                log.exception("Ensure your modules are structured such that the class name is the "
                                           "same as the *.py file name, except in title case")


def initialize_db():
    log = getLogger(__name__)
    if config.DEBUG:
        db_settings = config.DATABASES["debug"]
    else:
        db_settings = config.DATABASES["default"]
    log.debug("Connecting to database {0}".format(db_settings["NAME"]))
    # Start database manager using 3 processors for handling queries
    M.db = DbManager('', '', db_settings["NAME"], db_settings["APP"], num_db_processes=3)


def begin_application():
    # Set settings for server
    server_settings = {"autoreload": False,
                       "debug": config.DEBUG,
                       "gzip": True,
                       "static_path": config.STATIC_DIR,
                       "template_path": config.TEMPLATE_DIR,
                       "cookie_secret": config.SECRET_KEY,
                       "static_handler_class": handlers.MaslineStatic}
    application = web.Application([
        (r"^/$", handlers.MaslineApp),
        (r"^/data", handlers.MaslineSocket),
        (r"^/.+", handlers.MaslineLogin)
    ], **server_settings)

    # Update mimetypes for unknown types
    add_type("application/font-woff", ".woff")
    add_type("audio/ogg", ".ogg")
    add_type("application/manifest+json", ".json")

    # Start server and broadcast starting message
    application.listen(config.SERVER["port"])


# WebSockets do not properly close when Wi-Fi connection is lost, potentially allowing
# another user to perform actions that do not appear to be their own.
# To catch this, the server periodically `ping`s each device to make sure it's still
# listening, and if it's not, the connected is officially terminated.
def initiate_websocket_pings():
    def ping_websockets():
        for ws in M.users.keys():
            try:
                ws.ping(b"")
            except:
                # Broad exception catch is deliberate because I don't care why this fails, or even if it fails
                # No need to remove, simply `ping`ing causes on_close to fire for websocket
                pass

    # Currently, websockets are `ping`ed every 5 seconds
    # It currently takes about 20 seconds for the server to recognize a disconnected device. Good enough?
    ping_callback = ioloop.PeriodicCallback(ping_websockets, 5000)
    ping_callback.start()
