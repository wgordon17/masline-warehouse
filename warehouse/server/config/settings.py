# Standard library
from os import path, getenv
from sys import path as syspath
# Third party library
# Local library


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
# BASE_DIR is the warehouse package directory
# This is ONLY the base_dir when application.py is the initiating script
BASE_DIR = path.join(syspath[0], "warehouse")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = getenv("TORNADO_SECRET", "Cc>32wuPT|Hl{mio'y4LJ$xp:c)<_EiZ_JtbLOAT*()-($'*_Z@_etO)9c;U+Qb#,iHo")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# server definitions
SERVER = {
    "port": "9000"
}

# Directories
STATIC_DIR = path.join(BASE_DIR, "server", "static")
TEMPLATE_DIR = path.join(BASE_DIR, "server", "templates")

# Application definition
INSTALLED_APPS = [
    "warehouse.modules.picking",
]

# Database definitions
DATABASES = {
    "default": {
        "NAME": "epds01",
        "APP": "Warehouse"
    },
    "debug": {
        "NAME": "epds99",
        "APP": "Whse-Testing"
    }
}
