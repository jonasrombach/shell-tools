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


class PermissionTests(unittest.TestCase):
    def setUp(self):
        self.bluetooth = SimpleNamespace(
            CBManagerAuthorizationNotDetermined=0, CBManagerAuthorizationRestricted=1,
            CBManagerAuthorizationDenied=2, CBManagerAuthorizationAllowedAlways=3,
            CBManager=Mock(), CBCentralManager=Mock())
        context = patch.dict(sys.modules, CoreBluetooth=self.bluetooth)
        context.start()
        self.addCleanup(context.stop)

    def test_authorization_is_read_without_requesting_or_scanning(self):
        for value, expected in ((0, 'not_determined'), (1, 'restricted'), (2, 'denied'), (3, 'allowed'), (99, 'unavailable')):
            with self.subTest(state=expected):
                self.bluetooth.CBManager.authorization.return_value = value
                self.assertEqual(permissions.check(), expected)
        self.bluetooth.CBCentralManager.alloc.assert_not_called()
