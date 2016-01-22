import json

class ManifestReference(object):
    def __init__(self, name, tree_node):
        self.name = name
        self.tree_node = tree_node
        self.root = Manifest(tree_node)

    def toJSON(self):
#        return json.dumps({"name": name, "sections": map(lambda s : s.toJSON(), self.sections)})
        pass

class Manifest(object):
    def __init__(self, root):
        self.node = None

        # walk each of the children in the list and construct the hashes
        for child in root.nodes:
            if child.type() == "Manifest":
                pass
            elif child.type() == "Leaf":
                pass
