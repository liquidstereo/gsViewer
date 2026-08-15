import argparse
import time

from configs.settings import WINDOW_TITLE
from process.mode import STARTUP_MODE_CHOICES
from process.handle import interrupt_exit
from process.record.quality import validate_save_args
from process.launch import (
    init_session, load_inputs, setup_render_context,
    setup_seq_players, launch_viewer,
)

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=WINDOW_TITLE)
    p.add_argument(
        '-i', '--input', required=True,
        help='Directory/PLY path. Comma-separated list for '
             'multi-input (e.g. -i obj01,obj02)',
    )
    p.add_argument(
        '-r', '--range', metavar='START-END',
        help='Frame range, 0-based inclusive (e.g. -r 0-10)',
    )
    p.add_argument(
        '-s', '--save', action='store_true',
        help='Auto-save frames while playing in viewer',
    )
    p.add_argument(
        '-ss', '--silent_save', action='store_true',
        help='Batch save frames without viewer',
    )
    p.add_argument(
        '-c', '--continuous', action='store_true',
        help='Keep saving frames continuously (use with -s)',
    )
    p.add_argument(
        '-sq', '--save_quit', action='store_true',
        help='Show viewer, save full sequence, then auto-quit',
    )
    p.add_argument(
        '--no-cache', action='store_true',
        help='Disable all caches (disk .npz / sequence RAM / GPU preload)',
    )
    p.add_argument(
        '-ratio', '--slicing_ratio', type=float, default=None, metavar='R',
        help='Keep ratio 0<R<=1 (overrides SLICING_RATIO; default 1.0 = '
             'no slicing, R<1.0 enables stride downsampling)',
    )
    p.add_argument(
        '-m', '--mode', type=str.lower, default='default',
        choices=STARTUP_MODE_CHOICES, metavar='MODE',
        help='Startup render mode (overrides STARTUP_MODE; '
             'default: default)',
    )
    p.add_argument(
        '-t', '--turntable', action='store_true',
        help='Start turntable rotation (toggle anytime: NumDecimal)',
    )
    p.add_argument(
        '-v', '--verbose', action='store_true',
        help='Enable verbose DEBUG-level logging',
    )
    p.add_argument(
        '-no', '--no_overlay', action='store_true',
        help='Hide all overlays at startup (toggle back with Slash key)',
    )
    p.add_argument(
        '-p', '--plugin', metavar='LIST',
        help='Comma-separated plugin names (plugins/{NAME}/, '
             'e.g. -p particle,audio_distortion)',
    )
    p.add_argument(
        '-a', '--audio', metavar='FILE[,FILE...]',
        help='Audio file(s), comma-separated list 1:1 with -i '
             'inputs (enables audio panel; playlist modes chain '
             'audio per active input)',
    )
    p.add_argument(
        '-play', '--playback_mode',
        choices=('loop', 'chain', 'single', 'shuffle', 'random'),
        metavar='MODE',
        help='Multi-input playback: chain(default)/loop(composite)/single/'
             'shuffle/random (overrides PLAYBACK_MODE)',
    )
    p.add_argument(
        '-f', '--format', choices=('png', 'mp4'),
        help='Save format png/mp4 (requires -s/-ss/-sq; default SAVE_EXT)',
    )
    p.add_argument(
        '-q', '--quality', metavar='LEVEL',
        help='Save quality low/medium/high/raw (png also accepts 0-100; '
             'requires -s/-ss/-sq)',
    )
    args = p.parse_args()
    if args.slicing_ratio is not None and not (
        0.0 < args.slicing_ratio <= 1.0
    ):
        p.error('--slicing_ratio must be in (0.0, 1.0]')
    if args.silent_save and args.continuous:
        p.error('-c/--continuous cannot be used with -ss/--silent_save')
    if args.save_quit and args.silent_save:
        p.error('-sq/--save_quit cannot be used with -ss/--silent_save')
    if args.save_quit and args.continuous:
        p.error('-sq/--save_quit cannot be used with -c/--continuous')
    has_save = args.save or args.silent_save or args.save_quit
    err = validate_save_args(args.format, args.quality, has_save)
    if err is not None:
        p.error(err)
    return args

def exec_viewer(
    args: argparse.Namespace, start_time: float | None = None,
) -> None:
    print('--')
    session = init_session(args)
    load_inputs(session, args)
    setup_render_context(session)
    setup_seq_players(session, args)
    launch_viewer(session, args, start_time)

def main() -> None:
    start_time = time.perf_counter()
    try:
        exec_viewer(parse_args(), start_time=start_time)
    except KeyboardInterrupt:
        interrupt_exit()

if __name__ == '__main__':
    main()
