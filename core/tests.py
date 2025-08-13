from django.test import TestCase

# Create your tests here.
# core/tests.py
from django.test import TestCase
class SmokeTest(TestCase):
    def test_truth(self):
        self.assertTrue(True)
