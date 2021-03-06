#!/usr/bin/python3
import logging
from flask import Flask, request
import json

from ..chatinterface import MServer, TestMServer, ACCESS_KW, MCmd

class GroupMeServer(MServer):

  def __init__(self, handle_chat, handle_dm):
    self.handle_chat = handle_chat
    self.handle_dm = handle_dm
    self.app = Flask('mafiabot')
    self.app.debug = True

    self.app.add_url_rule('/', 'chat', self.chat, methods=['POST'])
    self.app.add_url_rule('/dm', 'dm', self.dm, methods=['POST'])

  def chat(self, data=None):
    if not data:
      data = json.loads(request.data.decode('utf-8'))
    print(data)
    text = data['text']
    if text[0:len(ACCESS_KW)] == ACCESS_KW:
      group_id = data['group_id']
      sender_id = data['sender_id']
      command = text.split()[0][len(ACCESS_KW):]
      self.handle_chat(group_id, sender_id, command, text=text, data=data)
    return "ok"

  def dm(self, data=None):
    if not data:
      data = json.loads(request.data.decode('utf-8'))
    print(data)
    text = data['text']
    if text[0:len(ACCESS_KW)] == ACCESS_KW:
      sender_id = data['sender_id']
      command = text.split()[0][len(ACCESS_KW):]
      self.handle_dm(sender_id, command, text=text, data=data)
    return "ok"

  def run(self, **kwargs):
    self.app.run(host="0.0.0.0",port=1121, **kwargs)

