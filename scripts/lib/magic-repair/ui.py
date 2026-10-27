#!/usr/bin/env python3
"""Magic Repair's terminal presentation. Bluetooth stays in the Bash engine.

The renderer never reads stdin. The engine owns pairing input; any raw response
pauses redraws until the Bluetooth call finishes. IPC events are ephemeral and
contain no pairing prompts or input. --demo does not start the engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import argparse
import collections
import json
import os
import selectors
import signal
import subprocess
import sys
import time
import unicodedata

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

VERSION = '3.0.0'
BG = '#101827'
CARD = '#162135'
INK = '#edf2fb'
MUTED = '#a4b3ca'
FAINT = '#7588a5'
LINE = '#35445f'
VIOLET = '#c4a7ff'
MINT = '#7de2c1'
AMBER = '#ffd48b'
ROSE = '#ff9baa'
SPINNER = ('⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏')


def clean(value: object) -> str:
    """Treat names/messages as text, never terminal control or Rich markup."""
    return ''.join(c if unicodedata.category(c) not in ('Cc', 'Cf', 'Cs') else ' ' for c in str(value))


def text(value: object, style: str = INK, **kwargs) -> Text:
    return Text(clean(value), style=style, **kwargs)


@dataclass
class Device:
    address: str
    name: str
    status: str = 'queued'
    phase: str = ''
    phase_action: str = ''
    paired: bool = False
    connected: bool = False
    round: int = 0
    deadline: float | None = None
    retry_at: float | None = None
    touched: bool = False
    steps: set[str] = field(default_factory=set)

    @property
    def kind(self) -> tuple[str, str]:
        lower = self.name.lower()
        if 'keyboard' in lower:
            return '⌨', 'KEYBOARD'
        if 'trackpad' in lower:
            return '▱', 'TRACKPAD'
        if 'mouse' in lower:
            return '◉', 'MOUSE'
        return '◇', 'ACCESSORY'


class Dashboard:
    def __init__(self, args: list[str] = (), *, clock=time.monotonic):
        self.clock = clock
        self.started = clock()
        self.finished_at = None
        self.devices: dict[str, Device] = {}
        self.active = ''
        self.action = ''
        self.action_started = self.started
        self.action_limit = 0.0
        self.scanning = '--scan' in args
        self.scan_finished = False
        self.preview = '--dry-run' in args or '--list' in args
        self.demo = '--demo' in args
        self.log_path = ''
        self.exit_status: int | None = None

    def consume(self, event: dict):
        now = self.clock()
        kind = event.get('event')
        address = event.get('address', '')
        device = self.devices.get(address)
        if kind == 'run_start':
            self.log_path = event.get('log_path', '')
        elif kind == 'selection':
            for item in event['devices']:
                address = item['address']
                self.devices.setdefault(address, Device(address, clean(item.get('name') or address)))
            self.scan_finished = True
        elif kind == 'device' and device:
            self.active = address
            device.status = 'active'
            device.round = event['round']
            device.deadline = now + max(0, event['remaining_s'])
            device.retry_at = None
        elif kind == 'call_start':
            self.action = event['action']
            self.action_started = now
            self.action_limit = event['limit_s']
            if self.action == '--inquiry':
                self.scanning = True
            if device and self.action in ('--unpair', '--pair', '--connect', '--disconnect'):
                device.status = 'active'
                device.phase = {'--unpair':'Release', '--disconnect':'Release', '--pair':'Pair', '--connect':'Connect'}[self.action]
                device.phase_action = self.action
                device.touched = True
        elif kind == 'call_end':
            self.action = ''
        elif kind == 'state' and device:
            device.paired, device.connected = event['paired'], event['connected']
            if device.phase_action == '--unpair' and not device.paired or device.phase_action == '--disconnect' and not device.connected:
                device.steps.add('Release')
            if device.paired:
                device.steps.add('Pair')
            if device.paired and device.connected:
                device.steps.add('Connect')
        elif kind == 'device_result' and device:
            device.status = {'ready':'ready', 'failed':'failed', 'retry':'waiting', 'not_attempted':'unavailable'}[event['outcome']]
            if device.status == 'waiting':
                device.retry_at = now + event['retry_after_s']
            if device.status == 'ready':
                device.steps.update(('Pair', 'Connect'))
            self.active = ''
        elif kind == 'run_end':
            self.finish(event['exit_status'])

    def finish(self, status: int):
        self.exit_status = status
        self.finished_at = self.clock()
        self.action = ''
        for device in self.devices.values():
            if device.status not in ('ready', 'failed', 'unavailable'):
                if self.preview and status == 0:
                    device.status = 'preview'
                elif status in (130, 143):
                    device.status = 'cancelled'
                else:
                    device.status = 'failed'

    @property
    def elapsed(self) -> float:
        return (self.finished_at if self.finished_at is not None else self.clock()) - self.started

    def pulse(self) -> str:
        return '·' if self.finished_at is not None else SPINNER[int(self.elapsed * 8) % len(SPINNER)]

    def device_card(self, device: Device, compact: bool = False):
        icon, kind = device.kind
        states = {
            'ready': ('✓ READY', MINT), 'failed': ('! NEEDS ATTENTION', ROSE),
            'cancelled': ('— STOPPED', AMBER), 'preview': ('◇ SELECTED', VIOLET),
            'unavailable': ('— NOT CHECKED', AMBER),
            'waiting': (f'{self.pulse()} RETRYING', AMBER), 'queued': ('· UP NEXT', FAINT),
            'active': (f'{self.pulse()} {device.phase.upper() or "CHECKING"}', VIOLET),
        }
        label, color = states[device.status]
        top = Table.grid(expand=True, padding=0)
        top.add_column(ratio=1)
        top.add_column(justify='right')
        top.add_row(text(f'{icon}  {kind}', f'bold {MUTED}'), text(label, f'bold {color}'))
        name = text(device.name, f'bold {INK}', overflow='ellipsis', no_wrap=True)
        rail = Text()
        for index, step in enumerate(('Release', 'Pair', 'Connect')):
            if index:
                rail.append('  ─  ', LINE)
            achieved = step in device.steps
            current = device.status == 'active' and device.phase == step
            rail.append(('✓ ' if achieved else '● ' if current else '· ') + step,
                        MINT if achieved else VIOLET if current else FAINT)
        if device.status == 'ready':
            detail = 'Connected to this Mac.' if device.touched else 'Already here. Kept connected.'
        elif device.status == 'unavailable':
            detail = 'Bluetooth stopped before this device could be checked.'
        elif device.status == 'waiting':
            remaining = max(0, int((device.retry_at or self.clock()) - self.clock() + .99))
            detail = f'Giving Bluetooth a moment · round {device.round + 1} next'
            if remaining:
                detail = f'Next try in {remaining}s · you can switch this device on now'
        elif device.status == 'failed':
            detail = 'Switch it off/on, then try again.'
        elif device.status == 'cancelled':
            detail = 'Saved for your next attempt.'
        elif device.status == 'preview':
            detail = 'Preview only · no connection changes'
        elif device.status == 'active':
            detail = {'Release':'Clearing the previous local connection.',
                      'Pair':'Establishing a fresh pairing.',
                      'Connect':'Opening the wireless connection.'}.get(device.phase, 'Checking the current connection.')
            if self.action and device.address == self.active:
                left = max(0, self.action_limit - (self.clock() - self.action_started))
                detail += f' Up to {left:.0f}s.'
        else:
            detail = 'Waiting its turn.'
        rows = [top, name]
        if not compact:
            rows += [text(''), rail]
        rows += [text(detail, MUTED, overflow='ellipsis', no_wrap=compact)]
        return Panel(Group(*rows), box=box.ROUNDED, padding=(1 if not compact else 0, 2 if not compact else 1),
                     style=f'{INK} on {CARD}', border_style=color if device.status in ('active', 'ready', 'failed') else LINE)

    def render(self, width: int = 96, height: int = 30):
        narrow = width < 78
        tight = height < 25 or width < 58 or len(self.devices) > 2
        finished = self.finished_at is not None
        success = finished and self.exit_status == 0
        cancelled = self.exit_status in (130, 143)
        color = MINT if success and not self.preview else AMBER if cancelled else ROSE if finished and not success else VIOLET
        header = Table.grid(expand=True)
        header.add_column(ratio=1)
        header.add_column(justify='right')
        brand = Text('✦  MAGIC ', style=f'bold {INK}')
        brand.append('/ REPAIR', VIOLET)
        header.add_row(brand, text(f'v{VERSION}', FAINT))
        if self.demo:
            eyebrow = 'DESIGN PREVIEW · NO BLUETOOTH CHANGES'
        elif self.preview:
            eyebrow = 'PREVIEW · THIS MAC'
        else:
            eyebrow = 'DEVICE HANDOFF  →  THIS MAC'
        if success:
            title = 'Your desk. Back in sync.' if not self.preview else 'Here’s the plan.'
            ready = sum(d.status == 'ready' for d in self.devices.values())
            subtitle = f'{ready} of {len(self.devices)} devices connected · {self.elapsed:.1f}s total' if not self.preview else f'{len(self.devices)} matching devices · nothing changed'
        elif cancelled:
            title, subtitle = 'Paused by you.', 'Your saved devices are ready for another attempt.'
        elif finished:
            title = 'Let’s finish the connection.'
            ready = sum(d.status == 'ready' for d in self.devices.values())
            subtitle = f'{ready} of {len(self.devices)} devices connected · the rest can be retried'
        elif self.scanning and not self.scan_finished:
            title, subtitle = 'Finding your devices.', 'Switch your Keyboard or Trackpad on now.'
        elif self.devices:
            title, subtitle = 'Bringing your desk together.', 'Switch your devices on. We’ll take it from here.'
        else:
            title, subtitle = 'A little magic. All connected.', 'Checking your saved devices and Bluetooth.'
        hero = Group(text(eyebrow, f'bold {color}'), text(title, f'bold {INK}'), text(subtitle, MUTED))
        items = list(self.devices.values())
        if items and not narrow and len(items) == 2:
            cards = Table.grid(expand=True, padding=(0, 1))
            cards.add_column(ratio=1)
            cards.add_column(ratio=1)
            cards.add_row(*(self.device_card(d, tight) for d in items))
        elif items:
            cards = Group(*(self.device_card(d, tight) for d in items))
        else:
            title_line = Text(f'{self.pulse()}  ' + ('Searching nearby' if self.scanning else 'Preparing the handoff'), style=f'bold {VIOLET}')
            detail = 'Known devices stay remembered. New names must match your filter.'
            if self.action == '--inquiry':
                elapsed = self.clock() - self.action_started
                detail = f'{elapsed:.0f}s elapsed · up to {max(0, self.action_limit - elapsed):.0f}s left in this search'
            cards = Panel(Group(title_line, text(detail, MUTED)), box=box.ROUNDED, border_style=LINE,
                          style=f'{INK} on {CARD}', padding=(1, 2))
        footer = Table.grid(expand=True)
        footer.add_column(ratio=1)
        footer.add_column(justify='right')
        if finished:
            footer.add_row(text('✓  All set.' if success and not self.preview else '◇  Preview complete.' if success else '↻  Run magic-repair to retry.', color), text(f'{self.elapsed:.1f}s', MUTED))
        else:
            footer.add_row(text(f'{self.pulse()}  Working locally', MUTED), text('CTRL C  Cancel', MUTED))
        contents = [header, text(''), hero, text(''), cards, text(''), footer]
        if self.log_path and finished:
            contents += [text(f'Diagnostics  {self.log_path}', FAINT, overflow='fold')]
        estimated_height = 13 + (5 * len(items) if narrow else 5)
        if width < 40 or height < min(estimated_height, 24):
            rows = [header, text(title, f'bold {color}')]
            for device in items:
                rows += [text(device.name, INK, overflow='ellipsis', no_wrap=True),
                         text(f'  {device.status.upper()}', MINT if device.status == 'ready' else VIOLET)]
            rows += [footer]
            contents = rows
        return Align.left(Panel(Group(*contents), box=box.ROUNDED, style=f'{INK} on {BG}',
                                border_style=LINE, padding=(1, 2 if width >= 58 else 1),
                                width=min(width, 104)))


class TerminalView:
    def __init__(self, console: Console, model: Dashboard):
        self.console, self.model = console, model
        self.live = None
        self.paused = False
        self.raw_open_line = False

    def refresh(self):
        if self.paused:
            return
        frame = self.model.render(self.console.width, self.console.height)
        if self.live is None:
            self.live = Live(frame, console=self.console, auto_refresh=False, transient=True,
                             redirect_stdout=False, redirect_stderr=False, vertical_overflow='crop')
            self.live.start(refresh=True)
        else:
            self.live.update(frame, refresh=True)

    def raw(self, data: bytes):
        # Prompts without a trailing newline stay raw so stdin editing is intact.
        if not self.paused:
            self.stop()
            self.paused = True
        if data.endswith(b'\n') and not self.raw_open_line:
            self.console.print(Panel(text(data.decode('utf-8', 'replace').rstrip(), MUTED),
                                     title=text('Bluetooth response', AMBER), box=box.ROUNDED,
                                     border_style=LINE, style=f'{INK} on {BG}', width=min(self.console.width, 104)))
        else:
            sys.stderr.buffer.write(data)
            sys.stderr.buffer.flush()
        self.raw_open_line = not data.endswith(b'\n')

    def resume(self):
        if self.raw_open_line:
            sys.stderr.write('\n')
            sys.stderr.flush()
        self.raw_open_line = False
        self.paused = False

    def stop(self):
        if self.live:
            self.live.stop()
            self.live = None

    def finish(self):
        self.stop()
        self.resume()
        self.console.print(self.model.render(self.console.width, self.console.height))


def run_engine(engine: str, args: list[str], console: Console, engine_shell: str = '/bin/bash') -> int:
    model = Dashboard(args)
    view = TerminalView(console, model)
    read_fd, write_fd = os.pipe()
    env = dict(os.environ, MAGIC_REPAIR_UI_ACTIVE='1', MAGIC_REPAIR_UI_FD=str(write_fd))
    # Stay in the terminal's session so pairing can read its real stdin. Starting
    # another session can revoke a pseudo-terminal when its leader exits on macOS.
    process = subprocess.Popen([engine_shell, engine, *args], env=env, stdin=None,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               pass_fds=(write_fd,))
    os.close(write_fd)
    selector = selectors.DefaultSelector()
    selector.register(read_fd, selectors.EVENT_READ, 'event')
    selector.register(process.stdout, selectors.EVENT_READ, 'stdout')
    selector.register(process.stderr, selectors.EVENT_READ, 'stderr')
    event_buffer = b''
    output_tail = collections.deque(maxlen=16)
    old_handlers = {}

    def interrupt(signum, _frame):
        if process.poll() is None:
            try:
                process.send_signal(signum)
            except ProcessLookupError:
                pass

    for signum in (signal.SIGINT, signal.SIGTERM):
        old_handlers[signum] = signal.signal(signum, interrupt)
    try:
        view.refresh()
        while selector.get_map():
            # A prompt/error was written before the engine's call_end event.
            # Drain stderr first so it cannot arrive just after a resume.
            ready = sorted(selector.select(.125), key=lambda pair: pair[0].data != 'stderr')
            for key, _mask in ready:
                data = os.read(key.fd, 65536)
                if not data:
                    selector.unregister(key.fileobj)
                    continue
                if key.data == 'stderr':
                    view.raw(data)
                elif key.data == 'stdout':
                    output_tail.append(data.decode('utf-8', 'replace'))
                else:
                    event_buffer += data
                    while b'\n' in event_buffer:
                        line, event_buffer = event_buffer.split(b'\n', 1)
                        event = json.loads(line)
                        model.consume(event)
                        if event.get('event') == 'call_end':
                            view.resume()
            view.refresh()
        status = process.wait()
        if model.exit_status is None:
            model.finish(status)
        view.finish()
        if not model.devices and status and output_tail:
            console.print(text(''.join(output_tail).strip(), ROSE))
        return status
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        view.stop()
        selector.close()
        os.close(read_fd)
        process.stdout.close()
        process.stderr.close()
        for signum, handler in old_handlers.items():
            signal.signal(signum, handler)


def demo(console: Console, static: bool = False) -> int:
    """A scripted visual preview. It never starts or imports the engine."""
    model = Dashboard(['--demo'])
    view = TerminalView(console, model)
    events = [
        (0.0, {'event':'selection', 'devices':[{'address':'demo-keyboard','name':'Magic Keyboard'}, {'address':'demo-trackpad','name':'Magic Trackpad'}]}),
        (.7, {'event':'device','address':'demo-keyboard','round':1,'remaining_s':45}),
        (.8, {'event':'call_start','address':'demo-keyboard','action':'--unpair','limit_s':5}),
        (1.4, {'event':'state','address':'demo-keyboard','paired':False,'connected':False}),
        (1.5, {'event':'call_start','address':'demo-keyboard','action':'--pair','limit_s':12}),
        (2.7, {'event':'state','address':'demo-keyboard','paired':True,'connected':True}),
        (2.8, {'event':'device_result','address':'demo-keyboard','outcome':'ready'}),
        (3.0, {'event':'device','address':'demo-trackpad','round':1,'remaining_s':45}),
        (3.1, {'event':'call_start','address':'demo-trackpad','action':'--pair','limit_s':12}),
        (4.0, {'event':'device_result','address':'demo-trackpad','outcome':'retry','retry_after_s':2}),
        (6.0, {'event':'device','address':'demo-trackpad','round':2,'remaining_s':42}),
        (6.1, {'event':'call_start','address':'demo-trackpad','action':'--pair','limit_s':12}),
        (7.0, {'event':'state','address':'demo-trackpad','paired':True,'connected':False}),
        (7.1, {'event':'call_start','address':'demo-trackpad','action':'--connect','limit_s':8}),
        (8.0, {'event':'state','address':'demo-trackpad','paired':True,'connected':True}),
        (8.1, {'event':'device_result','address':'demo-trackpad','outcome':'ready'}),
    ]
    try:
        for at, event in events:
            while not static and model.elapsed < at:
                view.refresh()
                time.sleep(.125)
            model.consume(event)
            if not static:
                view.refresh()
        model.finish(0)
        view.finish()
        return 0
    except KeyboardInterrupt:
        model.finish(130)
        view.finish()
        return 130
    finally:
        view.stop()


def show_help(console: Console):
    header = Group(text('✦  MAGIC / REPAIR', f'bold {VIOLET}'), text('Your devices. On this Mac.', f'bold {INK}'),
                   text('Power-cycle your accessories, then run magic-repair.', MUTED))
    groups = [
        ('EVERYDAY', [('magic-repair','Bring remembered devices here'), ('--scan','Find and add a new device'), ('--dry-run / --list','Preview the plan / list targets'), ('--demo','Watch the design preview; no Bluetooth access')]),
        ('RECOVERY', [('--force','Renew an already connected device'), ('--reconnect','Keep pairing; refresh the connection'), ('--diagnose','Save private local diagnostics'), ('--timeout N','Total device budget, default 45s'), ('--attempts N','Recovery rounds, default 3'), ('--pair-timeout N','Pairing limit, default 12s; 30s with --scan')]),
        ('SELECTION & HELP', [('-s / --search TERM','All literal terms must match; repeatable'), ('-d / --device MAC','Select exact addresses; repeatable'), ('--config FILE','Use a different configuration'), ('--no-color','Respect a monochrome terminal'), ('-h / --help','Show this guide'), ('-v / --version','Show version')]),
    ]
    contents = [header]
    for label, options in groups:
        table = Table.grid(padding=(0, 3), expand=True)
        table.add_column(style=INK, min_width=20)
        table.add_column(style=MUTED, ratio=1)
        for flag, description in options:
            table.add_row(text(flag), text(description, MUTED))
        contents += [text(''), text(label, f'bold {VIOLET}'), table]
    contents += [text(''), text('Default filter: Magic + Jonas · dependencies: blueutil, jq', MUTED),
                 text('Logs & targets: ~/.local/state/magic-repair (respects XDG_STATE_HOME)', FAINT)]
    console.print(Panel(Group(*contents), box=box.ROUNDED, padding=(1, 2), border_style=LINE,
                        style=f'{INK} on {BG}', width=min(console.width, 104)))


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--engine', required=True)
    parser.add_argument('--engine-shell', default='/bin/bash')
    opts, args = parser.parse_known_args()
    if args[:1] == ['--']:
        args = args[1:]
    console = Console(highlight=False, no_color='--no-color' in args or 'NO_COLOR' in os.environ)
    if '--demo' in args:
        static = not console.is_terminal or os.environ.get('TERM') == 'dumb'
        if static:
            console = Console(highlight=False, force_terminal=False, color_system=None)
        return demo(console, static)
    if '--help' in args or '-h' in args:
        show_help(console)
        return 0
    return run_engine(str(Path(opts.engine).resolve()), args, console, opts.engine_shell)


if __name__ == '__main__':
    raise SystemExit(main())
