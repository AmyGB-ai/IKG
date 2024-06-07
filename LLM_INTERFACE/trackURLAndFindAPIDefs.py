import ast
import os
import re

class URLAssignmentFinder(ast.NodeVisitor):
    def __init__(self, file_path):
        self.url_assignments = {}
        self.fp_ = file_path

    def _get_name_or_constant(self, node, refln):
        if isinstance(node, ast.Name):
            key_ = self.fp_ +'#'+ node.id +'#' + str(refln)
            if key_ in self.url_assignments:
                return node.id, self.url_assignments[key_]
        elif isinstance(node, ast.Constant):
            return node, node.value
        return None, None        

    def visit_Assign(self, node):

        if isinstance(node.value, ast.Str):
            url = node.value.s
            if re.match(r'http?', url):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        print( 'GATHERING ->', self.fp_, target.id, url, node.lineno )
                        self.url_assignments[ self.fp_ +'#'+ target.id +'#' + str(node.lineno)] = url

        # Check if the value is a concatenation involving a URL variable
        elif isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Add):
            tmpd_ = {}
            for composite_key, url_ in self.url_assignments.items():
                key_fp, key_tgt_id, key_ln_no = composite_key.split('#')

                left_ref_val_, left_value = self._get_name_or_constant(node.value.left, key_ln_no)
                rt_ref_val_, right_value = self._get_name_or_constant(node.value.right, key_ln_no)

                if left_ref_val_ == key_tgt_id:
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            full_url = url_ + right_value
                            tmpd_[ key_fp + '#' + target.id + '#' + str(node.lineno) ] = full_url

            if len( tmpd_ ) > 0:
                print('ADDING EXTENDED->', tmpd_)
                self.url_assignments.update( tmpd_ )

        self.generic_visit(node)

def parse_files_in_directory(directory):
    file_paths = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_paths.append(os.path.join(root, file))
    return file_paths

def parse_file(file_path):
    with open(file_path, "r") as source:
        return ast.parse(source.read(), filename=file_path)

def find_url_assignments(directory):
    url_assignments = {}
    file_paths = parse_files_in_directory(directory)
    for file_path in file_paths:
        tree = parse_file(file_path)
        finder = URLAssignmentFinder(file_path)
        finder.visit(tree)
        if finder.url_assignments:
            url_assignments[file_path] = finder.url_assignments
    return url_assignments

