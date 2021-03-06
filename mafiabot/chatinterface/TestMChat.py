from . import MChat, MDM
import re
from collections import deque

class TestMChatError(Exception):
  pass

class TestMChat(MChat):
  """ TestMChat. When these are created, use the group_id, which is unique to
  the name when new() is called, to find a file with expected outputs?

  Use some simple regexp ideas to make the output files more advanved...
  Each line can be a regexp if it is in [].
  Just a * will accept everything until the desired line appears
  Don't do two * in a row!
  """

  def __init__(self, group_id, name_reference=None,test_id=0):
    try:
      fname = "test_data/chat{}_{}_expected.msg".format(test_id, group_id)
      f = open(fname)
    except OSError as e:
      print("Failed to find file {}".format(fname))
      raise e
    
    self.state = "NORMAL"
    self.lines = self.parse(f.readlines())
    super().__init__(group_id,name_reference)
    f.close()

  def check_end(self):
    if len(self.lines) > 0:
      raise TestMChatError("Group {} Not at end: {}".format(self.id, self.lines))

  def parse(self, lines):
    results = deque()
    for line in lines:
      line = line.strip()
      if line[0] == "#" or len(line) == 0:
        continue
      if line[0] == "[" and line[-1] == "]":
        results.append(("regexp",line[1:-1]))
      elif line == "*":
        results.append(("star",line))
      elif line[0] == "{" and line[-1] == "}":
        results.append(("ignore_n",line[1:-1]))
      else:
        results.append(("standard",line))
    return results

  def cast(self,msg):
    # Compare msg to lines.
    msg = self.format(msg)
    msg = msg.replace("\n", ' ')
    self.check(msg)

  def check(self, msg):
    if isinstance(self.state, int):
      print("Matched: {}, {} \n {}".format("ignore_n", self.state, msg))
      self.state -= 1
      if self.state <= 0:
        self.state = "NORMAL"
      return True
    if len(self.lines) == 0:
      raise TestMChatError("msg", "(EoF)")
    t,expected = self.lines.popleft()
    try:
      if t == "standard":
        if not msg == expected:
          raise TestMChatError(msg, t, expected)
        print("Matched: {}, {} \n {}".format(t, expected, msg))
        result = True
      elif t == "regexp":
        exp = re.compile(expected, re.IGNORECASE)
        if exp.fullmatch(msg) == None:
          raise TestMChatError(msg, t, expected)
        print("Matched: {}, {} \n {}".format(t, expected, msg))
        result = True
      elif t == "star":
        self.state = "STAR"
        print("State is now Star")
        result = self.check(msg)
      elif t == "ignore_n":
        self.state = int(expected)
        result = self.check(msg)
    except TestMChatError as e:
      if not self.state == "STAR":
        raise e
      self.lines.appendleft((t,expected))
      print("Matched: {}, {} (next: {}, {}) \n {}".format("star","*", t, expected, msg))
      result = True
    return result

class TestMDM(MDM):
  """Similar to TestMChat, but has a file for each player"""

  def __init__(self, name_reference=None, test_id=0, user_ids=[]):
    self.lines = {}
    self.states = {}
    at_least_one_success = False
    for user_id in user_ids:
      try:
        fname = "test_data/dm{}_{}_expected.msg".format(test_id, user_id)
        with open(fname, 'r') as f:
          at_least_one_success = True
          self.states[user_id] = "NORMAL"
          self.lines[user_id] = self.parse(f.readlines())
      except OSError:
        print("Couldn't find file for id: {}".format(user_id))
        pass
  
    if not at_least_one_success:
      raise OSError("Couldn't find a single dm file!")

    super().__init__(name_reference)

  def check_end(self):
    for user_id in self.lines:
      if len(self.lines[user_id]) > 0:
        raise TestMChatError("user {} Not at end: {}".format(user_id,self.lines[user_id]))

  def parse(self, lines):
    results = deque()
    for line in lines:
      line = line.strip()
      if line[0] == "#" or len(line) == 0:
        continue
      if line[0] == "[" and line[-1] == "]":
        results.append(("regexp",line[1:-1]))
      elif line == "*":
        results.append(("star",line))
      elif line[0] == "{" and line[-1] == "}":
        results.append(("ignore_n",line[1:-1]))
      else:
        results.append(("standard",line))
    return results

  def send(self,msg, user_id):
    # Compare msg to lines.
    msg = self.format(msg)
    msg = msg.replace("\n", ' ')
    if not user_id in self.lines:
      return super().send(msg,user_id)
    self.check(msg, user_id)

  def check(self, msg, user_id):
    if isinstance(self.states[user_id], int):
      print("{} Matched: {}, {} \n {}".format(user_id, "ignore_n", self.states[user_id], msg))
      self.states[user_id] -= 1
      if self.states[user_id] <= 0:
        self.states[user_id] = "NORMAL"
      return True
    if len(self.lines[user_id]) == 0:
      raise TestMChatError("msg", "(EoF)")
    t,expected = self.lines[user_id].popleft()
    try:
      if t == "standard":
        if not msg == expected:
          raise TestMChatError(msg, t, expected)
        print("{} Matched: {}, {} \n {}".format(user_id, t, expected, msg))
        result = True
      elif t == "regexp":
        exp = re.compile(expected, re.IGNORECASE)
        if exp.fullmatch(msg) == None:
          raise TestMChatError(msg, t, expected)
        print("{} Matched: {}, {} \n {}".format(user_id, t, expected, msg))
        result = True
      elif t == "star":
        self.states[user_id] = "STAR"
        print("State is now Star")
        result = self.check(msg, user_id)
      elif t == "ignore_n":
        self.states[user_id] = int(expected)
        result = self.check(msg, user_id)
    except TestMChatError as e:
      if not self.states[user_id] == "STAR":
        raise e
      self.lines[user_id].appendleft((t,expected))
      print("{} Matched: {}, {} (next: {}, {}) \n {}".format(user_id, "star","*", t, expected, msg))
      result = True
    return result