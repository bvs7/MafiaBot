
from ..mafiactrl import MController

from ..chatinterface import MChat, MDM, MInterface
from . import GroupMeInterface, GroupMeServer, GroupMeGame

class GroupMeController(MController):

  MGameType = GroupMeGame
  MServerType = GroupMeServer
  minter = GroupMeInterface

  

class TestGroupMeController(MController):

  MChatType = MChat
  MDMType = MDM
  MGameType = GroupMeGame
  MServerType = GroupMeServer

  def __init__(self, lobby_id, MChatType, MDMType):
    super().__init__(lobby_id)
    self.MGameType.MChatType = MChatType
    self.MGameType.MDMType = MDMType

  def run(self):
    server = self.MServerType(self.handle_chat, self.handle_dm)
    server.run(debug=True)