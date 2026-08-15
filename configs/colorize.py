import sys
import time
import logging
import re
from typing import Optional
from threading import Event
from colorama import Fore, Back, Style, init
init(autoreset=True)

class ColorizeLogger:

    LEVEL_COLORS = {
        'DEBUG': Fore.GREEN,
        'INFO': Fore.WHITE,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.MAGENTA,
    }

    @staticmethod
    def format(
        record: logging.LogRecord, message: str,
    ) -> str:
        color = ColorizeLogger.LEVEL_COLORS.get(
            record.levelname, ''
        )
        return f'{color}{message}{Style.RESET_ALL}'

class Msg:

    _last_was_flush = False

    @staticmethod
    def _clear_line(line: int = 0):
        if line < 0:

            sys.stdout.write(f'\033[{abs(line)}A\033[2K\r')
        else:

            sys.stdout.write('\033[2K\r')
        sys.stdout.flush()

    @staticmethod
    def _handle_flush():
        if Msg._last_was_flush:
            Msg._clear_line()
            Msg._last_was_flush = False

    @staticmethod
    def _transform_message(
        msg: str, upper: bool = True,
    ) -> str:
        patterns = [
            r'\{[^}]+\}',
            r'"[^"]*"',
            r"'[^']*'",
            r'\[[^\]]*\]',
            r'\([^\)]*\)',
            r'\S*[\\/]\S*',
        ]
        combined = '|'.join(
            f'({p})' for p in patterns
        )
        tokens = re.split(combined, msg)
        res = []
        for token in tokens:
            if not token:
                continue
            if re.fullmatch(combined, token):
                res.append(token)
            else:
                res.append(
                    token.upper() if upper else token
                )
        return ''.join(res)

    @staticmethod
    def _colorize(
        message: str, fg: str, bg: str = '',
        plain: bool = True,
        dfg: str = Fore.WHITE,
        dbg: str = Back.WHITE,
    ) -> str:
        if plain:
            return (
                f'{Style.BRIGHT}{fg}'
                f'{message}{Style.RESET_ALL}'
            )
        bg_c = bg if bg else dbg
        bright = (
            '' if bg == dbg else Style.BRIGHT
        )
        return (
            f'{bg_c}{dfg}{bright}'
            f'{message}{Style.RESET_ALL}'
        )

    @staticmethod
    def _apply_formatting(
        styled: str,
        verbose: bool = False,
        flush: bool = False,
        divide: bool = False,
    ) -> str | None:
        if divide:
            styled = f'--\n{styled}\n--'
        if verbose:
            return styled
        if flush:
            Msg._clear_line()
            Msg._last_was_flush = True
        else:
            Msg._handle_flush()
        print(
            styled,
            end='\r' if flush else '\n',
            flush=flush,
        )
        return None

    @staticmethod
    def Info(
        message: str, divide: bool = True,
        upper: bool = True,
        verbose: bool = False,
        flush: bool = False,
    ):
        msg = Msg._transform_message(message, upper)
        styled = (
            f'{Fore.GREEN}{Style.BRIGHT}'
            f'INFO: {msg}{Style.RESET_ALL}'
        )
        return Msg._apply_formatting(
            styled, verbose, flush, divide
        )

    @staticmethod
    def Debug(
        message: str, divide: bool = False,
        upper: bool = True,
        verbose: bool = False,
        flush: bool = False,
    ):
        msg = Msg._transform_message(message, upper)
        styled = (
            f'{Fore.WHITE}{Style.BRIGHT}'
            f'DEBUG: {msg}{Style.RESET_ALL}'
        )
        return Msg._apply_formatting(
            styled, verbose, flush, divide
        )

    @staticmethod
    def Warning(
        message: str, divide: bool = True,
        upper: bool = True,
        verbose: bool = False,
        flush: bool = False,
    ):
        msg = Msg._transform_message(message, upper)
        styled = (
            f'{Fore.YELLOW}'
            f'WARNING: {msg}{Style.RESET_ALL}'
        )
        return Msg._apply_formatting(
            styled, verbose, flush, divide
        )

    @staticmethod
    def Confirm(
        message: str, divide: bool = False,
        upper: bool = True,
        verbose: bool = False,
        flush: bool = False,
    ):
        msg = Msg._transform_message(message, upper)
        styled = (
            f'{Style.BRIGHT}{Fore.CYAN}'
            f'CONFIRM: {msg}{Style.RESET_ALL}'
        )
        return Msg._apply_formatting(
            styled, verbose, flush, divide
        )

    @staticmethod
    def Error(
        message: str, divide: bool = True,
        upper: bool = True,
        verbose: bool = False,
        flush: bool = False,
    ):
        msg = Msg._transform_message(message, upper)
        styled = (
            f'{Back.RED}{Fore.WHITE}'
            f'ERROR: {msg}{Style.RESET_ALL}'
        )
        return Msg._apply_formatting(
            styled, verbose, flush, divide
        )

    @staticmethod
    def Critical(
        message: str, divide: bool = True,
        upper: bool = True,
        verbose: bool = False,
        flush: bool = False,
    ):
        msg = Msg._transform_message(message, upper)
        styled = (
            f'{Back.RED}{Fore.WHITE}'
            f'CRITICAL: {msg}{Style.RESET_ALL}'
        )
        return Msg._apply_formatting(
            styled, verbose, flush, divide
        )

    @staticmethod
    def Dim(
        message: str, divide: bool = False,
        upper: bool = True,
        flush: bool = False,
        verbose: bool = False,
    ) -> str | None:
        msg = Msg._transform_message(message, upper)
        styled = (
            f'{Style.DIM}{msg}{Style.RESET_ALL}'
        )
        return Msg._apply_formatting(
            styled, verbose, flush, divide
        )

    @staticmethod
    def Alert(
        message: str, divide: bool = True,
        upper: bool = True,
        flush: bool = False,
        verbose: bool = False,
    ) -> str | None:
        msg = Msg._transform_message(message, upper)
        styled = (
            f'{Fore.RED}'
            f'ALERT: {msg}{Style.RESET_ALL}'
        )
        return Msg._apply_formatting(
            styled, verbose, flush, divide
        )

    @staticmethod
    def Result(
        message: str, divide: bool = True,
        upper: bool = True,
        flush: bool = False,
        verbose: bool = False,
    ) -> str | None:
        msg = Msg._transform_message(message, upper)
        styled = (
            f'{Back.YELLOW}{Fore.BLACK}'
            f'RESULT: {msg}{Style.RESET_ALL}'
        )
        return Msg._apply_formatting(
            styled, verbose, flush, divide
        )

    @staticmethod
    def Red(
        message: str, divide: bool = False,
        upper: bool = True, flush: bool = False,
        verbose: bool = False, plain: bool = True,
    ):
        msg = Msg._transform_message(message, upper)
        styled = Msg._colorize(
            msg, Fore.RED, Back.RED, plain
        )
        return Msg._apply_formatting(
            styled, verbose, flush, divide
        )

    @staticmethod
    def Yellow(
        message: str, divide: bool = False,
        upper: bool = True, flush: bool = False,
        verbose: bool = False, plain: bool = True,
    ):
        msg = Msg._transform_message(message, upper)
        styled = Msg._colorize(
            msg, Fore.YELLOW, Back.YELLOW, plain
        )
        return Msg._apply_formatting(
            styled, verbose, flush, divide
        )

    @staticmethod
    def Green(
        message: str, divide: bool = False,
        upper: bool = True, flush: bool = False,
        verbose: bool = False, plain: bool = True,
    ):
        msg = Msg._transform_message(message, upper)
        styled = Msg._colorize(
            msg, Fore.GREEN, Back.GREEN, plain
        )
        return Msg._apply_formatting(
            styled, verbose, flush, divide
        )

    @staticmethod
    def Blue(
        message: str, divide: bool = False,
        upper: bool = True, flush: bool = False,
        verbose: bool = False, plain: bool = True,
    ):
        msg = Msg._transform_message(message, upper)
        styled = Msg._colorize(
            msg, Fore.BLUE, Back.BLUE, plain
        )
        return Msg._apply_formatting(
            styled, verbose, flush, divide
        )

    @staticmethod
    def Cyan(
        message: str, divide: bool = False,
        upper: bool = True, flush: bool = False,
        verbose: bool = False, plain: bool = True,
    ):
        msg = Msg._transform_message(message, upper)
        styled = Msg._colorize(
            msg, Fore.CYAN, Back.CYAN, plain
        )
        return Msg._apply_formatting(
            styled, verbose, flush, divide
        )

    @staticmethod
    def Magenta(
        message: str, divide: bool = False,
        upper: bool = True, flush: bool = False,
        verbose: bool = False, plain: bool = True,
    ):
        msg = Msg._transform_message(message, upper)
        styled = Msg._colorize(
            msg, Fore.MAGENTA, Back.MAGENTA, plain
        )
        return Msg._apply_formatting(
            styled, verbose, flush, divide
        )

    @staticmethod
    def Plain(
        message: str, divide: bool = False,
        upper: bool = True, flush: bool = False,
        verbose: bool = False,
    ):
        msg = Msg._transform_message(message, upper)
        return Msg._apply_formatting(
            msg, verbose, flush, divide
        )

    @staticmethod
    def White(
        message: str, divide: bool = False,
        upper: bool = True, flush: bool = False,
        verbose: bool = False, plain: bool = False,
    ):
        msg = Msg._transform_message(message, upper)
        styled = Msg._colorize(
            msg, Fore.BLACK, Back.WHITE, plain,
            dfg=Fore.BLACK, dbg=Back.WHITE,
        )
        return Msg._apply_formatting(
            styled, verbose, flush, divide
        )

    @staticmethod
    def Black(
        message: str, divide: bool = False,
        upper: bool = True, flush: bool = False,
        verbose: bool = False, plain: bool = True,
    ):
        msg = Msg._transform_message(message, upper)
        styled = Msg._colorize(
            msg, Fore.BLACK, Back.BLACK, plain,
            dfg=Fore.WHITE, dbg=Back.BLACK,
        )
        return Msg._apply_formatting(
            styled, verbose, flush, divide
        )

    @staticmethod
    def Blink(
        message: str,
        duration: float = 30.0,
        interval: float = 0.2,
        color: str = 'red',
        verbose: bool = False,
        clear_on_finish: bool = True,
        stop_event: Optional[Event] = None,
        upper: bool = False,
    ) -> str | None:
        msg = Msg._transform_message(message, upper)

        try:
            fg = getattr(Fore, color.upper())
        except AttributeError:
            fg = Fore.RESET

        if verbose:
            return f'{fg}{msg}{Fore.RESET}'

        end_time = time.time() + duration

        while True:
            if stop_event is not None:
                if stop_event.is_set():
                    break
            elif time.time() >= end_time:
                break

            sys.stdout.write(f'{fg}{msg}\r')
            sys.stdout.flush()

            if stop_event and stop_event.wait(interval):
                break

            sys.stdout.write(
                f"\r{' ' * len(msg)}\r"
            )
            sys.stdout.flush()

            if stop_event and stop_event.wait(interval):
                break

        time.sleep(0.1)

        if clear_on_finish:
            sys.stdout.write('\033[2K\r')
            sys.stdout.flush()
        else:
            sys.stdout.write(
                f'{fg}{msg}{Style.RESET_ALL}\n'
            )
            sys.stdout.flush()
