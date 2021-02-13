import unittest

from collections import deque
from .. import MController, FastMTimer
from ...chatinterface import TestMServer, PrintMInterface

class TestMController(MController):
  
  MServerType = TestMServer
  MTimerType = FastMTimer
  minter = PrintMInterface

class Test_MController(unittest.TestCase):

  def test_simple(self):
    self.mctrl = TestMController(['LOBBY','other'])
    self.mctrl.start(lines = deque(["c /watch LOBBY 1"]))
    self.mctrl.server.active = False
    self.mctrl.server.thread.join()