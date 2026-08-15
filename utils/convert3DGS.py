import argparse
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from configs.colorize import Msg
from utils.process.formats import (
    _ENCODERS,
    _LOG_DIR,
    resolve_output_dir,
    setup_logging,
    strip_ext,
)
from utils.process.pipeline import convert_dir, convert_file

logger = logging.getLogger(__name__)

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            '3DGS Format Converter: .ply / .compressed.ply / .splat\n'
            'Single file or batch directory conversion supported.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        '-i', '--input', required=True,
        help='Input file or directory (.ply / .compressed.ply / .splat)',
    )
    p.add_argument(
        '-o', '--output', default=None,
        help=(
            'Output file path (single) or directory path (batch). '
            'If omitted, auto-named from input + codec.'
        ),
    )
    p.add_argument(
        '-c', '--codec',
        choices=list(_ENCODERS),
        default=None,
        help='Target codec: ply / cply / splat',
    )
    return p.parse_args()

def exec_convert(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f'Input path not found: {input_path}')

    print('--')
    if input_path.is_dir():
        out_dir, fmt = resolve_output_dir(
            input_path, args.output, args.codec
        )
        res = convert_dir(input_path, out_dir, fmt)

    else:
        res, fmt = convert_file(input_path, args.output, args.codec)

    print('--')
    Msg.Result(f'Convert to {fmt.upper()} for "{args.input}" finished.', divide=False)
    log_file = f'convert_{strip_ext(Path(args.input).name)}.log'
    log_rel = _LOG_DIR.relative_to(_ROOT) / log_file
    Msg.Dim(
        f'Please refer to the log file for details.'
        f' (./{log_rel})')

def main() -> None:
    args = parse_args()
    log_name = strip_ext(Path(args.input).name)
    setup_logging(log_name)
    try:
        exec_convert(args)
    except (ValueError, FileNotFoundError, RuntimeError) as e:
        logger.error('Conversion failed: %s', e)
        sys.exit(1)

if __name__ == '__main__':
    main()
