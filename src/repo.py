import sys
import os
import threading

from ccnkv import *
from CCNx import *

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

# a poor man's repo.
# TODO: make this an abstract class with different instances -> FileRepo, SQLiteRepo, MongoDbRepo, etc.

class FileRepo(object):
    def __init__(self, prefix, path = "/tmp/ccnx/repo"):
        try:
            self.path = path
            os.makedirs(path)

            self.prefix = prefix
            self.client = CCNxClient(prefix)

            self.running = True
            self.d = threading.Thread(name='repodaemon', target=self.run)
            self.d.setDaemon(True)

            self.d.start()
        except Exception as e:
            print >> sys.stderr, "Directory %s exists" % (path)

        self.files = []
        self.load()

    def run(self):
        self.client.listen(self.prefix)
        while self.running:
            name, data = self.client.receive()
            fname = name.replace(self.name, "")

            data = None
            if self.contains(fname):
                data = json.dumps({"status": "OK", "data" : self.get(fname)})
            else:
                data = json.dumps({"status": "ERROR-DNE"})
            self.client.reply(name, data)

    def load(self):
        for fname in os.listdir(self.path):
            print >> sys.stderr, "\tREPO: loading %s" % (fname)
            self.files.append(fname)

    def full_path(self, name):
        return os.path.join(self.path, name)

    def contains(self, fname):
        return fname in self.files

    def get(self, fname):
        if fname in self.files:
            with open(self.full_path(fname), "r") as fh:
                return fh.read()
        else:
            raise Exception("File %s not present in the repository." % (fname))

    def add(self, fname, contents):
        with open(self.full_path(fname), "w") as fh:
            fh.write(contents)
        self.files.append(fname)

    def append(self, fname, contents):
        with open(self.full_path(fname), "a") as fh:
            fh.write(contents)

    def delete(self, fname):
        if fname in self.files:
            os.remove(self.full_path(fname))

    def __str__(self):
        return "Path %s %s" % (self.path, "\n\t".join(self.files))
