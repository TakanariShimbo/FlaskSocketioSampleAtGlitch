import os
from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
socketio = SocketIO(app)


class Room:
    def __init__(self, n_user=0, texts=""):
        self._n_user = n_user
        self._texts = texts
    
    def join_user(self):
        self._n_user += 1

    def leave_user(self):
        self._n_user -= 1

    def replace_text(self, texts):
        self._texts = texts

    def n_user(self):
        return self._n_user
    
    def texts(self):
        return self._texts


class User:
    def __init__(self, str_room):
        self._str_room = str_room

    def str_room(self):
        return self._str_room


room_dict = {}
user_dict = {}


"""
ROUTE
* /
* /create
* /enter
* /room/<room_name>
"""


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create', methods=['GET', 'POST'])
def create():
    # GET
    if request.method == 'GET':
        return render_template('create.html', rooms=list(room_dict.keys()))

    # POST
    room_name = request.form['room_name']
    if room_name not in room_dict:
        room_dict[room_name] = Room()
        return redirect(url_for('room', room_name=room_name))
    else:
        return "この部屋名は既に使用されています。", 400
    
@app.route('/enter', methods=['GET', 'POST'])
def enter():
    # GET
    if request.method == 'GET':
        return render_template('enter.html', rooms=list(room_dict.keys()))
    
    # POST
    room_name = request.form['room_name']
    if room_name in room_dict:
        return redirect(url_for('room', room_name=room_name))
    else:
        return "この部屋は存在しません。", 400
    
@app.route('/room/<room_name>')
def room(room_name):
    return render_template('room.html', room_name=room_name)


"""
SOCKET
* join_room
* leave_room
* disconnect
* text_update_request
"""


@socketio.on('join_room')
def on_join_room(data):
    str_room = data['room']
    join_room(str_room)
    _join_room_process(str_room)

@socketio.on('leave_room')
def on_leave_room(data):
    str_room = data['room']
    leave_room(str_room)
    _leave_room_process(str_room)

@socketio.on('disconnect')
def on_disconnect():
    room = user_dict.get(request.sid)
    if room:
        str_room = room.str_room()
        _leave_room_process(str_room)

@socketio.on('text_update_request')
def on_text_update_request(json):
    str_room = json['room']
    new_texts = json["text"]
    
    room = room_dict[str_room]
    room.replace_text( new_texts )
    emit('text_update', {'text': room.texts()}, room=str_room, include_self=False)


def _join_room_process(str_room):
    room = room_dict[str_room]
    room.join_user()

    user_dict[request.sid] = User(str_room)

    emit('count_update', {'user_count': room.n_user()}, room=str_room)
    emit('text_update', {'text': room.texts()}, room=request.sid)

def _leave_room_process(str_room):
    room = room_dict[str_room]
    room.leave_user()
    emit('count_update', {'user_count': room.n_user()}, room=str_room)

    del user_dict[request.sid]

    if room.n_user() == 0:
        del room_dict[str_room]


if __name__ == '__main__':
    socketio.run(app, debug=True)