class URLUsageFinder(ast.NodeVisitor):
    def __init__(self, url_variables, file_path):
        self.url_variables = url_variables
        self.url_usages = []
        self.current_target = None
        self.file_path = file_path

    def visit_Assign(self, node):
        # Store the target variable(s) of the assignment
        self.current_target = [target.id for target in node.targets if isinstance(target, ast.Name)]
        self.generic_visit(node)
        self.current_target = None  # Reset after processing

    def visit_Call(self, node):

        if not isinstance(node.func, ast.Name):
            print('visit_Call->', self.file_path, isinstance(node.func, ast.Attribute), node.func.attr, node.lineno)

        if isinstance(node.func, ast.Attribute) and \
                node.func.attr in {'post', 'get', 'put', 'delete', 'patch', 'POST', 'GET', 'PUT'}:

            if 'test_config_py_usage' in self.file_path:
              print( 'TRACKING ', node.lineno, node.args, node.keywords[0], isinstance(node.args[0], ast.Name  ) if node.args else None )
            if node.args and isinstance(node.args[0], ast.Name):
                for url_var in self.url_variables:
                    url_fp, url_variable_, url_defined_line_ = url_var.split('#')

                    #if node.args[0].id == url_variable_ and url_fp == self.file_path and\
                    if node.args[0].id == url_variable_ and \
                      ( 
                        ( url_fp == self.file_path \
                            and int( url_defined_line_ ) < node.lineno\
                            and ( len( self.url_usages ) == 0 or \
                                       ( len( self.url_usages ) > 0 \
                                          and ( int( self.url_usages[-1][1] ) < int(url_defined_line_) )
                                       )
                                )
                        )\
                        or \
                        ( url_fp != self.file_path )
                      ):
                                ## the last condition just ensures that the url assignmnt is aligned with the
                                ## usage ..meaning IF the same variable name is being used in different methods
                                ## the usage is tracked to the varriable declared AFTER the most recent usage
                      self.url_usages.append(( url_fp, url_defined_line_, node.lineno, \
                                                       node.col_offset, node.func.attr))

            elif node.keywords :
                for keyword in node.keywords:
                    for url_var in self.url_variables:
                        url_fp, url_variable_, url_defined_line_ = url_var.split('#')
                        print('TRACTOR-> keyword.value, url_variable_ ', keyword.value.id, url_variable_ )
                        #if keyword.value == url_variable_ and url_fp == self.file_path and\
                        if isinstance( keyword.value, ast.Name ) and keyword.value.id == url_variable_ and \
                          ( 
                            ( url_fp == self.file_path \
                                  and int( url_defined_line_ ) < node.lineno \
                                  and ( len( self.url_usages ) == 0 or \
                                            ( len( self.url_usages ) > 0 \
                                               and ( int( self.url_usages[-1][1] ) < int(url_defined_line_) )
                                            )
                                      ) 
                            )\
                            or\
                            ( url_fp != self.file_path ) 
                          ):
                                    ## the last condition just ensures that the url assignmnt is aligned with the
                                    ## usage ..meaning IF the same variable name is being used in different methods
                                    ## the usage is tracked to the varriable declared AFTER the most recent usage
                          self.url_usages.append(( url_fp, url_defined_line_, node.lineno, \
                                                           node.col_offset, node.func.attr))

        elif not isinstance(node.func, ast.Name) and node.func.attr == 'Request':
                print('GOLI->', self.file_path, node.lineno, node.keywords, self.current_target, node.args)

                for keyword in node.keywords:

                    if keyword.arg in [ 'url', 'data' ] and isinstance(keyword.value, ast.Name):
                        for url_var in self.url_variables:
                            url_fp, url_variable_, url_defined_line_ = url_var.split('#')

                            for arg in node.args:
                              if isinstance( arg, ast.Name ) and arg.id == url_variable_ and \
                                      ( 
                                        ( 
                                              ( url_fp == self.file_path and \
                                                      int( url_defined_line_ ) < node.lineno )
                                        )\
                                        or\
                                        ( url_fp != self.file_path )
                                      ):

                                 self.url_usages.append(( url_fp, url_defined_line_, node.lineno, node.col_offset, \
                                                         node.func.attr))

        self.generic_visit(node)

def find_url_usages(directory, url_assignments):
    url_usages = {}
    file_paths = parse_files_in_directory(directory)
    for file_path in file_paths:
        for ref_file_path in list( url_assignments.keys() ):
            url_variables = url_assignments[ ref_file_path ]
            tree = parse_file(file_path)
            finder = URLUsageFinder(url_variables, file_path)
            finder.visit(tree)
            if finder.url_usages:
                url_usages[file_path] = finder.url_usages
    return url_usages

def main(directory):
    # Step 1: Find URL assignments
    url_assignments = find_url_assignments(directory)
    print("URL Assignments Found:")
    for file_path, urls in url_assignments.items():
        for var, url in urls.items():
            print(f"File: {file_path}, Variable: {var}, URL: {url}")

    # Step 2: Find URL usages
    url_usages = find_url_usages(directory, url_assignments)
    print("\nURL Usages Found:")
    for file_path, usages in url_usages.items():
        for file_defined_, defined_line_, lineno, col_offset, method in usages:
            print(f"File: {file_path}, File Defined: { file_defined_ } , Defined: {defined_line_}, UsedLine: {lineno}, \
                  Column: {col_offset}, Method: {method}")

# Example usage
main('/datadrive/IKG/LLM_INTERFACE/SRC_DIR/')

