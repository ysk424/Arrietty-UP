import unittest

from arrietty_up.fan import FanController, level_for_speed, parse_response_level


class FakeSocket:
    def __init__(self):
        self.blocking = None
        self.bound = None
        self.sent = []
        self.responses = []
        self.closed = False

    def setblocking(self, value):
        self.blocking = value

    def bind(self, address):
        self.bound = address

    def sendto(self, payload, destination):
        self.sent.append((payload, destination))
        return len(payload)

    def recvfrom(self, _size):
        if not self.responses:
            raise BlockingIOError
        return self.responses.pop(0), ("192.168.4.1", 4210)

    def close(self):
        self.closed = True


class FanTests(unittest.TestCase):
    def test_speed_mapping(self):
        self.assertEqual([level_for_speed(v) for v in (0, 0.5, 0.6, 10, 20, 30, 50)], [0, 0, 1, 2, 4, 6, 6])

    def test_response_parser(self):
        self.assertEqual(parse_response_level("OK LEVEL 4"), 4)
        self.assertEqual(parse_response_level("OK LEVEL 2 TARGET 5"), 2)
        self.assertEqual(parse_response_level("OK SYNC 3"), 3)
        self.assertIsNone(parse_response_level("ERR unknown"))
        self.assertIsNone(parse_response_level("OK LEVEL 7"))

    def test_nonblocking_udp_lifecycle_and_response(self):
        fake = FakeSocket()
        fan = FanController(lambda *_args: fake)
        self.assertTrue(fan.start())
        self.assertFalse(fake.blocking)
        self.assertEqual(fake.bound, ("0.0.0.0", 0))

        fan.tick(10.0, 100.0)
        self.assertEqual(fake.sent[-1][0], b"LEVEL 2")
        fake.responses.append(b"OK LEVEL 2 TARGET 2")
        fan.tick(10.0, 100.1)
        self.assertEqual(fan.reported_level, 2)
        self.assertEqual(fan.status, "CONNECTED LEVEL 2")

        fan.correct_reported_level(1)
        self.assertEqual(fake.sent[-1][0], b"SYNC 3")
        self.assertEqual(fan.reported_level, 3)
        fan.stop()
        self.assertEqual(fake.sent[-1][0], b"LEVEL 0")
        self.assertTrue(fake.closed)
        self.assertEqual(fan.status, "STOPPED")

    def test_no_response_warning_and_resend(self):
        fake = FakeSocket()
        fan = FanController(lambda *_args: fake)
        fan.start()
        fan.tick(0.0, 10.0)
        self.assertEqual(len(fake.sent), 1)
        fan.tick(0.0, 11.0)
        self.assertEqual(len(fake.sent), 1)
        fan.tick(0.0, 12.0)
        self.assertEqual(len(fake.sent), 2)
        fan.tick(0.0, 22.0)
        self.assertEqual(fan.status, "NO RESPONSE - CONNECT WI-FI Arrietty-Fan")


if __name__ == "__main__":
    unittest.main()
