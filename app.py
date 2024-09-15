from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///water_game.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)

class Player(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    water_intake = db.Column(db.Integer, default=0)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'))

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    players = db.relationship('Player', backref='room', lazy=True)

@login_manager.user_loader
def load_user(user_id):
    return Player.query.get(int(user_id))

@app.route('/')
@login_required
def home():
    return redirect(url_for('choose_room'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = Player(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('choose_room'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = Player.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('choose_room'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/choose_room', methods=['GET', 'POST'])
@login_required
def choose_room():
    if request.method == 'POST':
        action = request.form['action']
        if action == 'create':
            if current_user.room_id:
                current_user.room_id = None
                db.session.commit()
            room = Room(name=current_user.username + "'s Room")
            db.session.add(room)
            db.session.commit()
            current_user.room_id = room.id
            db.session.commit()
            return redirect(url_for('room', room_id=room.id))
        elif action == 'join':
            return redirect(url_for('join_room'))
    return render_template('choose_room.html')

@app.route('/join_room', methods=['GET', 'POST'])
@login_required
def join_room():
    if request.method == 'POST':
        room_id = request.form['room_id']
        room = Room.query.get(room_id)
        if room:
            current_user.room_id = room.id
            db.session.commit()
            return redirect(url_for('room', room_id=room.id))
    return render_template('join_room.html')

@app.route('/room/<int:room_id>', methods=['GET', 'POST'])
@login_required
def room(room_id):
    room = Room.query.get_or_404(room_id)
    if request.method == 'POST':
        if 'water_amount' in request.form:
            water_amount = int(request.form['water_amount'])
            current_user.water_intake += water_amount
            db.session.commit()
    players = Player.query.filter_by(room_id=room_id).all()
    sorted_players = sorted(players, key=lambda p: p.water_intake, reverse=True)
    
    def format_water_intake(amount):
        liters = amount // 1000
        milliliters = amount % 1000
        if liters > 0:
            return f"{liters} L {milliliters} ml" if milliliters > 0 else f"{liters} L"
        else:
            return f"{milliliters} ml"
    
    formatted_players = [(player.username, format_water_intake(player.water_intake)) for player in sorted_players]
    
    return render_template('room.html', room=room, players=formatted_players)

@app.route('/leave_room', methods=['POST'])
@login_required
def leave_room():
    current_user.room_id = None
    db.session.commit()
    return redirect(url_for('choose_room'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
