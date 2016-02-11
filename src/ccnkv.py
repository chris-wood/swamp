#!/usr/bin/python

import sys, tempfile, time, json, random, errno, os, threading

sys.path.append('/Users/cwood/Projects/PARC/Repo/build/lib/python2.7/site-packages')
from CCNx import *
from swamp_pb2 import *

class CCNxClient(object):
    def __init__(self, async = False):
        if async:
            self.portal = self.openAsyncPortal()
        else:
            self.portal = self.openPortal()

    def setupIdentity(self):
        global IDENTITY_FILE
        IDENTITY_FILE = tempfile.NamedTemporaryFile(suffix=".p12")
        identity = create_pkcs12_keystore(IDENTITY_FILE.name, "foobar", "bletch", 1024, 10)
        return identity

    def openPortal(self):
        identity = self.setupIdentity()
        factory = PortalFactory(identity)
        portal = factory.create_portal()
        return portal

    def openAsyncPortal(self):
        identity = self.setupIdentity()
        factory = PortalFactory(identity)
        portal = factory.create_portal(transport=TransportType_RTA_Message, attributes=PortalAttributes_NonBlocking)
        return portal

    def get(self, name, data = ""):
        interest = Interest(Name(name), payload=data)
        self.portal.send(interest)
        response = self.portal.receive()
        if isinstance(response, ContentObject):
            return response.getPayload()
        else:
            return None

    def get_by_identifier(self, name, identifier):
        interest = Interest(Name(name), content_object_hash=identifier)
        self.portal.send(interest)
        response = self.portal.receive()
        if isinstance(response, ContentObject):
            return response.getPayload()
        else:
            return None

    def get_async(self, name, data, timeout_seconds):
        interest = None
        if data == None:
            interest = Interest(Name(name))
        else:
            interest = Interest(Name(name), payload=data)

        for i in range(timeout_seconds):
            try:
                self.portal.send(interest)
                response = self.portal.receive()
                if response and isinstance(response, ContentObject):
                    return response.getPayload()
            except Portal.CommunicationsError as x:
                if x.errno == errno.EAGAIN:
                    time.sleep(1)
                else:
                    raise
        return None

    def force_push(self, name, data):
        interest = Interest(Name(name), payload=data)
        try:
            self.portal.send(interest)
        except Portal.CommunicationsError as x:
            sys.stderr.write("ccnxPortal_Write failed: %d\n" % (x.errno,))
        pass

    def push(self, name, data, prefix):
        # 1. chunk the data
        chunks = []
        chunker = Chunker(data)
        for chunk in chunker:
            chunks.append(chunks)

        # 2. send a pull request
        request = PullRequest()
        request.name = prefix
        request.chunks = len(chunks)
        interest = Interest(Name(name), payload=request.SerializeToString())
        try:
            self.portal.send(interest)
        except Portal.CommunicationsError as x:
            sys.stderr.write("ccnxPortal_Write failed: %d\n" % (x.errno,))
        pass

        # 3. respond to each chunk
        sent = []
        num_chunks = len(chunks)
        while (len(sent) < num_chunks):
            name, payload = self.receive_raw()
            if name.startsWith(prefix):
                chunk_number = int(name[-1])
                chunk = chunks[chunk_number]
                self.reply(name, chunk)

                if chunk_number not in sent:
                    sent.append(chunk_number)
            else:
                pass

    def listen(self, prefix):
        try:
            self.portal.listen(Name(prefix))
        except Portal.CommunicationsError as x:
            sys.stderr.write("CCNxClient: comm error attempting to listen: %s\n" % (x.errno,))
        return True

    def receive(self):
        request = self.portal.receive()
        if isinstance(request, Interest):
            return str(request.name), request.getPayload()
        else:
            pass
        return None, None

    def receive_raw(self):
        request = self.portal.receive()
        if isinstance(request, Interest):
            return request.name, request.getPayload()
        else:
            pass
        return None, None

    def reply(self, name, data):
        try:
            self.portal.send(ContentObject(Name(name), data))
        except Portal.CommunicationsError as x:
            sys.stderr.write("reply failed: %d\n" % (x.errno,))
