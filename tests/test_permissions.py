"""Exercise permission transitions without displaying real system dialogs."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('permissions', Path(__file__).resolve().parents[1] / 'scripts/lib/magic-repair/permissions.py')
permissions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(permissions)


class NSObject:
    @classmethod
    def alloc(cls):
        return cls()

    def init(self):
        return self


class PermissionTests(unittest.TestCase):
    def setUp(self):
        self.bluetooth = SimpleNamespace(
            CBManagerAuthorizationNotDetermined=0, CBManagerAuthorizationRestricted=1,
            CBManagerAuthorizationDenied=2, CBManagerAuthorizationAllowedAlways=3,
            CBManager=Mock(), CBCentralManager=Mock(), CBCentralManagerOptionShowPowerAlertKey='powerAlert')
        foundation = SimpleNamespace(NSObject=NSObject, NSDate=Mock(), NSRunLoop=Mock())
        context = patch.dict(sys.modules, CoreBluetooth=self.bluetooth, Foundation=foundation)
        context.start()
        self.addCleanup(context.stop)

    def test_decided_permission_never_requests_again(self):
        for value, expected in ((1, 'restricted'), (2, 'denied'), (3, 'allowed')):
            self.bluetooth.CBManager.authorization.return_value = value
            self.assertEqual(permissions.check(request=True), expected)
        self.bluetooth.CBCentralManager.alloc.assert_not_called()

    def test_noninteractive_check_does_not_prompt(self):
        self.bluetooth.CBManager.authorization.return_value = 0
        self.assertEqual(permissions.check(), 'not_determined')
        self.bluetooth.CBCentralManager.alloc.assert_not_called()

    def test_allow_continues_after_native_request(self):
        self.bluetooth.CBManager.authorization.side_effect = [0, 3]
        self.assertEqual(permissions.check(request=True), 'allowed')
        options = self.bluetooth.CBCentralManager.alloc.return_value.initWithDelegate_queue_options_.call_args.args[2]
        self.assertEqual(options, {'powerAlert': False})

    def test_unanswered_request_is_bounded(self):
        self.bluetooth.CBManager.authorization.return_value = 0
        self.assertEqual(permissions.check(request=True, timeout=0), 'timed_out')
