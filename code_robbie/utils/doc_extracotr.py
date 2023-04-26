"""
# Python Documentation Extractor
Python Documentation Extractor is a command-line tool that recursively scans
a Python project and generates a plain-text report with the documentation of
classes, functions, and file docstrings.

Features:
- Recursively scans all Python files in a project directory
- Extracts file docstrings, class docstrings, and function docstrings
- Generates a plain-text report with extracted documentation
- Truncates long docstrings and indicates with "... (text clipped)"
- Ignores third-party libraries

usage:
    python doc_extractor.py /path/to/your/project
"""
import ast
import os
import sys
import textwrap


class DocExtractor(ast.NodeVisitor):
    def __init__(self):
        self.file_docstring = None
        self.extracted_docs = []

    def visit_Module(self, node):
        if ast.get_docstring(node):
            self.file_docstring = prep_docstring(ast.get_docstring(node), max_len=12)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        name = node.name
        args = ", ".join(arg.arg for arg in node.args.args)
        docstring = ast.get_docstring(node) or ""
        self.extracted_docs.append(f'- function: {name}({args}):\n{prep_docstring(docstring)}')
        if len(docstring) > 0:
            self.extracted_docs.append("\n")
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        name = node.name
        docstring = ast.get_docstring(node) or ""
        self.extracted_docs.append(f'- class: {name}:\n{prep_docstring(docstring)}')
        if len(docstring) > 0:
            self.extracted_docs.append("\n")
        self.generic_visit(node)


def extract_doc(file_content):
    tree = ast.parse(file_content)
    extractor = DocExtractor()
    extractor.visit(tree)

    extracted_docs = []
    if extractor.file_docstring:
        extracted_docs = [extractor.file_docstring, "\n"]
    extracted_docs.extend(extractor.extracted_docs)
    return "\n".join(extracted_docs)


# def prep_docstring(docstring: str) -> str:
#     docstring = textwrap.dedent(docstring.strip())
#     return textwrap.indent(docstring, '  ')

def prep_docstring(docstring: str, max_len=6) -> str:
    docstring = textwrap.dedent(docstring.strip())
    docstring_lines = docstring.splitlines()

    # Remove blank lines
    docstring_lines = [line for line in docstring_lines if line.strip()]

    # Process the lines to meet the specified conditions
    clipped = False
    continuous_lines = 0
    index_to_stop = 0

    for i, line in enumerate(docstring_lines):
        if continuous_lines >= max_len:
            clipped = True
            break

        if line.strip():
            continuous_lines += 1
            index_to_stop = i + 1
        else:
            continuous_lines = 0

    # let the reader know if the text is truncated.
    if clipped:
        docstring_lines = docstring_lines[:index_to_stop]
        docstring_lines[-1] += "   ... (text clipped)"

    # Join the lines and indent
    docstring = "\n".join(docstring_lines)
    return textwrap.indent(docstring, '    # ')


def get_all_files_recursive(path):
    python_files = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".py") and file not in ["__init__.py", "__main__.py"]:
                python_files.append(os.path.join(root, file))
    return python_files


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python doc_extractor.py <project_path>")
        sys.exit(1)

    project_path = sys.argv[1]

    python_files = get_all_files_recursive(project_path)

    print("I'd like to look at this auto generated text describing a code base. Can you understand the text? if so, please briefly summarise the code base.")
    print("-" * 80)

    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
            doc = extract_doc(file_content)
            if doc:
                doc = doc.replace("\n\n", "\n")
                relative_path = os.path.relpath(file_path, project_path)
                print(f"File: {relative_path}\n{doc}\n{'-' * 80}\n")
