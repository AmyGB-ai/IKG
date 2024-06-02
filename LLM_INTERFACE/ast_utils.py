import ast, sys, time

# Define a NodeVisitor class to traverse the AST
class CodeAnalyzer(ast.NodeVisitor):

    def __init__(self):
        self.ast_linewise_deets_ = dict()
        self.file_ptr_ = None
    
    def parse_ast( self, file_nm_, range_):
        self.file_ptr_ = open( file_nm_, 'r' )
        code = self.file_ptr_.readlines()[ range_[0]: range_[1] ]
        code = '\n'.join( code )
        # Parse the code into an AST
        return ast.parse(code)

    def gc(self):
        if self.file_ptr_ != None:
            self.file_ptr_.close()

    def visit_Assign(self, node):
        # Check for direct assignments
        targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        value = node.value
        value_names = self.get_names(value)
        print(f"Assignment: Line {node.lineno}, Targets: {targets}, Values: {value_names}")
        self.ast_linewise_deets_[ node.lineno ] = { 'Type':'Assignment', 'Targets': targets }
        self.generic_visit(node)

    def visit_If(self, node):
        # Handle if statements
        test_names = self.get_names(node.test)
        print(f"If statement: Line {node.lineno}, End {node.body[-1].lineno} ,Condition Variables: {test_names}")
        self.ast_linewise_deets_[ node.lineno ] = { 'Type':'If Statement', 'Targets': test_names , 'Ending': node.body[-1].lineno }
        self.generic_visit(node)

    def visit_For(self, node):
        # Handle for loops
        target = node.target.id if isinstance(node.target, ast.Name) else str(node.target)
        iter_names = self.get_names(node.iter)
        self.ast_linewise_deets_[ node.lineno ] = { 'Type':'For loop',  'Targets': iter_names, 'Ending': node.body[-1].lineno }
        print(f"For loop: Line {node.lineno}, End {node.body[-1].lineno} ,Loop Variable: {target}, Iterating Over: {iter_names}")
        self.generic_visit(node)

    def get_names(self, node):
        # Helper function to extract variable names from nodes
        if isinstance(node, ast.Name):
            return [node.id]
        elif isinstance(node, ast.BinOp):
            return self.get_names(node.left) + self.get_names(node.right)
        elif isinstance(node, ast.BoolOp):
            names = []
            for value in node.values:
                names.extend(self.get_names(value))
            return names
        elif isinstance(node, ast.Compare):
            names = self.get_names(node.left)
            for comp in node.comparators:
                names.extend(self.get_names(comp))
            return names
        elif isinstance(node, ast.Call):
            names = self.get_names(node.func)
            for arg in node.args:
                names.extend(self.get_names(arg))
            return names
        elif isinstance(node, ast.Attribute):
            return self.get_names(node.value) + [node.attr]
        elif isinstance(node, ast.Subscript):
            return self.get_names(node.value) + self.get_names(node.slice)
        elif isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            names = []
            for elt in node.elts:
                names.extend(self.get_names(elt))
            return names
        elif isinstance(node, ast.Dict):
            names = []
            for key in node.keys:
                names.extend(self.get_names(key))
            for value in node.values:
                names.extend(self.get_names(value))
            return names
        else:
            return []

if __name__ == "__main__":
    # Instantiate the analyzer and visit the AST nodes
    analyzer = CodeAnalyzer()
    analyzer.visit(parsed_ast)

    print( analyzer.ast_linewise_deets_ )
    print( 'DOMU->', time.time() - start_ )
