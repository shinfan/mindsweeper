#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os
import cgi
import random
from django.utils import simplejson
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

rooms = []

class Room:
    def __init__(self, id):    
        self.id = id
        self.combo = False
        self.left = 0
        self.cur = 0
        self.board=[]
        self.online = [] 
        self.playing = []
        self.score = []
    def create(self, size = 15):
        self.cur = 0
        self.left = 0
        del self.board[:]
        self.board += [[-1]*size for i in range(size)]
        random.seed()
        del self.playing[:]
        self.playing += self.online
        del self.score[:]
        self.score += [0]*len(self.playing)
        for i in range(size):
            for j in range(size):
                if (random.random() > 0.8) :
                    self.board[i][j] = -2
                    self.left += 1
                else:
                    self.board[i][j]= -1           
    def reset(self):
        self.combo = False
        self.left = 0
        self.cur = 0
        self.board=[]
        self.online = []
        self.playing = []
        self.score = []
    def nextPlayer(self):
        self.cur = (self.cur + 1) % len(self.playing)
    def curPlayer(self):
        return self.playing[self.cur]
    
rooms.append(Room(0))

class MainHandler(webapp.RequestHandler):
    global rooms
    def get(self):
        user = users.get_current_user()
        if user:
            name = user.nickname();
            for r in rooms:
                if name in r.online:
                    return self.redirect("/game?rid=" + str(rooms.index(r)))  
            data = {
               'online': map(lambda c: c.online, rooms),
               'playing': map(lambda c: c.playing, rooms)
            }
            path = os.path.join(os.path.dirname(__file__), 'main.html')
            self.response.out.write(template.render(path, data))
        else :
            self.redirect(users.create_login_url(self.request.uri))    

class NewRoom(webapp.RequestHandler):
    def get(self):
        global rooms        
        user = users.get_current_user()
        if user:
            rid = -1
            for r in rooms:
                if len(r.online) == 0:
                    rid = rooms.index(r)
            if (rid < 0):
                rid = len(rooms)
                rooms.append(Room(rid))
            self.redirect("/game?rid=" + str(rid))                    
        else :
            self.redirect(users.create_login_url(self.request.uri))    
        

class GameHandler(webapp.RequestHandler):
    def get(self):
        global rooms
        user = users.get_current_user()
        if user:
            rid = int(self.request.get('rid'))
            
            r = rooms[rid]
            if not user.nickname() in r.online:
                r.online += [user.nickname()]
            greeting = 'hello! ' + user.nickname()
            data = {
                'name': user.nickname(),
                'board': r.board,
                'greeting': greeting,
                'rid': rid
            }
            if user.nickname() in r.playing:
                data["playing"] = 1
            else:
                data["playing"] = 0
            path = os.path.join(os.path.dirname(__file__), 'index.html')
            self.response.out.write(template.render(path, data))
        else :
            self.redirect(users.create_login_url(self.request.uri))

class UpdateHandler(webapp.RequestHandler):
    global rooms
    def valid(self,board,x,y):
        return x >= 0 and y >= 0 and x < len(board) and y < len(board)
    def flood(self, board, x, y):
        if not self.valid(board, x, y) or board[x][y] != -1:
            return
        count = 0
        for i in range(-1,2):
            for j in range(-1,2):
                if (self.valid(board, x+i, y+j) and (board[i+x][j+y] == -3 or board[i+x][j+y] == -2)):
                    count+=1
        board[x][y] = count
        if count == 0:
            self.flood(board,x-1,y)
            self.flood(board,x,y-1)
            self.flood(board,x+1,y)
            self.flood(board,x,y+1)
            self.flood(board,x+1,y+1)
            self.flood(board,x-1,y+1)
            self.flood(board,x-1,y-1)
            self.flood(board,x+1,y-1)
        return
    def moveHandler(self, r, x, y):
        if not self.valid(r.board,x,y):
            return False;
        if r.board[x][y] == -2:
            r.board[x][y] = -3
            if not r.combo:
                r.score[r.cur]+=1
                r.combo = True
            else:
                r.score[r.cur]+=2
            r.left-=1
            return True
        elif r.board[x][y] != -1:
            return False
        else:
            r.combo = False
            self.flood(r.board,x,y)
            return False

    def post(self):
        global rooms
        rid = int(self.request.get('rid'))
        r = rooms[rid]
        type = self.request.get('type')
        ret = {}
        if type == 'start':
            ret["res"] = True
            r.create()
            ret["cur_player"] = r.curPlayer()           
        if len(r.playing) == 0:
            ret["cur_player"] = "None"
        else:
            ##if r.cur >= len(r.playing) or r.cur < 0:
                ##r.cur = r.cur % len(r.playing)
            if type == 'move' and self.request.get('name') == r.curPlayer():
                x = self.request.get('x')
                y = self.request.get('y')
                ret["res"] = self.moveHandler(r, int(x), int(y))
                if not ret["res"]:
                    r.nextPlayer()
            ret["cur_player"] = r.curPlayer()
                
        
        ret["playing"] = r.playing
        ret["online"] = r.online
        ret["board"] = r.board
        ret["score"] = r.score 
        ret["left"] = r.left     
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(simplejson.dumps(ret))

class LogoutHandler(webapp.RequestHandler):
    def post(self):
        global rooms
        rid = int(self.request.get('rid'))
        r = rooms[rid]
        ret = {}
        ret["url"] = users.create_logout_url("/")
        name = self.request.get('name')
        r.online.remove(name)
        if name in r.playing:
            ret["playing_interrupt"] = True
            r.playing.remove(name)
            r.create()
        if len(r.online) == 0:
            ## all player left, reset the room
            rooms[rid] = Room(rid)
        return self.response.out.write(simplejson.dumps(ret))

        
app = webapp.WSGIApplication([
    ('/', MainHandler), ('/new', NewRoom), ('/game', GameHandler),('/move', UpdateHandler), ('/logout', LogoutHandler)
], debug=True)
