"""Read authorization without creating a Bluetooth manager.

Creating CBCentralManager can trigger an uncatchable TCC abort when the
responsible terminal lacks NSBluetoothAlwaysUsageDescription (e.g. WezTerm).
Do not request consent here or modify the terminal's signed Info.plist.
"""
import sys


def check():
    import CoreBluetooth as bluetooth

    states = {
        bluetooth.CBManagerAuthorizationAllowedAlways: 'allowed',
        bluetooth.CBManagerAuthorizationDenied: 'denied',
        bluetooth.CBManagerAuthorizationRestricted: 'restricted',
        bluetooth.CBManagerAuthorizationNotDetermined: 'not_determined',
    }
    return states.get(bluetooth.CBManager.authorization(), 'unavailable')


if __name__ == '__main__':
    try:
        print(check(), flush=True)
    except (ImportError, AttributeError) as error:
        print(f'Bluetooth permission check unavailable: {error}. Rerun ./install.sh.', file=sys.stderr)
        sys.exit(1)
