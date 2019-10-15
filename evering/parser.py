from abc import ABC
from typing import Any, Dict, List, Optional, Tuple, Union

from .util import *

"""
This parsing solution has the following structure:

1. Separate header and config file content, if necessary
2. Split up text into lines, if still necessary
3. Parse each line individually
4. Use a recursive descent approach to group the lines into blocks and if-blocks
5. Evaluate the blocks recursively
"""

__all__ = ["ParseException", "Parser"]

class ParseException(Exception):
    @classmethod
    def on_line(cls, line: "Line", text: str) -> "ParseException":
        return ParseException(f"Line {line.line_number}: {text}")

def split_header_and_rest(text: str) -> Tuple[List[str], List[str]]:
    lines = text.splitlines()

    header: List[str] = []
    rest: List[str] = []

    in_header = True
    for line in lines:
        if not in_header:
            rest.append(line)
        elif len(line) >= 3 and line == "=" * len(line):
            # The header is separated from the rest of the file by
            # a line that contains 3 or more "=" characters and
            # nothing else.
            in_header = False
        else:
            header.append(line)

    return header, rest

class Parser:
    def __init__(self,
                 raw_lines: List[str],
                 statement_initiator: str,
                 expression_opening_delimiter: str,
                 expression_closing_delimiter: str,
    ) -> None:
        """
        May raise: ParseException
        """
        
        self.statement_initiator = statement_initiator
        self.expression_opening_delimiter = expression_opening_delimiter
        self.expression_closing_delimiter = expression_closing_delimiter

        # Split up the text into lines and parse those
        lines: List[Line] = []
        for i, text in enumerate(raw_lines):
            lines.append(Line.parse(self, text, i))

        # Parse the lines into a block
        lines_queue = list(reversed(lines))
        self.main_block = Block(self, lines_queue)

    def evaluate(self, local_vars: Dict[str, Any]) -> str:
        lines = self.main_block.evaluate(local_vars)
        return "".join(f"{line}\n" for line in lines)

# Line parsing (inline expressions)

class Line(ABC):
    @staticmethod
    def parse(parser: Parser, text: str, line_number: int) -> "Line":
        try:
            return IfStatement(parser, text, line_number)
        except ParseException:
            pass

        try:
            return ElifStatement(parser, text, line_number)
        except ParseException:
            pass

        try:
            return ElseStatement(parser, text, line_number)
        except ParseException:
            pass

        try:
            return EndStatement(parser, text, line_number)
        except ParseException:
            pass

        return ActualLine(parser, text, line_number)
    
    def __init__(self, parser: Parser, line_number: int) -> None:
        self.parser = parser
        self.line_number = line_number

    def _parse_statement(self, text: str, statement_name: str) -> Optional[str]:
        start = f"{self.parser.statement_initiator} {statement_name}"
        text = text.strip()
        if text.startswith(start):
            return text[len(start):].strip()
        else:
            return None

    def _parse_statement_noarg(self, text: str, statement_name: str) -> bool:
        return text.strip() == f"{self.parser.statement_initiator} {statement_name}"
    
class ActualLine(Line):
    def __init__(self, parser: Parser, text: str, line_number: int) -> None:
        """
        May raise: ParseException
        """

        super().__init__(parser, line_number)
        self.chunks = self._parse_chunks(text)

    def _parse_chunks(self, text: str) -> List[Tuple[str, bool]]:
        """
        A chunk is a tuple (text, is_expression), where the first
        argument is the text contained in the chunk and the second
        argument a boolean that indicates whether this chunk is a
        python expression (or just plain text).
        
        Because it simplifies the program logic, a chunk's text may
        also be the empty string.

        May raise: ParseException
        """

        chunks: List[Tuple[str, bool]] = []

        i = 0
        while i < len(text):
            # Find opening delimiter
            od = text.find(self.parser.expression_opening_delimiter, i)
            if od == -1:
                chunks.append((text[i:], False))
                break # We've consumed the entire string.
            od_end = od + len(self.parser.expression_opening_delimiter)

            # Find closing delimiter
            cd = text.find(self.parser.expression_closing_delimiter, od_end)
            if cd == -1:
                raise ParseException.on_line(self, f"No closing delimiter\n{text[:od_end]} <-- to THIS opening delimiter")
            cd_end = cd + len(self.parser.expression_closing_delimiter)

            # Split up into chunks
            chunks.append((text[i:od], False))
            chunks.append((text[od_end:cd], True))
            i = cd_end

        return chunks

    def evaluate(self, local_vars: Dict[str, Any]) -> str:
        """
        May raise: ExecuteException
        """

        return "".join(self._evaluate_chunk(chunk, local_vars) for chunk in self.chunks)

    def _evaluate_chunk(self,
                        chunk: Tuple[str, bool],
                        local_vars: Dict[str, Any],
    ) -> str:
        """
        May raise: ExecuteException
        """
        
        if not chunk[1]:
            return chunk[0]

        return str(safer_eval(chunk[0], local_vars))

