import time
import datetime
import json

from typing import NewType, Callable, Optional
from ..resp_lib import resp_lib
from .MTimer import MTimer
from ..mafiastate import MState, MPlayer, MRules, MRole, MPlayerID, \
  InvalidActionException, EndGameException, MPhase, dispKnownRoles
from ..chatinterface import MChat, MDM, MCmd

# Starts game, creates chats?
# Sticks around after the game to manage chats?
# route these commands into here:
# vote, target, reveal, timer, untimer
# These ones use context? But are general commands usually
# (status), (help)

# Initialized upon "start" in lobby resolving?
# Can create from saved MState, or made new?
# from save:
#  find chats?
#  recreate MState
#  get lobby still?

TIME_PER_PLAYER = 5*30

class DeleteGameException(Exception):
  pass

def wrap_end(func):
  def f(self, *args, **kwargs):
    try:
      result = func(self, *args,**kwargs)
    except EndGameException as ege:
      return self.__end_game(ege.msg)
    return result
  return f

# Contains MState, checks inputs, fulfills non-event actions
class MGame:

  MChatType = MChat
  MDMType = MDM
  MTimerType = MTimer

  def __init__(self, game_id, main_chat_id=None, mafia_chat_id=None):
    # Search for saved game using game_id. If it already exists, load.
    self.id = game_id
    if main_chat_id == None:
      self.main_chat = self.MChatType.new("MAIN CHAT {}".format(self.id))
    else:
      self.main_chat = self.MChatType(main_chat_id)
    if mafia_chat_id == None:
      self.mafia_chat = self.MChatType.new("MAFIA CHAT {}".format(self.id), self.main_chat)
    else:
      self.mafia_chat = self.MChatType(mafia_chat_id, name_reference=self.main_chat)
    self.dms = self.MDMType(self.main_chat)
    self.mstate = None
    self.timer = None
    self.timered = set()
    self.end_game = self.__end_game
    self.end_timer = None
    self.destroy_callback = self.__destroy_callback
  
  def hook_up(self):
    if self.mstate != None:
      self.mstate.main_chat = self.main_chat
      self.mstate.mafia_chat = self.mafia_chat
      self.mstate.dms = self.dms
      self.mstate.halt_timer = self.halt_timer

  @classmethod
  def new(cls): 
    game_id = 1#getNewGameID()
    g = cls(game_id)
    return g

  def wrap_end(func:Callable): # pylint: disable=no-self-argument
    def f(self, *args, **kwargs):
      try:
        result = func(self, *args,**kwargs) # pylint: disable=not-callable
      except EndGameException as ege:
        return self.__end_game(self.id, ege.msg)
      return result
    return f

  def start(self, users, roleGen, **kwargs):
    """ Inputs, roleGen is a roleGen fn, users is... user ids and nicknames?
    Should we import user nicknames? Yes, eventually have MUser!?? for generality
    """
    self.mstate = MState(self.main_chat, self.mafia_chat, self.dms, **kwargs)
    self.mstate.halt_timer = self.halt_timer
    ids = list(users.keys())
    (assignments, contracts) = roleGen(ids)
    ids = [p_id for p_id,r in assignments]
    roles = [MRole(r) for p_id,r in assignments]
    assignments = list(zip(ids,roles))
    # Should roleGen do a better job of returning things?
    mafia_users = {}
    for p_id, role in assignments:
      if MRole(role).is_mafia():
        mafia_users[p_id] = users[p_id]

    self.main_chat.add(users)
    self.mafia_chat.add(mafia_users)

    try:
      self.mstate.start(assignments, contracts)
    except Exception as e:
      print(e, flush=True)

  def active(self):
    return self.mstate != None and self.mstate.phase.active()

  def end_game_timer_callback(self, ege):
    if isinstance(ege, EndGameException):
      self.__end_game(self.id, ege.msg)
    else:
      raise ege

  def __end_game(self,g_id,msg):
    # Start Destroy timer.
    self.end_timer = self.MTimerType(30*60, {0:[self.destroy]})
    if self.end_game != self.__end_game:
      self.end_game(g_id, msg)
    else:
      raise NotImplementedError
    return True

  # decorator for end of game or invalid action?
  def handle_chat(self, group_id, sender_id:MPlayerID, cmd:MCmd, **kwargs):
    if group_id == self.main_chat.id and cmd.is_main():
      try:
        self.handle_main(sender_id, cmd, **kwargs)
      except Exception as e:
        raise e # TODO handle better?
      return True
    elif group_id == self.mafia_chat.id and cmd.is_mafia():
      try:
        self.handle_mafia(sender_id, cmd, **kwargs)
      except Exception as e:
        raise e # TODO handle better?
      return True

  # A message sent to main chat, decide signature?
  def handle_main(self, sender_id:MPlayerID, cmd:MCmd, **kwargs):
    raise NotImplementedError("Default MGame")

  def handle_mafia(self, sender_id:MPlayerID, cmd:MCmd, **kwargs):
    raise NotImplementedError("Default MGame")

  def handle_dm(self, sender_id, cmd:MCmd, **kwargs):
    raise NotImplementedError("Default MGame")

  @wrap_end
  def handle_vote(self,voter_id,votee_id):
    try:
      self.mstate.vote(voter_id, votee_id)
      return True
    except InvalidActionException as iae:
      self.main_chat.cast(iae.msg)
      return False
  
  @staticmethod
  def getTarget(text):
    words = text.split()
    target_letter = words[1]
    if not len(target_letter) == 1:
      raise TypeError()
    return target_letter

  @wrap_end
  def handle_target(self,actor_id,target_id):
    # Get target handled by subclass
    try:
      # If phase is dusk, assume this is an itarget?
      if self.mstate.phase == MPhase.DUSK:
        self.mstate.itarget(actor_id, target_id)
        return True
      else:
        self.mstate.target(actor_id,target_id)
        return True
    except InvalidActionException as iae:
      self.dms.send(iae.msg, actor_id)
      return False

  @wrap_end
  def handle_mtarget(self, targeter_id, target_id):
    try:
      self.mstate.mtarget(targeter_id, target_id)
      return True
    except InvalidActionException as iae:
      self.mafia_chat.cast(iae.msg)
      return False

  @wrap_end
  def handle_reveal(self, reveal_id):
    try:
      self.mstate.reveal(reveal_id)
      return True
    except InvalidActionException as iae:
      self.dms.send(iae.msg, reveal_id)
      return False
    
  def halt_timer(self):
    if not self.timer == None:
      self.timer.halt()
      self.timer = None
    self.timered = set()

  def set_timer(self, time):
    def make_alarm(msg):
      def alarm():
        self.main_chat.cast(msg)
      return alarm
    timer = self.MTimerType(time,
      {
        0 : [self.mstate.timer],
        60: [make_alarm(resp_lib['TIMER_1MINUTE'])],
        5*60 : [make_alarm(resp_lib['TIMER_5MINUTE'])],
        10*60 : [make_alarm(resp_lib['TIMER_10MINUTE'])],
      }, exception_callback=self.end_game_timer_callback, low_set_lim=TIME_PER_PLAYER)
    return timer

  @wrap_end
  def handle_timer(self, player_id):
    if self.timer == None:
      n_players = len(self.mstate.players)
      time = n_players * TIME_PER_PLAYER
      self.timer = self.set_timer(time)
      time_str = str(self.timer)
      self.main_chat.cast_resp("TIMER_STARTED",time=time_str)
      
    else:
      if player_id in self.timered:
        self.main_chat.cast_resp("ALREADY_TIMERED")
        return True
      self.timer.addTime(-TIME_PER_PLAYER)
      self.main_chat.cast_resp("TIMER_REDUCED",time=str(self.timer))
    self.timered.add(player_id)
    return True
  
  @wrap_end
  def handle_untimer(self, player_id):
    if self.timer == None or not player_id in self.timered:
      self.main_chat.cast_resp("HAVENT_TIMERED")
    elif len(self.timered) == 1:
      self.halt_timer()
      self.main_chat.cast_resp("TIMER_HALTED")
    else: 
      self.timered.remove(player_id)
      self.timer.addTime(TIME_PER_PLAYER)
      self.main_chat.cast_resp("TIMER_EXTENDED", time=str(self.timer))
    return True

  def handle_main_help(self, sender_id, text):
    self.main_chat.cast("Help not implemented yet")

  def handle_mafia_help(self, sender_id, text):
    self.mafia_chat.cast("Help not implemented yet")
    
  def handle_dm_help(self, sender_id, text):
    self.dms.send("Help not implemented yet",sender_id)

  @staticmethod
  def vote_status(votes, players, timered=set(), detailed=False):
    print(votes)
    status_msg = ""
    thresh = len(votes)//2+1
    no_kill_thresh = len(votes) - thresh + 1
    for p_id in players:
      this_votes = [v for v in votes.values() if v==p_id]
      if len(this_votes) == 0:
        continue
      status_msg += "[{}]: {}/{}".format(p_id, len(this_votes),thresh)
      if detailed:
        status_msg += " (" + \
          ", ".join(["[%s]"%o_id for o_id,v in votes.items() if v==p_id]) + ")"
      status_msg += "\n"
    nokill_votes = [(o_id,v) for o_id,v in votes.items() if v==MPlayer.NOTARGET]
    if len(nokill_votes) > 0:
      status_msg += "No kill: {}/{}".format(len(nokill_votes),no_kill_thresh)
      if detailed:
        status_msg += " (" + ", ".join(["[%s]"%o_id for o_id,v in nokill_votes]) + ")"
      status_msg += "\n"
    return status_msg[:-1]

  @staticmethod
  def get_status_reveal(rules):
    known_roles = rules[MRules.known_roles]
    reveal_on_death = rules[MRules.reveal_on_death]
    status_reveal = "OFF"
    if known_roles == "ROLE" and reveal_on_death == "ROLE":
      status_reveal = "ROLE"
    elif known_roles in ["ROLE","MAFIA"] and \
        reveal_on_death in ["ROLE","MAFIA"]:
      status_reveal = "MAFIA"
    elif known_roles in ["ROLE","MAFIA","TEAM"] and \
      reveal_on_death in ["ROLE","MAFIA","TEAM"]:
      status_reveal = "TEAM"
    return status_reveal

  def handle_main_status(self, sender_id, text):
    words = text.split()
    if len(words) > 1:
      context = words[1].lower()
      if "vote" in context:
        votes = dict([(p_id,p.vote) for p_id,p in self.mstate.players.items()])
        self.main_chat.cast(self.vote_status(votes,self.mstate.players,detailed=True))
      elif "player" in context:
        # TODO: Add timer status
        players_str = "\n".join("[%s]"%p_id for p_id in self.mstate.players)
        players_str += "\nTotal: %i"%len(self.mstate.players)
        self.main_chat.cast(players_str)
      elif "role" in context:
        roles = [p.role for p in self.mstate.players.values()]
        status_reveal = self.get_status_reveal(self.mstate.rules)
        role_msg = dispKnownRoles(roles, status_reveal)
        known_roles = self.mstate.rules[MRules.known_roles]
        reveal_on_death = self.mstate.rules[MRules.reveal_on_death]
        start_roles = self.mstate.start_roles
        if not status_reveal == reveal_on_death:
          living_ps = set(self.mstate.players.keys())
          original_ps = set([p_id for p_id,role in start_roles[0]])
          dead_ps = original_ps - living_ps
          dead_roles = [role for p_id,role in start_roles[0] if p_id in dead_ps]
          if len(dead_roles) > 0:
            role_msg += "\nDead Roles: "
            role_msg += dispKnownRoles(dead_roles, reveal_on_death)
        elif not status_reveal == known_roles:
          original_roles = [role for p_id,role in start_roles[0]]
          role_msg += "\nOriginal Roles: "
          role_msg += dispKnownRoles(original_roles, known_roles)
        self.main_chat.cast(role_msg)
      elif "timer" in context:
        if self.timer != None:
          status_msg = "{phase} {day}: ".format(
            phase=self.mstate.phase.__str__(), day=self.mstate.day)
          status_msg += str(self.timer) + "\n"
          status_msg += "Timered: {}".format(", ".join(
            ["[{}]".format(t_id) for t_id in self.timered]))
        else:
          status_msg = "No timer"
        self.main_chat.cast(status_msg)
    else:
      # Standard status
      status_msg = "{phase} {day}: ".format(
        phase=self.mstate.phase.__str__(), day=self.mstate.day)
      if not self.timer == None:
        status_msg += str(self.timer)
      status_msg += "\n"
      votes = dict([(p_id,p.vote) for p_id,p in self.mstate.players.items()])
      status_msg += self.vote_status(votes, self.mstate.players, self.timered)
      roles = [p.role for p in self.mstate.players.values()]
      known_roles = self.mstate.rules[MRules.known_roles]
      reveal_on_death = self.mstate.rules[MRules.reveal_on_death]
      status_msg += "\nRoles: " + dispKnownRoles(roles, self.get_status_reveal(self.mstate.rules))
      self.main_chat.cast(status_msg)
    return True

  def handle_mafia_status(self, sender_id, text):
    msg = self.mstate.mafia_status()
    self.mafia_chat.cast(msg)

  def handle_dm_status(self, sender_id, text):
    msg = self.mstate.dm_status(sender_id)
    self.dms.send(msg,sender_id)

  def handle_rule(self, sender_id, text):
    """ Return the rule for a specific rule or list of rules """
    pass

  def __destroy_callback(self, g_id):
    if self.destroy_callback != self.__destroy_callback:
      self.destroy_callback(g_id)
    else:
      raise NotImplementedError

  # Do some __del__?
  def destroy(self):
    self.mstate.destroy()
    self.main_chat.destroy()
    self.mafia_chat.destroy()
    self.__destroy_callback(self.id)

  def save(self):
    # f = open("game_{}.maf".format(self.id),"w")
    # msave(self,f)
    # f.close()
    pass

  def to_json(self):
    d = {
      "main_chat_id": self.main_chat.id,
      "mafia_chat_id": self.mafia_chat.id,
      "mgame_id": self.id,
      "mstate": self.mstate,
    }
    return d

  @classmethod
  def from_json(cls,d):
    mgame = cls(d["mgame_id"], d["main_chat_id"], d["mafia_chat_id"])
    mgame.mstate = d["mstate"]
    mgame.hook_up()
    return mgame