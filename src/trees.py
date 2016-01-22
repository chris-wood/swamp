import sys
import argparse
import networkx as nx
import hashlib
import json

LEAF_SIZE_LIMIT = (64*1024) - 256 # leave some room for packet shenanigans
NODE_SIZE_LIMIT = (64*512) - 256  # smaller to start

class Node(object):
    def __init__(self, name = ""):
        self.name = name
        self.limit = NODE_SIZE_LIMIT
        self.size = 0
        self.nodes = []
        self.parent = None
        self.sibling = None

    def insert_node(self, node):
        if self.size < self.limit:
            self.nodes.append(node)
            self.size += (32 + 4) # 32 bytes for the hash, and 4 bytes for the pointer
            return True
        else:
            return False

    def empty_clone(self):
        node = Node(self.name)
        for child in self.nodes:
            node.insert_node(child.empty_clone())
        return node

    def display(self, out = sys.stdout, prefix = "  ", indents = 0):
        print >> out, (prefix * indents) + self.name + ":"
        for node in self.nodes:
            node.display(out, prefix, indents + 1)

    def type(self):
        return "Manifest"

    def hash(self):
        h = hashlib.new('sha256')
        hashes = map(lambda n : n.hash(), self.nodes)
        for value in hashes:
            h.update(value)
        return h.hexdigest()

    # TODO: rename to serialize!
    def toJSON(self):
        hashes = map(lambda n : n.hash(), self.nodes)
        return json.dumps({"type": self.type(), "contents": str(hashes)})

class Leaf(Node):
    def __init__(self, name = ""):
        self.name = name
        self.data = []
        self.size = 0
        self.parent = None
        self.limit = LEAF_SIZE_LIMIT

    def add_data(self, data):
        if self.size + len(data) <= self.limit:
            self.data.append(data)
            self.size += len(data)
            return True
        else:
            return False

    def empty_clone(self):
        return Leaf(self.name)

    def type(self):
        return "Leaf"

    def display(self, out = sys.stdout, prefix = "  ", indents = 0):
        print >> out, (prefix * indents) + self.name + ":"
        for data in self.data:
            print >> out, (prefix * (indents + 1)), data

    def hash(self):
        h = hashlib.new('sha256')
        h.update("".join(self.data))
        return h.hexdigest()

    # TODO: rename to serialize!
    def toJSON(self):
        return "".join(self.data)

class Chunker(object):
    def __init__(self, data, chunksize = 4096):
        self.chunksize = chunksize
        self.data = data
        self.limit = len(data)
        self.index = 0

    def __iter__(self):
        while self.index < self.limit:
            yield self.data[self.index:(self.index + self.chunksize)]
            self.index += self.chunksize

def build_skewed_tree(chunker):
    index = 0
    node_index = 0

    node = Leaf("/leaf/%d" % (index))
    index += 1
    root = None

    for chunk in chunker:
        success = node.add_data(chunk)
        if not success:
            if root == None:
                root = Node("/node/%d" % (node_index))
                node_index += 1

            success = root.insert_node(node)
            if not success:
                new_parent = Node("/node/%d" % (node_index))
                node_index += 1
                new_parent.insert_node(root)
                new_parent.insert_node(node)
                root = new_parent

            node = Leaf("/leaf/%d" % (index))
            index += 1
            node.add_data(chunk)
            
    if root == None:
        root = Node("/node/0")
        root.insert_node(node)

    return root

def build_level(lowerlevel, node_index = 0):
    level = []
    num_nodes = ((len(lowerlevel) - 1) / NODE_SIZE_LIMIT) + 1
    index = 0
    for x in range(num_nodes):
        node = Node("/node/%d" % (node_index))
        node_index += 1
        for y in range(NODE_SIZE_LIMIT):
            if index < len(lowerlevel):
                node.insert_node(lowerlevel[index])
                index += 1
        level.append(node)
    return level, node_index

def overlay_tree(leaves):
    level, index = build_level(leaves)
    while len(level) > 1:
        level, index = build_level(level, index)
    return level[0]

def build_flat_tree(chunker):
    index = 0

    leaves = []
    leaf = Leaf("/leaf/%d" % (index))
    index += 1

    for chunk in chunker:
        success = leaf.add_data(chunk)
        if not success:
            leaves.append(leaf)
            leaf = Leaf("/leaf/%d" % (index))
            index += 1
            leaf.add_data(chunk)

    root = overlay_tree(leaves)
    return root

def main(argv):

    desc = '''
Play around with different data tree construction strategies.
'''

    parser = argparse.ArgumentParser(prog='trees', formatter_class=argparse.RawDescriptionHelpFormatter, description=desc)
    parser.add_argument('-n', action="store", default=256, required=False, help="Size of sequential data stream")
    args = parser.parse_args()

    n = int(args.n)
    data = [x for x in range(0, n)]

    # Skewed tree
    chunker = Chunker(data, 32)
    root = build_skewed_tree(chunker)
    if root:
        root.display(sys.stdout)

    # Flat tree
    chunker = Chunker(data, 32)
    root = build_flat_tree(chunker)
    if root:
        root.display(sys.stdout)

if __name__ == "__main__":
    main(sys.argv)