class IfStatement(Line):
    def __init__(self, parser: Parser, text: str, line_number: int) -> None:
        """
        May raise: ParseException
        """

        super().__init__(parser, line_number)

        self.argument = self._parse_statement(text, "if")
        if self.argument is None:
            raise ParseException.on_line(self, "Not an 'if' statement")

class ElifStatement(Line):
    def __init__(self, parser: Parser, text: str, line_number: int) -> None:
        """
        May raise: ParseException
        """

        super().__init__(parser, line_number)

        self.argument = self._parse_statement(text, "elif")
        if self.argument is None:
            raise ParseException.on_line(self, "Not an 'elif' statement")

class ElseStatement(Line):
    def __init__(self, parser: Parser, text: str, line_number: int) -> None:
        """
        May raise: ParseException
        """

        super().__init__(parser, line_number)

        if not self._parse_statement_noarg(text, "else"):
            raise ParseException.on_line(self, "Not an 'else' statement")

class EndStatement(Line):
    def __init__(self, parser: Parser, text: str, line_number: int) -> None:
        """
        May raise: ParseException
        """

        super().__init__(parser, line_number)

        if not self._parse_statement_noarg(text, "end"):
            raise ParseException.on_line(self, "Not an 'end' statement")

# Block parsing

class Block:
    def __init__(self, parser: Parser, lines_queue: List[Line]) -> None:
        """
        May raise: ParseException
        """
        
        self._elements: List[Union[ActualLine, IfBlock]] = []

        while lines_queue:
            next_line = lines_queue[-1] # Peek
            if isinstance(next_line, ActualLine):
                lines_queue.pop()
                self._elements.append(next_line)
            elif isinstance(next_line, IfStatement):
                self._elements.append(IfBlock(parser, lines_queue))
            else:
                # We've hit the border of our enclosure. Parsing that
                # is up to the parent of this block, not the block
                # itself.
                break

    def evaluate(self, local_vars: Dict[str, Any]) -> List[str]:
        lines: List[str] = []

        for element in self._elements:
            if isinstance(element, ActualLine):
                lines.append(element.evaluate(local_vars))
            else:
                lines.extend(element.evaluate(local_vars))

        return lines

class IfBlock(Block):
    def __init__(self, parser: Parser, lines_queue: List[Line]) -> None:
        """
        May raise: ParseException
        """

        self._sections: List[Tuple[Block, Optional[str]]] = []

        if not lines_queue:
            raise ParseException("Unexpected end of file, expected 'if' statement")

        # If statement
        #
        # This is the short version:
        # if not isinstance(lines_queue[-1], IfStatement): # This should never happen
        #     raise ParseException.on_line(lines_queue[-1], "Expected 'if' statement")
        # self._sections.append((Block(parser, lines_queue), lines_queue.pop().argument))
        #
        # And this the long version, which mypy understands without errors:
        next_statement = lines_queue[-1]
        if not isinstance(next_statement, IfStatement): # This should never happen
            raise ParseException.on_line(next_statement, "Expected 'if' statement")
        lines_queue.pop()
        self._sections.append((Block(parser, lines_queue), next_statement.argument))

        # Elif statements
        #
        # This is the short version:
        # while lines_queue and isinstance(lines_queue[-1], ElifStatement):
        #     self._sections.append((Block(parser, lines_queue), lines_queue.pop().argument))
        #
        # And this the long version, which mypy understands without errors:
        while True:
            if not lines_queue: break
            next_statement = lines_queue[-1]
            if not isinstance(next_statement, ElifStatement): break
            lines_queue.pop()
            self._sections.append((Block(parser, lines_queue), next_statement.argument))

        # Optional else statement
        if lines_queue and isinstance(lines_queue[-1], ElseStatement):
            lines_queue.pop()
            self._sections.append((Block(parser, lines_queue), None))

        if not lines_queue:
            raise ParseException("Unexpected end of file, expected 'if' statement")
        if not isinstance(lines_queue[-1], EndStatement):
            raise ParseException.on_line(lines_queue[-1], "Expected 'end' statement")
        lines_queue.pop()
        
    def evaluate(self, local_vars: Dict[str, Any]) -> List[str]:
        for entry in self._sections:
            if entry[1] is None or safer_eval(entry[1], local_vars):
                return entry[0].evaluate(local_vars)

        return []
