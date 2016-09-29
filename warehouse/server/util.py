# Standard library
from datetime import datetime, timedelta
from logging import getLogger
# Third party library
# Local library
from warehouse.server.config.globals import M


def decode_cookie(request):
    my_cookie = request.get_secure_cookie("session", max_age_days=1)
    try:
        curr_uuid = my_cookie.decode("ascii")
    except AttributeError:
        curr_uuid = ""
    return curr_uuid


def is_authentic_connection(connection, handoff):
    log = getLogger("warehouse.server.handlers")
    # Using M.user_sub as my baseline for what must exist, check if all keys are present in `handoff`
    # Check 1: If not all of handoff keys exist in M.user_sub -> Problem
    # Check 2: If any current values from handoff match their defaults in M.user_sub -> Problem
    # Check 3: If it has taken longer than 5 second to redirect to index -> Problem
    # Check 4: If the original IP making the request is no longer the same IP address -> Problem
    if not all([key in handoff for key in M.user_sub.keys()]) or \
            any([handoff[key] == M.user_sub[key] for key in M.user_sub.keys()]) or \
            handoff["timestamp"] + timedelta(seconds=5) < datetime.now() or \
            handoff["originating"] != connection.request.remote_ip:
        # Houston, we have a problem, detect ALL problems and report each
        if not all([key in handoff for key in M.user_sub.keys()]):
            log.warning("Keys missing in handoff: {0}. Redirecting to login".format(
                [key for key in M.user_sub.keys() if key not in handoff]
            ), extra=connection.extra)
        if any([handoff[key] == M.user_sub[key] for key in M.user_sub.keys()]):
            log.warning("Values unchanged from default in handoff: {0}. Redirecting to login".format(
                ["{0}:{1}".format(key, handoff[key]) for key in M.user_sub.keys() if M.user_sub[key] == handoff[key]]
            ), extra=connection.extra)
        if "timestamp" in handoff and handoff["timestamp"] + timedelta(seconds=1) < datetime.now():
            log.warning("Client took {0} seconds to redirect. Redirecting to login".format(
                (datetime.now() - handoff["timestamp"]).total_seconds()
            ), extra=connection.extra)
        if "originating" in handoff and handoff["originating"] != connection.request.remote_ip:
            log.warning("Originating IP address, {0}, does not match current IP address, {1}. Redirecting to login".format(
                handoff["originating"], connection.request.remote_ip
            ), extra=connection.extra)

        # Not a successful authentication attempt
        return False
    else:
        # Successful authentication attempt!
        return True
