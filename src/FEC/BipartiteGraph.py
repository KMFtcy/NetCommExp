class BipartiteGraph:
    def __init__(self):
        self.left_nodes = {}
        self.right_nodes = {}

    def add_edge(self, left, right):
        if left not in self.left_nodes:
            self.left_nodes[left] = set()
        if right not in self.right_nodes:
            self.right_nodes[right] = set()
        self.left_nodes[left].add(right)
        self.right_nodes[right].add(left)

    def remove_edge(self, left, right):
        if left in self.left_nodes and right in self.left_nodes[left]:
            self.left_nodes[left].remove(right)
            if not self.left_nodes[left]:
                del self.left_nodes[left]
        if right in self.right_nodes and left in self.right_nodes[right]:
            self.right_nodes[right].remove(left)
            if not self.right_nodes[right]:
                del self.right_nodes[right]

    def get_neighbors(self, node, side='left'):
        if side == 'left':
            return self.left_nodes.get(node, set())
        else:
            return self.right_nodes.get(node, set())

    def get_degree(self, node, side='left'):
        if side == 'left':
            return len(self.left_nodes.get(node, set()))
        else:
            return len(self.right_nodes.get(node, set()))

    def print_graph(self):
        print("Left nodes and their neighbors:")
        for left, neighbors in self.left_nodes.items():
            print(f"{left}: {neighbors}")
        print("Right nodes and their neighbors:")
        for right, neighbors in self.right_nodes.items():
            print(f"{right}: {neighbors}")

    def adjacency_matrix(self):
        left_nodes = sorted(self.left_nodes.keys())
        right_nodes = sorted(self.right_nodes.keys())
        matrix = [[0] * len(left_nodes) for _ in range(len(right_nodes))]
        for i, right in enumerate(right_nodes):
            for j, left in enumerate(left_nodes):
                if right in self.left_nodes.get(left, set()):
                    matrix[i][j] = 1
        return matrix    

if __name__ == "__main__":
    # Example usage
    graph = BipartiteGraph()
    graph.add_edge('A', 1)
    graph.add_edge('A', 2)
    graph.add_edge('B', 2)
    graph.add_edge('B', 3)
    graph.add_edge('C', 3)

    print("Initial graph:")
    graph.print_graph()

    print("\nDegrees of nodes:")
    print(f"Degree of 'A': {graph.get_degree('A', 'left')}")
    print(f"Degree of 'B': {graph.get_degree('B', 'left')}")
    print(f"Degree of 'C': {graph.get_degree('C', 'left')}")
    print(f"Degree of 1: {graph.get_degree(1, 'right')}")
    print(f"Degree of 2: {graph.get_degree(2, 'right')}")
    print(f"Degree of 3: {graph.get_degree(3, 'right')}")

    graph.remove_edge('A', 2)
    print("\nGraph after removing edge (A, 2):")
    graph.print_graph()

    graph.remove_edge('B', 2)
    print("\nGraph after removing edge (B, 2):")
    graph.print_graph()