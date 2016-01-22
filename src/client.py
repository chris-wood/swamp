#!/usr/bin/python

# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

# DO NOT ALTER OR REMOVE COPYRIGHT NOTICES OR THIS FILE HEADER.
# Copyright 2015 Palo Alto Research Center, Inc. (PARC), a Xerox company.  All Rights Reserved.
# The content of this file, whole or in part, is subject to licensing terms.
# If distributing this software, include this License Header Notice in each
# file and provide the accompanying LICENSE file.

# @author Alan Walendowski, System Sciences Laboratory, PARC
# @copyright 2015 Palo Alto Research Center, Inc. (PARC), A Xerox Company. All Rights Reserved.

import sys
from trees import *
from repo import *
sys.path.append('/Users/cwood/Projects/PARC/Review/build/lib/python2.7/site-packages')

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

def add_to_repo(repo, node):
    # THE HASH IS THE NAME!
    repo.add(node.hash(), node.toJSON())
    if "Leaf" == node.type():
        pass
    else: # "Manifest"
        for child in node.nodes:
            add_to_repo(repo, child)

def usage(argv):
    # TODO: fix this.
    print "Usage: %s [-h ] [[-l | -lci] lci:/name/to/send/to] <payload string>" % argv[0]

def parse_args(argv):
    namePrefix = None
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
            namePrefix = arg
            print "Will send to name [ %s ]" % namePrefix

    return (namePrefix, " ".join(args)) # listenPrefix, Everything left over

if __name__ == "__main__":
    namePrefix = "lci:/tracker"
    myStoragePrefix = "lci:/chris"

    repo = FileRepo(myStoragePrefix, "repo")

    data = None
    dataname = sys.argv[1]
    with open(dataname, "rb") as fh:
        data = fh.read()

    chunker = Chunker(data)
    root = build_skewed_tree(chunker)

    if root:
        rootNode = root.toJSON()
        print rootNode, dataname
        if not repo.contains(dataname):
            print >> sys.stderr, "The file was not in the repo. We're adding it now..."
            add_to_repo(repo, root)
            repo.add(dataname, rootNode)

        uploadRequest = json.dumps({"fname": dataname, "owner": myStoragePrefix, "root": rootNode})

        portal = open_portal()

        ### 1. Upload the root manifest.
        interest = Interest(Name(namePrefix + "/upload"))
        interest.setPayload(uploadRequest)
        portal.send(interest)

        print interest.name

        received = False
        while not received:
            message = portal.receive()
            print message
            if isinstance(message, Interest):
                print "Received Interest: ", str(message)
            elif isinstance(message, ContentObject):
                print "Received content message: ", str(message)
                payload = message.getPayload()
                if payload:
                    print "Data: ", payload
                received = True

        ### 2. Fetch the root manifest for the thing you want
        interest = Interest(Name(namePrefix + "/fetch/big.bin"))
        portal.send(interest)

        message = portal.receive()
        if isinstance(message, Interest):
            print "Received Interest: ", str(message)
        elif isinstance(message, ContentObject):
            print "Received content message: ", str(message)

        payload = message.getPayload()
        if payload:
            print "Data", payload

            tracker = json.loads(payload)
            prefix = tracker["owner"]
            manifest = json.loads(tracker["root"])

            # Recursively fetch with the root manifest.
            chunks = []
            digests = manifest["contents"]
            while len(digests) > 0:
                digest = digests[0]
                digests = digests[1:]

                print "I WOULD FETCH FOR %s" % (prefix)
                break

#                interest = Interest(Name(prefix))
#                interest.setContentObjectHashRestriction(digest)
#
#                portal.send(interest)
#                message = portal.receive()
#                payload = message.getPayload()
#
#                try:
#                    newmanifest = json.loads(payload)
#                    digests.append(newmanifest["contents"])
#                except:
#                    chunks.append(payload)

            print "!!DONE TRANSFERRING THE FILE!!"
            print chunks
