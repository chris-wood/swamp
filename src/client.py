#!/usr/bin/python

import sys
from swamp_pb2 import *
from trees import *
from repo import *
sys.path.append('/Users/cwood/Projects/PARC/Repo/build/lib/python2.7/site-packages')

import os, time, tempfile, json, getopt, torrent
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

def add_to_repo(repo, node): # THE HASH IS THE NAME!
    repo.add(node.hash(), node.toJSON())
    if "Manifest" == node.type():
        for child in node.nodes:
            add_to_repo(repo, child)


def usage(argv):
    # TODO: fix this.
    print "Usage: %s [-h ] [[-l | -lci] lci:/name/to/send/to] <payload string>" % argv[0]

def parse_args(argv):
    name_prefix = None
    repoPrefix = None
    storageLocation = None
    try:
        opts, args = getopt.getopt(argv[1:], "n:r:s:hd", ["name=", "repo=", "storage="])
    except getopt.GetoptError:
        usage(argv)
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage(argv)
            sys.exit()
        elif opt == '-d':
            global _debug
            _debug = 1
        elif opt in ("-l", "--lci"):
            name_prefix = arg
            print "Will send to name [ %s ]" % name_prefix

    return (name_prefix, " ".join(args)) # listenPrefix, Everything left over

def load_data(fname, repo):
    data = None
    with open(fname, "rb") as fh:
        data = fh.read()

    chunker = Chunker(data)
    root = build_skewed_tree(chunker)

    return root

def upload_data(client, fname, repo):
    root = load_data(fname, repo)

    if root:
        rootNode = root.toJSON()
        print rootNode, fname
        if not repo.contains(fname):
            print >> sys.stderr, "The file was not in the repo. We're adding it now..."
            add_to_repo(repo, root)
            repo.add(fname, rootNode)

        torrent = UploadRequest()
        torrent.torrent.owner = storage_prefix # TODO: rename storage_prefix to something else
        torrent.torrent.seeders.append(storage_prefix)
        torrent.torrent.fname = fname
        torrent.torrent.root = rootNode
        # torrent.signature = XXX

        uploadRequest = torrent.SerializeToString()
        response_data = client.get(name_prefix + "/upload", uploadRequest)

        response = Ack()
        response.ParseFromString(response_data)

        print "Upload[%d]: %s" % (response.code, response.message)

def fetch_data(client, name_prefix, name):
    response = client.get(name_prefix + "/fetch/" + name)
    data_torrent = Torrent()
    if data_torrent.ParseFromString(payload):
        print "FETCH THE MANIFEST", data_torrent

def run(name_prefix, storage_prefix):
    client = CCNxClient()
    repo = FileRepo(storage_prefix, "repo")

    cmd = raw_input("> ").strip()
    splits = cmd.split(" ")

    while splits[0] != "quit":
        if splits[0] == "put":
            upload_data(client, splits[1], repo)
        if splits[0] == "fetch":
            fetch_data(client, name_prefix, splits[1])
        else:
            print "Unsupported command."

        cmd = raw_input("> ").strip()
        splits = cmd.split(" ")

if __name__ == "__main__":
    args = parse_args(sys.argv[1:])

    # TODO: handle the arguments here.

    name_prefix = "lci:/tracker"
    storage_prefix = "lci:/chris"

    run(name_prefix, storage_prefix)
