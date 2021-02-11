"""
Interface class for interacting with chats and dms or other comms forms
"""

class MInterface:

  valid = False
  chats = []
  dms = None

  @classmethod
  def init(cls):
    cls.chats = []
    cls.dms = None
    cls.valid = True

  @classmethod
  def cast(cls, chat_id, msg):
    pass

  @classmethod
  def send(cls, user_id, msg):
    pass

  @classmethod
  def format(cls, chat_id, msg):
    # return formatted msg using names from chat_id
    pass

  # TODO: create, add, refill, remove, getName, etc?

  