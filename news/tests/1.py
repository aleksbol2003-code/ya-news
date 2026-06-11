from datetime import datetime
from django.utils import timezone


from django.test import TestCase

class TimezoneTest(TestCase):
    def test_current_time(self):
        print(timezone.now())
        self.assertIsNotNone(timezone.now())

    def test_current_time_1(self):
        print(datetime.now())
        self.assertIsNotNone(datetime.now())


