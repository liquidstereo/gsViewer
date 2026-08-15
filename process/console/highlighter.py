import keyword

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import (
    QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextDocument,
)

from process.console.settings import (
    SYNTAX_BUILTIN_COLOR, SYNTAX_COMMENT_COLOR, SYNTAX_JSON_KEY_COLOR,
    SYNTAX_JSON_LITERAL_COLOR, SYNTAX_KEYWORD_COLOR, SYNTAX_NUMBER_COLOR,
    SYNTAX_STRING_COLOR)

_KEYWORD_COLOR = SYNTAX_KEYWORD_COLOR
_BUILTIN_COLOR = SYNTAX_BUILTIN_COLOR
_STRING_COLOR = SYNTAX_STRING_COLOR
_COMMENT_COLOR = SYNTAX_COMMENT_COLOR
_NUMBER_COLOR = SYNTAX_NUMBER_COLOR
_JSON_KEY_COLOR = SYNTAX_JSON_KEY_COLOR
_JSON_LITERAL_COLOR = SYNTAX_JSON_LITERAL_COLOR
_BUILTIN_NAMES = ('self', 'cls', 'True', 'False', 'None')
_JSON_LITERALS = ('true', 'false', 'null')
_NUMBER_RE = r'\b[0-9]+\.?[0-9]*\b'
_SQ_RE = r"'[^'\\]*(\\.[^'\\]*)*'"
_DQ_RE = r'"[^"\\]*(\\.[^"\\]*)*"'
_COMMENT_RE = r'#[^\n]*'

def _fmt(color: str, bold: bool = False) -> QTextCharFormat:
    fmt = QTextCharFormat()
    fmt.setForeground(QColor(color))
    if bold:
        fmt.setFontWeight(QFont.Weight.Bold)
    return fmt

class PythonHighlighter(QSyntaxHighlighter):

    def __init__(self, document: QTextDocument) -> None:
        super().__init__(document)
        self._rules: list = self._build_rules()
        self._comment = QRegularExpression(_COMMENT_RE)
        self._comment_fmt = _fmt(_COMMENT_COLOR)

    def _build_rules(self) -> list:
        rules = []
        kw_fmt = _fmt(_KEYWORD_COLOR, bold=True)
        for kw in keyword.kwlist:
            rules.append((QRegularExpression(rf'\b{kw}\b'), kw_fmt))
        builtin_fmt = _fmt(_BUILTIN_COLOR)
        for name in _BUILTIN_NAMES:
            rules.append((QRegularExpression(rf'\b{name}\b'), builtin_fmt))
        rules.append((QRegularExpression(_NUMBER_RE), _fmt(_NUMBER_COLOR)))
        str_fmt = _fmt(_STRING_COLOR)
        rules.append((QRegularExpression(_SQ_RE), str_fmt))
        rules.append((QRegularExpression(_DQ_RE), str_fmt))
        return rules

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self._rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)
        it = self._comment.globalMatch(text)
        while it.hasNext():
            m = it.next()
            self.setFormat(
                m.capturedStart(), m.capturedLength(), self._comment_fmt)

class JsonHighlighter(QSyntaxHighlighter):

    def __init__(self, document: QTextDocument) -> None:
        super().__init__(document)
        self._rules: list = self._build_rules()

    def _build_rules(self) -> list:

        rules = [(QRegularExpression(_DQ_RE), _fmt(_STRING_COLOR))]
        rules.append((
            QRegularExpression(_DQ_RE + r'(?=\s*:)'),
            _fmt(_JSON_KEY_COLOR, bold=True),
        ))
        rules.append((QRegularExpression(_NUMBER_RE), _fmt(_NUMBER_COLOR)))
        literal_fmt = _fmt(_JSON_LITERAL_COLOR, bold=True)
        for lit in _JSON_LITERALS:
            rules.append((QRegularExpression(rf'\b{lit}\b'), literal_fmt))
        return rules

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self._rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)
