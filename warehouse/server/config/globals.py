# Standard library
# Third party library
# Local library


# Global variables are kept in a class to prevent from X import Y copying issues, as well
# as to allow for short and easy access to variables, hence the short class name...M for Masline
class M:
    # Contains one of two values, either "testing" or "production".
    # This helps to differentiate what's being worked on at a glance.
    icon_type = None
    # Dictionary containing WebSocket key, and a dictionary item. The
    # dictionary item will be constructed as follows (in no particular order, alphabetized is shown):
    #    "authorized":    This is a list of modules the current user is allowed to access. There
    #                        is no order that needs to be kept in this list and the easiest way to
    #                        check authority is by using an `in` statement.
    #    "username":        This is a convenience key, and it contains the coded username of the current
    #                        current user. It likely would never need to be known by the current user, but
    #                        it would make searching by other users easier.
    #    "timestamp":    This key is for authentication purposes, to prevent a user from doing anything malicious.
    #                        This is considered helpful assuming nothing malicious can occur in under 1 second, the
    #                        current timeout detection.
    #    "originating":    This key is also for authentication, to prevent cookie impersonations. If the originating IP
    #                        address differs from the IP address making the request, it is assumed the cookie has been
    #                        spoofed.
    # Keys that are optional, and may or may not be present:
    #    "module":        This is the current module that is selected and being executed against. All the
    #                        modules have the same interface:
    #                                Module(<database_instance>, <websocket>)    Returns an instance of the module
    #                                my_module.send_input(<data from client>)    Returns nothing
    users = {}
    user_sub = {"authorized": None, "username": None, "timestamp": None, "originating": None}
    # This dictionary is used for storing information before a websocket connection is established. It is meant
    # to handle information very temporarily and will pass information to `users` dictionary once a websocket
    # is established.
    # The key will be a UUID that is set and stored in the client as a secure cookie once they successfully login.
    # The key will point to another dictionary very similar to the previous dictionary item, with the intent to perform
    # a shallow copy once the handoff is complete.
    websocket_handoff = {}
    # Database instance shared among web server and individual modules
    db = None
    # A TextWrapper instance globally available for reuse
    wrapper = None
    # A dynamic dictionary of available modules, filled at beginning of run time, before the server is available
    mods = {}
    # A dictionary lookup for possible websocket close reasons. This dict is also stored in JSON in 'masline.js.socket()'
    ws_reasons = {
        None: "No reason provided",
        # 0 - 999 are reserved and will not be used
        1000: "JS called .close()",
        1001: "Browser closed connection",
        1002: "Protocol error",
        1003: "Received unknown data",
        # 1004 is reserved
        1005: "No status code provided; Typically self initiated .close()",
        1006: "Connection lost without an explicit .close()",
        1007: "Data was not of consistent type",
        1008: "Message violates policy",
        1009: "Message received was too big",
        1010: "Extensions not included in handshake",
        1011: "Server terminated because of unknown condition",
        # 1012 - 1014 are not listed
        1015: "TLS (encrypted) handshake failed",
        # 1016 - 1999 are reserved for future implementation
        # 2000 - 2999 are reserved for websocket extensions
        # 3000 - 3999 are reserved for frameworks
        # 4000 - 4999 are allowed for private usage
        4001: "Connection refused",
        4002: "Connection not found"
    }
