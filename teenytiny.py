from lex import *  # noqa: F403
from emit import *  # noqa: F403
from parse import *  # noqa: F403
import sys

def main():
    print("Teeny Tiny Compiler")

    if len(sys.argv) != 2:
        sys.exit("Error: Compiler needs source file as argument.")
    with open(sys.argv[1], 'r') as inputFile:
        source = inputFile.read()

    # Initialize the lexer and parser.
    lexer = Lexer(source)  # noqa: F405
    emitter = Emitter("out.c")  # noqa: F405
    parser = Parser(lexer, emitter)  # noqa: F405

    parser.program() # Start the parser.
    emitter.writeFile()
    print("Parsing completed.")

main()