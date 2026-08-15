import logging
import sys
from pathlib import Path

from utils.decoders.cply_decoder import decode_cply
from utils.decoders.ply_decoder import decode_ply
from utils.decoders.splat_decoder import decode_splat
from utils.encoders.cply_encoder import encode_cply
from utils.encoders.ply_encoder import encode_ply
from utils.encoders.splat_encoder import encode_splat

_ROOT = Path(__file__).resolve().parent.parent.parent
_LOG_FORMAT = (
    '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d: %(message)s'
)
_LOG_DIR = _ROOT / 'logs'

_DECODERS: dict = {
    'ply':   decode_ply,
    'cply':  decode_cply,
    'splat': decode_splat,
}
_ENCODERS: dict = {
    'ply':   encode_ply,
    'cply':  encode_cply,
    'splat': encode_splat,
}
_CODEC_SUFFIX: dict[str, str] = {
    'ply':   '.ply',
    'cply':  '.compressed.ply',
    'splat': '.splat',
}
_SUPPORTED_EXTS: list[str] = ['.compressed.ply', '.ply', '.splat']

def setup_logging(input_name: str) -> None:
    _LOG_DIR.mkdir(exist_ok=True)
    log_file = _LOG_DIR / f'convert_{input_name}.log'
    fmt = logging.Formatter(_LOG_FORMAT)
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.WARNING)
    ch.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    root.addHandler(fh)
    root.addHandler(ch)

def _detect_format(path: Path) -> str:
    name = path.name.lower()
    if name.endswith('.compressed.ply'):
        return 'cply'
    if name.endswith('.ply'):
        return 'ply'
    if name.endswith('.splat'):
        return 'splat'
    raise ValueError(f'Unsupported file format: {path.name}')

def strip_ext(name: str) -> str:
    for ext in _SUPPORTED_EXTS:
        if name.lower().endswith(ext):
            return name[: -len(ext)]
    return name

def resolve_output_file(
    input_path: Path,
    output_arg: str | None,
    codec: str | None,
) -> tuple[Path, str]:
    if output_arg is None and codec is None:
        raise ValueError(
            'Either -o/--output or -c/--codec must be specified'
        )
    if output_arg is not None:
        out_path = Path(output_arg)
        fmt = codec if codec else _detect_format(out_path)
        return out_path, fmt
    suffix = _CODEC_SUFFIX[codec]
    stem = strip_ext(input_path.name)
    return input_path.parent / f'{stem}{suffix}', codec

def resolve_output_dir(
    input_dir: Path,
    output_arg: str | None,
    codec: str | None,
) -> tuple[Path, str]:
    if codec is None:
        raise ValueError('-c/--codec is required for directory input')
    if output_arg is not None:
        return Path(output_arg), codec
    return input_dir.parent / f'{input_dir.name}_{codec}', codec

def collect_files(dir_path: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(dir_path.iterdir()):
        if not path.is_file():
            continue
        name = path.name.lower()
        if any(name.endswith(ext) for ext in _SUPPORTED_EXTS):
            files.append(path)
    return files
