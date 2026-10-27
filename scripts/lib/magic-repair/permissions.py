"""Request native Bluetooth consent without scanning, pairing or changing power.

macOS attributes command-line access to the responsible host application.
Already denied/restricted access must be resolved in Settings/by its administrator.
"""
import sys
import time


def check(request=False, timeout=60):
    import CoreBluetooth as bluetooth
    from Foundation import NSDate, NSObject, NSRunLoop

    states = {
        bluetooth.CBManagerAuthorizationAllowedAlways: 'allowed',
        bluetooth.CBManagerAuthorizationDenied: 'denied',
        bluetooth.CBManagerAuthorizationRestricted: 'restricted',
        bluetooth.CBManagerAuthorizationNotDetermined: 'not_determined',
    }
    state = states.get(bluetooth.CBManager.authorization(), 'unavailable')
    if state != 'not_determined' or not request:
        return state

    class PermissionDelegate(NSObject):
        def centralManagerDidUpdateState_(self, manager):
            pass

    print('Allow Bluetooth access in the macOS dialog to continue (up to 60s).', file=sys.stderr, flush=True)
    delegate = PermissionDelegate.alloc().init()
    manager = bluetooth.CBCentralManager.alloc().initWithDelegate_queue_options_(
        delegate, None, {bluetooth.CBCentralManagerOptionShowPowerAlertKey: False})
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.1))
        state = states.get(bluetooth.CBManager.authorization(), 'unavailable')
        if state != 'not_determined':
            return state
    # Keep the manager/delegate alive while the system's request is pending.
    del manager, delegate
    return 'timed_out'


if __name__ == '__main__':
    try:
        print(check(request='--request' in sys.argv[1:]), flush=True)
    except (ImportError, AttributeError) as error:
        print(f'Bluetooth permission check unavailable: {error}. Rerun ./install.sh.', file=sys.stderr)
        sys.exit(1)
