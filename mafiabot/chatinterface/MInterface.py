"""
Interface class for interacting with chats and dms or other comms forms
"""

from typing import NewType, Iterable, Mapping, Callable
from abc import ABC

from .MChat import MChat, MDM, CastError
from .TestMChat import TestMChat, TestMDM

DEFAULT_CHAT_NAME = "___"

def make_chat(func):
  def fn(cls, chat_id, *args, **kwargs):
    if not chat_id in cls.chats:
      cls.new(DEFAULT_CHAT_NAME)
    func(cls, chat_id, *args, **kwargs)
  return fn

def check_chat(func):
  def fn(cls, chat_id, *args, **kwargs):
    if not chat_id in cls.chats:
      raise CastError("Chat_id not found: {}".format(chat_id))
    func(cls, chat_id, *args, **kwargs)
  return fn

class MInterface:

  MChatID = NewType("MChatID", str)
  MUserID = NewType("MUserID", str)

  MChatType = MChat
  MDMType = MDM

  valid = False

  @classmethod
  def init(cls):
    if not cls.valid:
      cls.chats = {}
      try:
        cls.dms = cls.MDMType()
      except OSError as e:
        print(e)
      cls.valid = True

  @classmethod
  @check_chat
  def cast(cls, chat_id:MChatID, msg:str):
    return cls.chats[chat_id].cast(msg)

  @classmethod
  def send(cls, user_id:MUserID, msg:str):
    return cls.dms.send(msg, user_id)

  @classmethod
  @check_chat
  def format(cls, chat_id:MChatID, msg:str):
    return cls.chats[chat_id].format(msg)

  @classmethod
  def new(cls, chat_name:str) -> MChatID:
    chat = cls.MChatType(chat_name)
    cls.chats[chat.id] = chat
    return chat.id

  @classmethod
  @make_chat
  def add(cls, chat_id:MChatID, users:Mapping[MUserID,str]):
    cls.chats[chat_id].add(users)

  @classmethod
  @check_chat
  def remove(cls, chat_id:MChatID, user_ids:Iterable[MUserID]):
    cls.chats[chat_id].remove(user_ids)

  @classmethod
  @make_chat
  def refill(cls, chat_id:MChatID, users:Mapping[MUserID,str]):
    cls.chats[chat_id].refill(users)

  @classmethod
  @check_chat
  def destroy(cls, chat_id:MChatID):
    cls.chats[chat_id].destroy()
    del cls.chats[chat_id]

  @classmethod
  @check_chat
  def getName(cls, chat_id:MChatID, user_id:MUserID):
    return cls.chats[chat_id].getName(user_id)

  @classmethod
  @check_chat
  def getAcks(cls, chat_id, msg_id):
    return cls.chats[chat_id].getAcks(msg_id)

class PrintMInterface(MInterface):
  """ Overly Simple Test without ChatType or DMType implementation """
  MChatID = MInterface.MChatID
  MUserID = MInterface.MUserID

  MChatType = None
  MDMType = None

  valid = False

  @classmethod
  def init(cls):
    if not cls.valid:
      print("INIT PrintMInterface")
      cls.valid = True

  @classmethod
  def new(cls, chat_name:str):
    print("NEW", chat_name)
    return chat_name

  @classmethod
  def cast(cls, chat_id:MChatID, msg:str):
    print("CAST", chat_id, msg)

  @classmethod
  def send(cls, user_id:MUserID, msg:str):
    print("SEND", user_id, msg)

  @classmethod
  def format(cls, chat_id:MChatID, msg:str) -> str:
    return "f({}) {}".format(chat_id, msg)

  @classmethod
  def add(cls, chat_id:MChatID, users:Mapping[MUserID,str]):
    print("ADD", chat_id, users)

  @classmethod
  def remove(cls, chat_id:MChatID, user_ids:Iterable[MUserID]):
    print("REMOVE", chat_id, user_ids)

  @classmethod
  def refill(cls, chat_id:MChatID, users:Mapping[MUserID,str]):
    print("REFILL", chat_id, users)

  @classmethod
  def destroy(cls, chat_id:MChatID):
    print("DESTROY", chat_id)


class TestMInterface(MInterface):

  MChatID = MInterface.MChatID
  MUserID = MInterface.MUserID

  MChatType = TestMChat
  MDMType = TestMDM

  test_id = None

  @classmethod
  def init(cls):
    try:
      cls.dms = cls.MDMType(test_id=cls.test_id, user_ids=range(5))
    except OSError as e:
      print(e)
    if not cls.valid:
      cls.chats = {}
      cls.valid = True

  @classmethod
  def new(cls, chat_name:str) -> MChatID: #pylint: disable=undefined-variable
    chat = cls.MChatType(chat_name.split()[0], test_id=cls.test_id)
    cls.chats[chat_name] = chat
    return chat_name

class MCastable(ABC):

  minter = MInterface
  def __init__(self):
    self.main_chat_id = None
    self.mafia_chat_id = None

  def main_cast(self, msg):
    msg = self.minter.format(self.main_chat_id, msg)
    self.minter.cast(self.main_chat_id, msg)
  def mafia_cast(self, msg):
    msg = self.minter.format(self.main_chat_id, msg)
    self.minter.cast(self.mafia_chat_id, msg)
  def dm_send(self, user_id, msg):
    msg = self.minter.format(self.main_chat_id, msg)
    self.minter.send(user_id, msg)