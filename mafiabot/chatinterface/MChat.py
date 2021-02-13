from ..resp_lib import get_resp

class CastError(Exception):
  pass

class MChat:
  # TODO: Consider cast_resp, and even prep_resp which will load in a str and wait to cast it until next cast?
  # prep_resp and flush? or does any cast flush?
  def __init__(self, group_id=None):
    print("MChat %s"%group_id, flush=True)
    self.id = group_id
    self.names = {}

  def destroy(self):
    print("DEL",self.id)

  @classmethod
  def new(cls, name): # Just return id?
    return cls(name)

  def getName(self,user_id):
    return "Name of %s"%user_id

  def format(self, msg):
    for id,name in self.names.items():
      msg = msg.replace("[{}]".format(id),name)
    return msg

  def remove(self, user_id):
    del self.names[user_id]
    print("REMOVE", user_id)

  def refill(self, users):
    for id in users:
      self.names[id] = users[id]
    print("REFILL",users)

  def add(self, users):
    for id in users:
      self.names[id] = users[id]
    print("ADD", users)

  def cast(self, msg):
    print("CAST", self.id, msg)
    return "-1"

  def ack(self, message_id):
    print("ACK:", message_id)
  
  def getAcks(self, message_id):
    return []

class MDM:
  # dms are based on another (main chat)
  def __init__(self):
    pass

  # TODO: also take an iterable as msg, then send those in chunks based on max msg size
  def send(self,msg,user_id):
    print("SEND {}: {}".format(user_id, msg), flush=True)



