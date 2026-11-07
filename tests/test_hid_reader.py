from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from keeb_assistant.hid_reader import BatteryReader, _parse_report


class HidBatteryTests(unittest.TestCase):
    def test_captured_k2_he_wireless_report(self):
        # K2 HE ANSI on Link-KM 0.1.1, custom telemetry firmware.
        packet = bytes.fromhex('a4 54 93 0f 00 04 00') + bytes(25)
        reading = _parse_report(packet)
        self.assertEqual(reading.percentage, 84)
        self.assertEqual(reading.voltage_mv, 3987)
        self.assertEqual(reading.transport_name, '2.4 GHz')
        self.assertFalse(reading.is_charging)
        self.assertEqual(reading.model_id, 0)  # unspecified, not an allocated K2 id

    def test_captured_k2_he_usb_charging_report(self):
        reading = _parse_report(bytes.fromhex('a4 63 02 10 01 01 00') + bytes(25))
        self.assertEqual(reading.percentage, 99)
        self.assertEqual(reading.voltage_mv, 4098)
        self.assertEqual(reading.transport_name, 'USB')
        self.assertTrue(reading.is_charging)

    def test_legacy_and_numbered_model_reports(self):
        for model in (0, 1, 2):
            packet = bytes([0xa4, 40, 0x74, 0x0e, 0, 4, model]) + bytes(25)
            self.assertEqual(_parse_report(packet).model_id, model)
            self.assertEqual(_parse_report(b'\0' + packet).model_id, model)
        self.assertEqual(_parse_report(bytes.fromhex('a4 28 74 0e 00 04')).model_id, 0)

    def test_invalid_reports(self):
        for packet in (b'', bytes(32), b'\xa4', bytes.fromhex('a4 65 74 0e 00 04')):
            self.assertIsNone(_parse_report(packet))

    def test_pull_has_32_byte_payload_plus_report_id(self):
        reader = BatteryReader(lambda reading: None)
        device = Mock()
        reader._devices = {b'test': device}
        reader._send_pull()
        request = device.write.call_args.args[0]
        self.assertEqual(len(request), 33)
        self.assertEqual(request, b'\0\xa4' + bytes(31))


if __name__ == '__main__':
    unittest.main()
