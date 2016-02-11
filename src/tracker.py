#!/usr/bin/python

import sys, tempfile, getopt, time, json, random, sqlite3

from repo import *
from CCNx import *

from swamp_pb2 import *

def now_in_millis():
    return int(round(time.time() * 1000))

def setup_identity():
    global IDENTITY_FILE
    IDENTITY_FILE = tempfile.NamedTemporaryFile(suffix=".p12")
    identity = create_pkcs12_keystore(IDENTITY_FILE.name, "foobar", "bletch", 1024, 10)
    return identity

def open_portal():
    identity = setup_identity()
    factory = PortalFactory(identity)
    portal = factory.create_portal()
    return portal

def send_and_wait_for_response(portal, message):
        portal.send(message)

        response = None
        while not response:
            response = portal.receive()

        if response and isinstance(response, ContentObject):
            print response.payload.value

class Tracker(object):
    def __init__(self, name):
        self.name = name
        self.files = {}
        self.repo = FileRepo("tracker-repo")

    def handle_command(self, command, params, payload):
        if command == "upload":
            return self.upload(payload)
        elif command == "fetch":
            return self.fetch(params)

    def upload(self, fpayload):
        request = UploadRequest()
        request.ParseFromString(fpayload)

        # TODO: verify the signature if needed 

        torrent = request.torrent
        fname = torrent.fname

        if not self.repo.contains(fname):
            self.repo.add(fname, torrent.SerializeToString())
            ack = Ack()
            ack.code = Ack.Ok
            ack.message = "OK"
            return ack.SerializeToString()
        else:
            ack = Ack()
            ack.code = Ack.Error
            ack.message = "Error: file %s already exists in the tracker" % (fname)
            return ack.SerializeToString()

    def fetch(self, name_components):
        name = "/".join(name_components)
        if not self.repo.contains(name):
            ack = Ack()
            ack.code = Ack.Error
            ack.message = "File '%s' not found" % (name)
            return ack.SerializeToString()
        else:
            return self.repo.get(name) # this is already serialized

def main(lciPrefix = "lci:/tracker"):
    try:
        portal = open_portal()

        listenName = Name(lciPrefix)
        portal.listen(listenName)

        commandOffset = len(listenName)

        tracker = Tracker(listenName)

        keepRunning = True
        while keepRunning:
            message = portal.receive()

            print "Tracker received %s" % (str(message.name))

            name = str(message.name)[len(lciPrefix):]
            nameComponents = name.split('/')

            if len(name) == commandOffset:
                pass

            command = str(nameComponents[commandOffset])
            responseData = tracker.handle_command(command, nameComponents[(commandOffset+1):], message.getPayload())
            portal.send(ContentObject(message.name, responseData))

    except Portal.CommunicationsError as x:
        sys.stderr.write("sender: comm error attempting to listen: %s\n" % (x.errno,))

if __name__ == "__main__":
    main()
