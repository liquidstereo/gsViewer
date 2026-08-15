from configs.settings_color import THEME

_DARK: dict[str, str] = {
    'bg': '#1e1e1e',
    'fg': '#d4d4d4',
    'keyword': '#569cd6',
    'builtin': '#4ec9b0',
    'string': '#ce9178',
    'comment': '#6a9955',
    'number': '#b5cea8',
    'json_key': '#9cdcfe',
    'json_literal': '#569cd6',
}
_BRIGHT: dict[str, str] = {
    'bg': '#ffffff',
    'fg': '#1e1e1e',
    'keyword': '#0000ff',
    'builtin': '#267f99',
    'string': '#a31515',
    'comment': '#008000',
    'number': '#098658',
    'json_key': '#0451a5',
    'json_literal': '#0000ff',
}
_T: dict[str, str] = _BRIGHT if THEME == 'Bright' else _DARK

CONSOLE_BG_COLOR: str = _T['bg']
CONSOLE_FG_COLOR: str = _T['fg']

SYNTAX_KEYWORD_COLOR: str = _T['keyword']
SYNTAX_BUILTIN_COLOR: str = _T['builtin']
SYNTAX_STRING_COLOR: str = _T['string']
SYNTAX_COMMENT_COLOR: str = _T['comment']
SYNTAX_NUMBER_COLOR: str = _T['number']
SYNTAX_JSON_KEY_COLOR: str = _T['json_key']
SYNTAX_JSON_LITERAL_COLOR: str = _T['json_literal']
