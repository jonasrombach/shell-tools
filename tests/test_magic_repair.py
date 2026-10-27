"""Behavior tests with a stateful blueutil double; never touch real Bluetooth."""
import json
import os
import pty
import signal
from copy import deepcopy
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/magic-repair'
TEST_BASH = os.environ.get('TEST_BASH', '/bin/bash')
MAC = 'aa:bb:cc:dd:ee:01'
OTHER = 'aa:bb:cc:dd:ee:02'
FAKE = r'''#!/usr/bin/env python3
import json, os, sys, time
from pathlib import Path
p = Path(os.environ['FAKE_STATE'])
s = json.loads(p.read_text())
a = sys.argv[1:]
with open(os.environ['FAKE_LOG'], 'a') as f: f.write(json.dumps(a) + '\n')
cmd = a[0]
d = next((d for d in s['devices'] if len(a)>1 and d['address']==a[1]), None)
if cmd == s.get('hang'):
    if s.get('pair_before_hang'):
        d['paired'] = True
        p.write_text(json.dumps(s))
    Path(os.environ['FAKE_STATE'] + '.pid').write_text(str(os.getpid()))
    time.sleep(60)
if cmd == s.get('fail_once') and not s.get('failed_once') and (not s.get('fail_once_device') or a[1] == s['fail_once_device']):
    s['failed_once'] = True
    p.write_text(json.dumps(s))
    sys.exit(1)
if cmd == s.get('fail'):
    print(s.get('fail_message', 'simulated failure'), file=sys.stderr)
    sys.exit(s.get('fail_code', 1))
if cmd == '--info' and s.get('pending_unpair'):
    s['pending_unpair'] -= 1
    if s['pending_unpair'] == 0: d.update(paired=False, connected=False)
if cmd == '--info' and s.get('align_pair') and not s.get('aligned') and not d['paired']:
    # Start the next pairing call shortly before a wall-clock second changes.
    time.sleep((0.8 - time.time() % 1) % 1)
    s['aligned'] = True
if cmd == '--version': print('2.14.0-test')
elif cmd == '--paired':
    print(s.get('raw', json.dumps([d for d in s['devices'] if d['paired']])))
elif cmd == '--inquiry':
    time.sleep(s.get('inquiry_delay', 0))
    print(s.get('inquiry_raw', json.dumps(s.get('nearby', []))))
elif cmd == '--power': print(s.get('power', 1))
elif cmd == '--is-connected': print(int(d['connected']) if d else 0)
elif cmd == '--info': print(s.get('info_raw', json.dumps(d or {'address':a[1], 'paired':False, 'connected':False})))
elif cmd == '--unpair':
    if s.get('unpair_after_reads'): s['pending_unpair'] = s['unpair_after_reads']
    elif not s.get('sticky'): d.update(paired=False, connected=False)
elif cmd == '--pair':
    time.sleep(s.get('pair_delay', 0))
    if s.get('prompt'):
        print('Input passkey 123456 on "Magic Keyboard"', file=sys.stderr)
    if not d:
        d = dict(address=a[1], name=a[1], connected=False)
        nearby = next((x for x in s.get('nearby', []) if x['address'].lower().replace('-', ':') == a[1]), None)
        if nearby: d['name'] = nearby['name']
        s['devices'].append(d)
    d['paired'] = True
    if s.get('auto_connect_on_pair'): d['connected'] = True
elif cmd == '--connect':
    if not d or not d['paired']: sys.exit(1)
    if not s.get('false_connect'): d['connected'] = True
elif cmd == '--disconnect': d['connected'] = False
elif cmd == '--wait-connect':
    if not d['connected']: sys.exit(75)
else: sys.exit(64)
p.write_text(json.dumps(s))
if cmd == s.get('mutate_then_fail'): sys.exit(1)
'''


class MagicRepairTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        (self.bin / 'blueutil').write_text(FAKE)
        (self.bin / 'blueutil').chmod(0o755)
        self.state = self.root / 'fake.json'
        self.log = self.root / 'calls.jsonl'
        self.config = self.root / 'config'
        self.config.write_text('search_terms="Magic Jonas"\n')
        self.data = {'devices': [dict(address=MAC, name='Magic Trackpad Jonas', paired=True, connected=False)]}
        self.save()
        self.env = dict(os.environ, PATH=str(self.bin) + ':' + os.environ['PATH'],
                        XDG_STATE_HOME=str(self.root / 'state'),
                        XDG_DATA_HOME=str(self.root / 'data'),
                        MAGIC_REPAIR_UI_ACTIVE='1',
                        FAKE_STATE=str(self.state), FAKE_LOG=str(self.log))

    def save(self):
        self.state.write_text(json.dumps(self.data))

    def run_tool(self, *args):
        return subprocess.run([TEST_BASH, str(SCRIPT), '--config', str(self.config),
                               '--attempts', '1', *args], env=self.env, text=True,
                              capture_output=True, timeout=25)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def mutations(self):
        return [a for a in self.calls() if a[0] in ('--pair', '--unpair', '--connect', '--disconnect')]

    def test_default_repairs_and_verifies(self):
        result = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([a[0] for a in self.mutations()], ['--unpair', '--pair', '--connect'])
        self.assertIn(['--info', MAC, '--format', 'json'], self.calls())
        self.assertIn('1 connected, 0 failed', result.stdout)

    def test_permission_denied_stops_before_bluetooth_or_pairing(self):
        permission_python = self.root / 'data/shell-tools/magic-repair-ui/bin/python'
        permission_python.parent.mkdir(parents=True)
        permission_python.write_text('#!/bin/bash\nprintf "denied\\n"\n')
        permission_python.chmod(0o755)
        result = self.run_tool('--diagnose')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual([a[0] for a in self.calls()], ['--version'])
        events = self.diagnostic_events()
        self.assertTrue(any(e['event'] == 'failure' and e['reason'] == 'bluetooth_access' for e in events))
        self.assertIn('Quit and reopen', result.stderr)

    def test_permission_helper_abort_is_not_reported_as_missing_dependencies(self):
        permission_python = self.root / 'data/shell-tools/magic-repair-ui/bin/python'
        permission_python.parent.mkdir(parents=True)
        for code in (134, 137):
            with self.subTest(exit_status=code):
                permission_python.write_text(f'#!/bin/bash\nexit {code}\n')
                permission_python.chmod(0o755)
                result = self.run_tool('--diagnose')
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(self.mutations(), [])
                self.assertIn('Privacy & Security > Bluetooth', result.stderr)
                self.assertNotIn('refresh the dependencies', result.stderr)
                events = self.diagnostic_events()
                self.assertTrue(any(e['event'] == 'permission' and e['state'] == 'aborted' for e in events))

    def test_undecided_permission_stops_before_discovery(self):
        permission_python = self.root / 'data/shell-tools/magic-repair-ui/bin/python'
        permission_python.parent.mkdir(parents=True)
        permission_python.write_text('#!/bin/bash\nprintf "not_determined\\n"\n')
        permission_python.chmod(0o755)
        result = self.run_tool('--scan')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.calls(), [])
        self.assertIn('If it is missing, use +', result.stderr)

    def test_api_abort_reports_access_failure_before_selection(self):
        self.data.update(fail='--paired', fail_code=134)
        self.save()
        result = self.run_tool('--diagnose')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.mutations(), [])
        events = self.diagnostic_events()
        self.assertTrue(any(e['event'] == 'failure' and e['reason'] == 'bluetooth_access' for e in events))
        self.assertFalse(any(e['event'] == 'selection' for e in events))

    def test_search_works_as_first_selector_and_overrides_config(self):
        result = self.run_tool('-s', 'trackpad')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_literal_search_metacharacters_and_case(self):
        self.data['devices'][0]['name'] = 'MAGIC [Jonas].* "|\\'
        self.save()
        result = self.run_tool('-s', '[jonas].* "|\\')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.mutations()), 3)
        result = self.run_tool('-s', '.*other')
        self.assertEqual(result.returncode, 1)

    def test_null_name_and_and_matching(self):
        self.data['devices'] += [dict(address=OTHER, name=None, paired=True, connected=False)]
        self.save()
        result = self.run_tool('-s', 'Magic', '-s', 'Missing', '--list')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.mutations(), [])

    def test_search_term_preserves_embedded_newline(self):
        self.data['devices'][0]['name'] = 'Magic Jonas\nTrackpad'
        self.save()
        result = self.run_tool('-s', 'Jonas\nTrackpad', '--list')
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_tool('-s', 'Jonas\nMissing', '--list')
        self.assertEqual(result.returncode, 1)

    def test_preview_and_list_are_read_only(self):
        for option in ('--dry-run', '--list'):
            result = self.run_tool(option)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.mutations(), [])
        self.assertFalse((self.root / 'state').exists())

    def test_connected_skipped_unless_forced(self):
        self.data['devices'][0]['connected'] = True
        self.save()
        self.assertEqual(self.run_tool().returncode, 0)
        self.assertEqual(self.mutations(), [])
        self.assertEqual(self.run_tool('--force').returncode, 0)
        self.assertEqual(len(self.mutations()), 3)

    def test_reconnect_keeps_pairing(self):
        self.data['devices'][0]['connected'] = True
        self.save()
        self.assertEqual(self.run_tool('--reconnect').returncode, 0)
        self.assertEqual([a[0] for a in self.mutations()], ['--disconnect', '--connect'])

    def test_failed_pair_remembers_target_for_next_invocation(self):
        self.data['fail'] = '--pair'
        self.save()
        result = self.run_tool()
        self.assertEqual(result.returncode, 1)
        self.assertIn('0 connected, 1 failed', result.stdout)
        self.data = json.loads(self.state.read_text())
        self.assertFalse(self.data['devices'][0]['paired'])
        del self.data['fail']
        self.save()
        self.log.unlink()
        self.assertEqual(self.run_tool().returncode, 0)
        self.assertEqual([a[0] for a in self.mutations()], ['--pair', '--connect'])

    def test_explicit_unpaired_address_and_normalization(self):
        self.data['devices'] = []
        self.save()
        result = self.run_tool('--device', 'AA-BB-CC-DD-EE-01')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.mutations()[0], ['--pair', MAC])

    def test_discovery_failures_do_not_mutate(self):
        original = deepcopy(self.data)
        for change in ({'fail':'--paired'}, {'raw':'not json'}, {'raw':'{}'},
                       {'raw':'[{"address":"bad","name":"Magic Jonas"}]'}):
            self.data = deepcopy(original)
            self.data.update(change)
            self.save()
            self.assertEqual(self.run_tool().returncode, 1)
        self.assertEqual(self.mutations(), [])

    def test_bluetooth_off_does_not_mutate(self):
        self.data['power'] = 0
        self.save()
        self.assertEqual(self.run_tool().returncode, 1)
        self.assertEqual(self.mutations(), [])

    def test_unpair_failure_never_pairs(self):
        for change in ({'fail':'--unpair'}, {'sticky':True}):
            self.data.update(change)
            self.data.pop('fail', None) if 'sticky' in change else None
            self.save()
            self.assertEqual(self.run_tool().returncode, 1)
        self.assertTrue(all(a[0] == '--unpair' for a in self.mutations()))

    def test_successful_connect_command_requires_confirmed_connection(self):
        self.data['false_connect'] = True
        self.save()
        self.assertEqual(self.run_tool().returncode, 1)

    def test_partial_failure_continues_and_returns_failure(self):
        self.data['devices'].append(dict(address=OTHER, name='Magic Keyboard Jonas', paired=True, connected=True))
        self.data['fail'] = '--pair'
        self.save()
        result = self.run_tool()
        self.assertEqual(result.returncode, 1)
        self.assertIn('1 connected, 1 failed', result.stdout)

    def test_pair_timeout_is_bounded(self):
        self.data['hang'] = '--pair'
        self.save()
        result = self.run_tool('--timeout', '1')
        self.assertEqual(result.returncode, 1)
        self.assertTrue('Timed out' in result.stderr or 'budget exhausted' in result.stderr)

    def test_argument_validation_precedes_bluetooth(self):
        for args in (('-s',), ('--wat',), ('--attempts', '0'), ('--timeout', '301'),
                     ('--device','no'), ('--device', 'aa:bb-cc:dd:ee:01'),
                     ('--device', ':aabbccddee01'),
                     ('-s','Magic','-d',MAC), ('--attempts','01')):
            self.assertEqual(self.run_tool(*args).returncode, 2, args)
        self.assertEqual(self.calls(), [])

    def test_config_is_data_and_phrase_terms_work(self):
        marker = self.root / 'executed'
        self.config.write_text(f'search_term="$(touch {marker})"\n')
        self.assertEqual(self.run_tool('--list').returncode, 1)
        self.assertFalse(marker.exists())
        self.config.write_text('search_term="Magic Trackpad"\nsearch_term="Jonas"\n')
        self.assertEqual(self.run_tool('--list').returncode, 0)

    def test_corrupt_cache_stops_before_mutations(self):
        cache = self.root / 'state/magic-repair'
        cache.mkdir(parents=True)
        (cache / 'devices.json').write_text('{broken')
        self.assertEqual(self.run_tool().returncode, 1)
        self.assertEqual(self.mutations(), [])

    def test_retries_transient_pair_failure(self):
        self.data['fail_once'] = '--pair'
        self.save()
        result = self.run_tool('--attempts', '2')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([a[0] for a in self.mutations()], ['--unpair', '--pair', '--pair', '--connect'])

    def test_existing_lock_prevents_mutations(self):
        lock = self.root / 'state/magic-repair/repair.lock'
        lock.mkdir(parents=True)
        result = self.run_tool()
        self.assertEqual(result.returncode, 1)
        self.assertIn('Another repair', result.stderr)
        self.assertTrue(lock.is_dir())
        self.assertEqual(self.mutations(), [])

    def assert_signal_cleanup(self, *extra_args):
        self.data['hang'] = '--pair'
        self.save()
        proc = subprocess.Popen([TEST_BASH, str(SCRIPT), '--config', str(self.config), *extra_args],
                                env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True)
        self.addCleanup(lambda: proc.kill() if proc.poll() is None else None)
        pid_file = Path(str(self.state) + '.pid')
        deadline = time.monotonic() + 5
        while not pid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertTrue(pid_file.exists(), 'pair operation never started')
        child_pid = int(pid_file.read_text())
        proc.send_signal(signal.SIGTERM)
        proc.communicate(timeout=5)
        self.assertEqual(proc.returncode, 143)
        with self.assertRaises(ProcessLookupError):
            os.kill(child_pid, 0)
        self.assertFalse((self.root / 'state/magic-repair/repair.lock').exists())

    def test_signal_kills_active_child_and_releases_lock(self):
        self.assert_signal_cleanup()

    def test_remembers_only_selected_devices(self):
        self.data['devices'].append(dict(address=OTHER, name='Headphones', paired=True, connected=True))
        self.save()
        self.assertEqual(self.run_tool().returncode, 0)
        cache = json.loads((self.root / 'state/magic-repair/devices.json').read_text())
        self.assertEqual([d['address'] for d in cache], [MAC])

    def test_fixed_targets_in_config(self):
        self.config.write_text(f'device = "{MAC}"\n')
        result = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.mutations()[0], ['--unpair', MAC])

    def test_rejects_mixed_selectors_and_unclosed_quotes_in_config(self):
        for contents in (f'device="{MAC}"\nsearch_term="Magic"\n',
                         'search_term="Magic\n', 'search_term=\'Magic\n',
                         'search_term="\n', "search_term='\n"):
            self.config.write_text(contents)
            self.assertEqual(self.run_tool().returncode, 2)
        self.assertEqual(self.calls(), [])

    def test_cached_name_updates_when_device_renamed(self):
        self.assertEqual(self.run_tool().returncode, 0)
        self.data = json.loads(self.state.read_text())
        self.data['devices'][0]['name'] = 'Magic Keyboard Jonas'
        self.save()
        self.assertEqual(self.run_tool('--device', MAC).returncode, 0)
        cache = json.loads((self.root / 'state/magic-repair/devices.json').read_text())
        self.assertEqual(cache[0]['name'], 'Magic Keyboard Jonas')
        # Simulate pairing removal: discovery must now use the refreshed name.
        self.data['devices'][0].update(paired=False, connected=False)
        self.save()
        result = self.run_tool('-s', 'Keyboard')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_failed_pair_with_successful_side_effect_is_not_repeated(self):
        self.data['mutate_then_fail'] = '--pair'
        self.save()
        result = self.run_tool('--attempts', '3')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([a[0] for a in self.mutations()], ['--unpair', '--pair', '--connect'])

    def test_failed_connect_that_already_connected_is_success(self):
        self.data['mutate_then_fail'] = '--connect'
        self.save()
        self.assertEqual(self.run_tool('--attempts', '3').returncode, 0)
        self.assertEqual([a[0] for a in self.mutations()].count('--connect'), 1)

    def test_pair_that_connects_needs_no_redundant_connect(self):
        self.data['auto_connect_on_pair'] = True
        self.save()
        self.assertEqual(self.run_tool().returncode, 0)
        self.assertEqual([a[0] for a in self.mutations()], ['--unpair', '--pair'])

    def test_delayed_unpair_is_observed_not_reissued(self):
        self.data['unpair_after_reads'] = 2
        self.save()
        result = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([a[0] for a in self.mutations()].count('--unpair'), 1)

    def test_connect_retries_preserve_new_pairing(self):
        self.data['fail_once'] = '--connect'
        self.save()
        self.assertEqual(self.run_tool('--attempts', '2').returncode, 0)
        self.assertEqual([a[0] for a in self.mutations()], ['--unpair', '--pair', '--connect', '--connect'])

    def test_all_devices_get_first_attempt_before_retries(self):
        self.data['devices'].append(dict(address=OTHER, name='Magic Keyboard Jonas', paired=True, connected=False))
        self.data.update(fail_once='--pair', fail_once_device=MAC)
        self.save()
        result = self.run_tool('--attempts', '2')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([a[1] for a in self.mutations() if a[0] == '--pair'], [MAC, OTHER, MAC])

    def test_system_errors_stop_all_further_repair_attempts(self):
        for code in (64, 69, 70, 71, 134):
            with self.subTest(code=code):
                self.data.update(fail='--pair', fail_code=code)
                self.data['devices'][0].update(paired=True, connected=False)
                self.data['devices'] = self.data['devices'][:1] + [dict(address=OTHER, name='Magic Keyboard Jonas', paired=True, connected=False)]
                self.save()
                self.log.unlink(missing_ok=True)
                result = self.run_tool('--attempts', '3')
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual([a[0] for a in self.mutations()], ['--unpair', '--pair'])
                self.assertIn('Not completed', result.stderr)

    def test_connected_without_pairing_is_not_treated_as_success(self):
        self.data['devices'][0].update(paired=False, connected=True)
        self.save()
        result = self.run_tool('--device', MAC)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.mutations()[0], ['--pair', MAC])

    def test_reconnect_never_pairs_an_unpaired_device(self):
        self.data['devices'][0]['paired'] = False
        self.save()
        result = self.run_tool('--device', MAC, '--reconnect')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.mutations(), [])

    def test_pair_timeout_rechecks_before_retrying(self):
        self.data.update(hang='--pair', pair_before_hang=True)
        self.save()
        result = self.run_tool('--pair-timeout', '1', '--attempts', '2')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([a[0] for a in self.mutations()], ['--unpair', '--pair', '--connect'])

    def test_total_budget_caps_all_rounds(self):
        self.data['hang'] = '--pair'
        self.save()
        started = time.monotonic()
        result = self.run_tool('--attempts', '10', '--timeout', '2')
        self.assertEqual(result.returncode, 1)
        self.assertLess(time.monotonic() - started, 4)
        self.assertEqual([a[0] for a in self.mutations()].count('--pair'), 1)

    def test_invalid_state_fails_without_mutation_or_retry(self):
        self.data['info_raw'] = '{"paired":true}'
        self.save()
        self.assertEqual(self.run_tool('--attempts', '3').returncode, 1)
        self.assertEqual(self.mutations(), [])
        self.assertEqual([a[0] for a in self.calls()].count('--info'), 1)

    def test_wait_feedback_and_plain_redirected_output(self):
        self.data['hang'] = '--pair'
        self.save()
        result = self.run_tool('--timeout', '7')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('Still pairing', result.stderr)
        self.assertIn('Ctrl-C cancels', result.stdout)
        self.assertNotIn('\x1b', result.stdout + result.stderr)

    def test_force_is_not_skipped_after_transient_state_query_failure(self):
        self.data['devices'][0]['connected'] = True
        self.data['fail_once'] = '--info'
        self.save()
        result = self.run_tool('--force', '--attempts', '2')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([a[0] for a in self.mutations()], ['--unpair', '--pair', '--connect'])

    def test_terminal_colors_respect_no_color_and_dumb_terminal(self):
        for args, override, colored in (((), {}, True), (('--no-color',), {}, False),
                                        ((), {'NO_COLOR':''}, False), ((), {'TERM':'dumb'}, False)):
            with self.subTest(args=args, override=override):
                master, slave = pty.openpty()
                try:
                    env = dict(self.env, TERM='xterm-256color')
                    env.pop('NO_COLOR', None)
                    env.update(override)
                    # An already connected device exercises UI without changing pairing.
                    self.data['devices'][0]['connected'] = True
                    self.save()
                    result = subprocess.run([TEST_BASH, str(SCRIPT), '--config', str(self.config), *args],
                                            env=env, stdout=slave, stderr=slave, timeout=10)
                    # Keep our slave FD open while draining: macOS can discard
                    # queued PTY output when the last slave descriptor closes.
                    os.set_blocking(master, False)
                    output = b''
                    while True:
                        try:
                            chunk = os.read(master, 4096)
                        except (BlockingIOError, OSError):
                            break
                        if not chunk:
                            break
                        output += chunk
                    self.assertEqual(result.returncode, 0, output)
                    self.assertEqual(b'\x1b[' in output, colored, output)
                finally:
                    if slave is not None:
                        os.close(slave)
                    os.close(master)

    def diagnostic_events(self):
        latest = self.root / 'state/magic-repair/logs/latest.jsonl'
        return [json.loads(line) for line in latest.read_text().splitlines()]

    def test_diagnostics_log_states_timings_and_exit_status(self):
        result = self.run_tool('--diagnose')
        self.assertEqual(result.returncode, 0, result.stderr)
        events = self.diagnostic_events()
        self.assertEqual(events[0]['event'], 'run_start')
        self.assertEqual(events[-1]['event'], 'run_end')
        self.assertEqual(events[-1]['exit_status'], 0)
        self.assertTrue(any(e['event'] == 'dependency' and e['blueutil_version'] == '2.14.0-test' for e in events))
        self.assertTrue(any(e['event'] == 'state' and e['paired'] and e['connected'] for e in events))
        starts = [e for e in events if e['event'] == 'call_start']
        ends = [e for e in events if e['event'] == 'call_end']
        self.assertEqual(len(starts), len(ends))
        self.assertTrue(all(end['timestamp'] >= start['timestamp'] for start, end in zip(starts, ends)))
        latest = self.root / 'state/magic-repair/logs/latest.jsonl'
        self.assertEqual(latest.stat().st_mode & 0o777, 0o600)
        self.assertEqual(latest.resolve().parent.stat().st_mode & 0o777, 0o700)

    def test_diagnostic_prompts_remain_visible_without_persisting_pin(self):
        self.data['prompt'] = True
        self.save()
        result = self.run_tool('--diagnose')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('123456', result.stderr)
        self.assertNotIn('123456', json.dumps(self.diagnostic_events()))

    def test_diagnostics_capture_hci_code_and_failed_run(self):
        self.data.update(fail='--pair', fail_message='Failed to pair "address" with error 0x05 (Authentication Failure)')
        self.save()
        result = self.run_tool('--diagnose')
        self.assertEqual(result.returncode, 1)
        events = self.diagnostic_events()
        self.assertTrue(any(e.get('hci_error') == '0x05' for e in events))
        self.assertEqual(events[-1]['exit_status'], 1)

    def test_diagnostic_preview_logs_but_does_not_save_targets_or_mutate(self):
        self.assertEqual(self.run_tool('--diagnose', '--dry-run').returncode, 0)
        self.assertEqual(self.mutations(), [])
        self.assertFalse((self.root / 'state/magic-repair/devices.json').exists())
        self.assertEqual(self.diagnostic_events()[-1]['exit_status'], 0)

    def test_diagnostics_log_timeout_and_cleanup_capture_child(self):
        self.data['hang'] = '--pair'
        self.save()
        result = self.run_tool('--diagnose', '--timeout', '3')
        self.assertEqual(result.returncode, 1)
        events = self.diagnostic_events()
        self.assertTrue(any(e.get('timed_out') for e in events))
        self.assertEqual(events[-1]['exit_status'], 1)

    def test_diagnostics_record_interruption_and_clean_up_children(self):
        self.assert_signal_cleanup('--diagnose')
        self.assertEqual(self.diagnostic_events()[-1]['exit_status'], 143)

    def test_one_second_limit_does_not_expire_at_next_clock_tick(self):
        self.data['devices'][0]['paired'] = False
        self.data.update(align_pair=True, pair_delay=0.4)
        self.save()
        result = self.run_tool('--device', MAC, '--pair-timeout', '1', '--diagnose')
        self.assertEqual(result.returncode, 0, result.stderr)
        events = self.diagnostic_events()
        self.assertFalse(any(e.get('timed_out') for e in events), events)

    def test_scan_adds_matching_unpaired_devices_and_remembers_them(self):
        self.data['nearby'] = [dict(address=OTHER, name='Magic Keyboard von Jonas', paired=False, connected=False),
                               dict(address='aa:bb:cc:dd:ee:03', name='Someone else Magic Mouse', paired=False, connected=False)]
        self.save()
        result = self.run_tool('--scan', '--diagnose')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(['--pair', OTHER], self.mutations())
        self.assertNotIn(['--pair', 'aa:bb:cc:dd:ee:03'], self.mutations())
        cache = json.loads((self.root / 'state/magic-repair/devices.json').read_text())
        self.assertEqual({x['address'] for x in cache}, {MAC, OTHER})
        self.assertTrue(any(e['event'] == 'discovery' for e in self.diagnostic_events()))
        # The next ordinary invocation must recover the keyboard without scanning.
        self.data = json.loads(self.state.read_text())
        for device in self.data['devices']: device.update(paired=False, connected=False)
        self.data['nearby'] = []
        self.save()
        self.log.unlink()
        result = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('--inquiry', [a[0] for a in self.calls()])
        self.assertIn(['--pair', OTHER], self.mutations())

    def test_scan_preview_is_read_only_and_deduplicates_addresses(self):
        self.data['nearby'] = [dict(address=MAC.upper().replace(':', '-'), name='Magic Trackpad Jonas', paired=True, connected=False)]
        self.save()
        result = self.run_tool('--scan', '--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Selected 1 device', result.stdout)
        self.assertEqual(self.mutations(), [])
        self.assertFalse((self.root / 'state').exists())

    def test_scan_failure_stops_before_changing_known_devices(self):
        self.data['fail'] = '--inquiry'
        self.save()
        self.assertEqual(self.run_tool('--scan').returncode, 1)
        self.assertEqual(self.mutations(), [])

    def test_scan_rejects_malformed_discovery_data(self):
        self.data['inquiry_raw'] = '[{"address":"bad","name":"Magic Jonas"}]'
        self.save()
        self.assertEqual(self.run_tool('--scan').returncode, 1)
        self.assertEqual(self.mutations(), [])

    def test_null_scanned_name_preserves_known_matching_name(self):
        self.data['nearby'] = [dict(address=MAC, name=None, paired=True, connected=False)]
        self.save()
        result = self.run_tool('--scan', '--list')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Magic Trackpad Jonas', result.stdout)

    def test_scan_allows_human_confirmation_and_respects_override(self):
        for args, expected in ((('--scan',), 30),
                               (('--pair-timeout', '7', '--scan'), 7),
                               (('--scan', '--pair-timeout', '8'), 8)):
            with self.subTest(args=args):
                result = self.run_tool(*args, '--diagnose', '--dry-run')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.diagnostic_events()[0]['pair_timeout'], expected)

    def test_scan_without_matching_devices_does_not_pair_or_save_targets(self):
        self.data['devices'] = []
        self.data['nearby'] = [dict(address=OTHER, name='Magic Keyboard Other Person', paired=False, connected=False)]
        self.save()
        self.assertEqual(self.run_tool('--scan').returncode, 1)
        self.assertEqual(self.mutations(), [])
        self.assertFalse((self.root / 'state/magic-repair/devices.json').exists())

    def test_scan_with_bluetooth_off_does_not_inquire_or_mutate(self):
        self.data['power'] = 0
        self.save()
        self.assertEqual(self.run_tool('--scan').returncode, 1)
        self.assertNotIn('--inquiry', [a[0] for a in self.calls()])
        self.assertEqual(self.mutations(), [])

    def test_reported_total_duration_includes_discovery(self):
        self.data['devices'][0]['connected'] = True
        self.data['inquiry_delay'] = 2
        self.save()
        result = self.run_tool('--scan', '--diagnose')
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = next(e for e in self.diagnostic_events() if e['event'] == 'result')
        self.assertGreaterEqual(summary['duration_s'], 2)


if __name__ == '__main__':
    unittest.main()
