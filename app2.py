from flask import Flask, render_template, redirect, url_for, jsonify, request
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import pymysql

app = Flask(__name__)
app.secret_key = '1075c6329458d592ecef209ba5139fb9'

login_manager = LoginManager()
login_manager.init_app(app)

# MySQL database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'changeme',
    'database': 'cloud_stack',
    'cursorclass': pymysql.cursors.DictCursor  # Use DictCursor for dictionary-like results
}

# Establish a connection to the MySQL database
conn = pymysql.connect(**db_config)
cursor = conn.cursor()

# Create user table if not exists
cursor.execute('''
    CREATE TABLE IF NOT EXISTS user (
        id INTEGER PRIMARY KEY AUTO_INCREMENT,
        username VARCHAR(100) UNIQUE NOT NULL,
        password VARCHAR(100) NOT NULL
    )
''')

# Create cloud credential table if not exists
cursor.execute('''
    CREATE TABLE IF NOT EXISTS cloud_credential (
        id INTEGER PRIMARY KEY AUTO_INCREMENT,
        user_id INTEGER NOT NULL,
        cloud_provider VARCHAR(100) NOT NULL,
        credential_name VARCHAR(100) NOT NULL,
        access_key VARCHAR(100) NOT NULL,
        secret_key VARCHAR(100) NOT NULL,
        FOREIGN KEY (user_id) REFERENCES user (id)
    )
''')

# Check if admin user exists, if not, create it
cursor.execute('SELECT * FROM user WHERE username=%s', ('admin',))
admin_exists = cursor.fetchone()
if not admin_exists:
    cursor.execute('INSERT INTO user (username, password) VALUES (%s, %s)', ('admin', 'admin'))
    conn.commit()

conn.commit()

# Define User class
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    cursor.execute('SELECT * FROM user WHERE id=%s', (user_id,))
    user_data = cursor.fetchone()
    if user_data:
        user = User(user_data['id'], user_data['username'])
        return user
    return None

# Define route to render the initial login page
@app.route('/', methods=['GET'])
def login_prompt():
    return render_template('login.html')

# Define route for login logic
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    cursor.execute('SELECT * FROM user WHERE username=%s AND password=%s', (username, password))
    user_data = cursor.fetchone()
    if user_data:
        user = User(user_data['id'], user_data['username'])
        login_user(user)
        return jsonify({'message': 'Login successful', 'redirect_url': url_for('index'), 'username': current_user.username})
    else:
        return jsonify({'error': 'Invalid username or password', 'redirect_url': url_for('login_prompt')})

# Define route to render the Home page
@app.route('/index')
@login_required
def index():
    return render_template('index.html', user=current_user)

# Define route to render the pages for all cloud providers
@app.route('/provision/<cloud_provider>')
@login_required
def provision(cloud_provider):
    if cloud_provider in ['aws', 'azure', 'gcp']:
        return render_template(f'{cloud_provider}_prov_form.html', user=current_user)
    else:
        return 'Invalid cloud provider', 404

# Define route to render the Config page
@app.route('/config', methods=['GET'])
@login_required
def config():
    if current_user.username == 'admin':
        return render_template('admin_config.html', user=current_user)
    else:
        return render_template('user_config.html', user=current_user)
    
# Define route to render the users page
@app.route('/users')
@login_required
def users():
    if current_user.username == 'admin':
        # Fetch user data from the database
        cursor.execute('SELECT id, username FROM user')
        user_data = cursor.fetchall()
        users = [{'id': row['id'], 'username': row['username']} for row in user_data]
        # Render the user data into an HTML template
        return render_template('users.html', users=users)
    else:
        return jsonify({'error': 'Only admin can view users'})

# Define route to render the form for creating a new user
@app.route('/create_new_user_form', methods=['GET'])
@login_required
def create_new_user_form():
    return render_template('add_user.html', user=current_user)

# Define route to add a new user
@app.route('/add_user', methods=['POST'])
@login_required
def add_user():
    if current_user.username == 'admin':
        username = request.form['username']
        password = request.form['password']
        cursor.execute('INSERT INTO user (username, password) VALUES (%s, %s)', (username, password))
        conn.commit()
        return jsonify({'username': username})
    else:
        return jsonify({'error': 'Only admin can add users'})

# Define route to add cloud credentials
@app.route('/cloud_credentials', methods=['POST'])
@login_required
def add_credentials():
    cloud_provider = request.form['cloud_provider']
    credential_name = request.form['credential_name']
    access_key = request.form['access_key']
    secret_key = request.form['secret_key']
    cursor.execute('INSERT INTO cloud_credential (user_id, cloud_provider, credential_name, access_key, secret_key) VALUES (%s, %s, %s, %s, %s)', (current_user.id, cloud_provider, credential_name, access_key, secret_key))
    conn.commit()
    return jsonify({'message': 'Cloud Credentials added successfully', 'redirect_url': url_for('config')})

# Define route for logout logic
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login_prompt'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
