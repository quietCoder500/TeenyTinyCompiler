import sys
from lex import TokenType, Token

class AST:
    def __init__(self):
        self.tree = []

    def add(self, token):
        node = Node(token)
        self.tree.append(node)
        return node

class Node():
    def __init__(self, token, left = None, right = None):
        self.token = token
        self.value = token.text
        self.kind = token.kind
        self.left = left
        self.right = right 

    def __repr__(self):
        right = ("None" if self.right is None else str(self.right))
        left  = ("None" if self.left  is None else str(self.left))
        return "AST NODE: \"" + str(self.kind) + "\" subnodes: [" + left + ", " + right + "]"

class Parser:
    def __init__(self, lexer, emitter):
        self.lexer = lexer
        self.ast = AST()
        self.emitter = emitter

        self.symbols = set()
        self.labelsDeclared = set()
        self.labelsGotoed = set()

        self.curToken = None
        self.peekToken = None
        self.nextToken()
        self.nextToken()


    def checkToken(self, kind):
        return kind == self.curToken.kind


    def checkPeek(self, kind):
        return kind == self.peekToken.kind


    def match(self, kind):
        if not self.checkToken(kind):
            self.abort("Expected " + kind.name + ", got " + self.curToken.kind.name)
        self.nextToken()


    def nextToken(self):
        self.curToken = self.peekToken
        self.peekToken = self.lexer.getToken()


    def abort(self, message):
        sys.exit("Error. " + message)


    def program(self):
        self.emitter.headerLine("#include <stdio.h>")
        self.emitter.headerLine("int main(void){")

        while self.checkToken(TokenType.NEWLINE):
            self.nextToken()

        while not self.checkToken(TokenType.EOF):
            self.statement()

        self.emitter.emitLine("return 0;")
        self.emitter.emitLine("}")

        for label in self.labelsGotoed:
            if label not in self.labelsDeclared:
                self.abort("Attempting to GOTO to undeclared label: " + label)


    def statement(self):
        if self.checkToken(TokenType.PRINT):
            head = self.ast.add(self.curToken)
            self.nextToken()
            
            if self.checkToken(TokenType.STRING):
                self.emitter.emitLine("printf(\"" + self.curToken.text + "\\n\");")
                head.left = Node(self.curToken)
                self.nextToken() 
            else:
                self.emitter.emit("printf(\"%" + ".f\\n\", (float)(")
                self.expression(head)
                self.emitter.emitLine("));")

        elif self.checkToken(TokenType.IF):
            self.nextToken()
            self.emitter.emit("if(")
            self.comparison()

            self.match(TokenType.THEN)
            self.nl()
            self.emitter.emit("){")

            # Zero or more statements in the body.
            while not self.checkToken(TokenType.ENDIF):
                self.statement()

            self.match(TokenType.ENDIF)
            self.emitter.emitLine("}")

        elif self.checkToken(TokenType.WHILE):
            self.nextToken()
            self.emitter.emit("while(")
            self.comparison()

            self.match(TokenType.REPEAT)
            self.nl()
            self.emitter.emit("){")

            # Zero or more statements in the loop body.
            while not self.checkToken(TokenType.ENDWHILE):
                self.statement()

            self.match(TokenType.ENDWHILE)
            self.emitter.emitLine("}")

        # "LABEL" ident
        elif self.checkToken(TokenType.LABEL):
            self.nextToken()

            if self.curToken.text in self.labelsDeclared:
                self.abort("Label already exists: " + self.curToken.text)
            self.labelsDeclared.add(self.curToken.text)

            self.emitter.emitLine(self.curToken.text + ":")
            self.match(TokenType.IDENT)

        # "GOTO" ident
        elif self.checkToken(TokenType.GOTO):
            self.nextToken()
            self.labelsGotoed.add(self.curToken.text)
            self.emitter.emitLine("goto" + self.curToken.text + ";")
            self.match(TokenType.IDENT)

        # "LET" ident "=" expression
        elif self.checkToken(TokenType.LET):
            self.nextToken()

            if self.curToken.text not in self.symbols:
                self.symbols.add(self.curToken.text)
                self.emitter.headerLine("float " + self.curToken.text + ";")
            
            self.emitter.emit(self.curToken.text + " = ")
            self.match(TokenType.IDENT)
            self.match(TokenType.EQ)

            self.expression()
            self.emitter.emitLine(";")

        # "INPUT" ident
        elif self.checkToken(TokenType.INPUT):
            self.nextToken()
            
            if self.curToken.text not in self.symbols:
                self.symbols.add(self.curToken.text)
                self.emitter.headerLine("float " + self.curToken.text + ";")

            self.emitter.emitLine("if(0 == scanf(\"%" + "f\", &" + self.curToken.text + ")) {")
            self.emitter.emitLine(self.curToken.text + " = 0;")
            self.emitter.emit("scanf(\"%")
            self.emitter.emitLine("*s\");")
            self.emitter.emitLine("}")
            self.match(TokenType.IDENT)

        # This is not a valid statement. Error!
        else:
            self.abort("Invalid statement at " + self.curToken.text + " (" + self.curToken.kind.name + ")")

        self.nl()


    # nl ::= '\n'+
    def nl(self):
        self.match(TokenType.NEWLINE)

        while self.checkToken(TokenType.NEWLINE):
            self.nextToken()
            

    def comparison(self):
        self.expression()

        if self.isComparisonOperator():
            self.emitter.emit(self.curToken.text)
            self.nextToken()
            self.expression()
        else:
            self.abort("Expected comparison operator at: " + self.curToken.text)
        
        while self.isComparisonOperator():
            self.emitter.emit(self.curToken.text)
            self.nextToken()
            self.expression()
    
    # expression ::= term {( "-" | "+" ) term}
    def expression(self, head):
        self.term()

        while self.checkToken(TokenType.PLUS) or self.checkToken(TokenType.MINUS):
            self.emitter.emit(self.curToken.text)
            self.nextToken()
            self.term()


    # term ::= unary {( "/" | "*" ) unary}
    def term(self):
        node = self.unary()
        # Can have 0 or more *// and expressions.
        while self.checkToken(TokenType.ASTERISK) or self.checkToken(TokenType.SLASH):
            self.emitter.emit(self.curToken.text)
            self.nextToken()
            node = self.unary()


    # unary ::= ["+" | "-"] primary
    def unary(self):
        # Optional unary +/- (positive or negative on the primary)
        if self.checkToken(TokenType.PLUS) or self.checkToken(TokenType.MINUS):
            self.emitter.emit(self.curToken.text)
            sign = self.curToken
            self.nextToken()
            return Node(sign, self.primary())
        return self.primary()


    # primary ::= number | ident
    def primary(self):
        if self.checkToken(TokenType.NUMBER):
            self.emitter.emit(self.curToken.text)
            node = Node(self.curToken)
            self.nextToken()
        elif self.checkToken(TokenType.IDENT):
            if self.curToken.text not in self.symbols:
                self.abort("Referencing variable before assignment: " + self.curToken.text)
            
            self.emitter.emit(self.curToken.text)
            node = Node(self.curToken)
            self.nextToken()
        else:
            self.abort("Unexpected token at " + self.curToken.text)
            return None
        return node


    def isComparisonOperator(self):
        return self.checkToken(TokenType.GT) or self.checkToken(TokenType.GTEQ) or self.checkToken(TokenType.LT) or self.checkToken(TokenType.LTEQ) or self.checkToken(TokenType.EQEQ) or self.checkToken(TokenType.NOTEQ)
