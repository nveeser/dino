#!/usr/bin/env python
"""
This is the main entry point into mod_wsgi for the client.

mod_wsgi will look for a global object in this file called
'application' and cache it in memory, expecting it to be a valid WSGI
application.
"""

import os, sys
from paste.deploy import loadapp, loadserver

application = loadapp('config:/etc/dino/dinoweb.ini')

if __name__ == "__main__":
    server = loadserver(me_spec)
    server(application)

