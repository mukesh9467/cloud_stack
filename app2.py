from flask import Flask, render_template, redirect, url_for, jsonify, request
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import sqlite3

app = Flask(__name__)
app.secret_key = '1075c6329458d592ecef209ba5139fb9'

login_manager = LoginManager()
login_manager.init_app(app)

################# Create database connection #################
conn = sqlite3.connect('config.db', check_same_thread=False)
cursor = conn.cursor()

################# Create user table #################
cursor.execute('''
    CREATE TABLE IF NOT EXISTS user (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
''')

################# Create cloud credential table #################
cursor.execute('''
    CREATE TABLE IF NOT EXISTS cloud_credential (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        cloud_provider TEXT NOT NULL,
        credential_name TEXT NOT NULL,
        access_key TEXT NOT NULL,
        secret_key TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES user (id)
    )
''')

conn.commit()

################# Define User class #################
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    user_data = cursor.execute('SELECT * FROM user WHERE id=?', (user_id,)).fetchone()
    if user_data:
        user = User(user_data[0], user_data[1])  # Assuming user_data[1] contains the username
        return user
    return None

################# Define route to render the initial login page #################
@app.route('/', methods=['GET'])
def login_prompt():
    return render_template('login.html')

################# Define route to render for login page and logic #################
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    # Perform login authentication logic here
    user_data = cursor.execute('SELECT * FROM user WHERE username=? AND password=?', (username, password)).fetchone()
    if user_data:
        user = User(user_data[0], user_data[1])
        login_user(user)
        #return jsonify({'message': 'Login successful', 'redirect_url': url_for('index')})
        return jsonify({'message': 'Login successful', 'redirect_url': url_for('index'), 'username': current_user.username})
    
    # Invalid credentials, return JSON response with error message
    else:
        return jsonify({'error': 'Invalid username or password', 'redirect_url': url_for('login_prompt')})

################# Define route to render the Home page #################

@app.route('/home')
def home():
    return render_template('index.html', user=current_user)

################# Define route to render the Home page #################

@app.route('/about')
def about():
    return render_template('about.html', user=current_user)

################# Define route to render the Index page #################

@app.route('/index')
@login_required
def index():
    return render_template('index.html', user=current_user)

################# Define route to render the pages for all cloud provideers #################

@app.route('/provision/<cloud_provider>')
@login_required
def provision(cloud_provider):
    # Check if the cloud provider is valid (e.g., AWS, Azure, GCP)
    if cloud_provider in ['aws', 'azure', 'gcp']:
        # Render the corresponding provisioning template
        return render_template(f'{cloud_provider}_prov_form.html', user=current_user)
    else:
        # Handle invalid cloud provider
        return 'Invalid cloud provider', 404

##################### Define route to render the Config page #####################

@app.route('/config', methods=['GET'])
@login_required
def config():
    if current_user.username == 'admin':
        return render_template('admin_config.html', user=current_user)
    else:
        return render_template('user_config.html', user=current_user)


@app.route('/users')
@login_required  # Ensure only logged-in users can access this route
def users():
    #Fetch user data from the database
    user_data = cursor.execute('SELECT id, username FROM user').fetchall()
    users = [{'id': row[0], 'username': row[1]} for row in user_data]
    # Render the user data into an HTML template
    return render_template('users.html', users=users)
    
# Define route to render the form for creating a new user
@app.route('/create_new_user_form', methods=['GET'])
@login_required
def create_new_user_form():
    return render_template('add_user.html', user=current_user)

################# User creation logic and API route for admin user ##################

@app.route('/add_user', methods=['POST'])
@login_required
def add_user():
    if current_user.username == 'admin':
        username = request.form['username']
        password = request.form['password']
    try:
        cursor.execute('INSERT INTO user (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
        return jsonify({'username': username})
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'})

################# Cloud credentials add logic and API route for all users #################

@app.route('/cloud_credentials', methods=['POST'])
@login_required
def add_credentials():
    cloud_provider = request.form['cloud_provider']
    credential_name = request.form['credential_name']
    access_key = request.form['access_key']
    secret_key = request.form['secret_key']
    cursor.execute('INSERT INTO cloud_credential (user_id, cloud_provider, credential_name, access_key, secret_key) VALUES (?, ?, ?, ?, ?)', (current_user.id, cloud_provider, credential_name, access_key, secret_key))
    conn.commit()
    return jsonify({'message': 'Cloud Credentials added successfully', 'redirect_url': url_for('config')})

################# Define route for logout logic #################
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login_prompt'))

if __name__ == '__main__':
    app.run(debug=True)
