import pytest
import sys # Add sys
import os

# Add project root to sys.path to allow imports from 'app'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import create_app, db as _db # Use _db to avoid conflict with fixture
from app.models import User, Message, Room, RoomMember # Import your models
from config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:' # Use in-memory SQLite for tests
    WTF_CSRF_ENABLED = False # Disable CSRF for simpler form testing in unit tests
    SECRET_KEY = 'test-secret-key' # Ensure a secret key for session management

@pytest.fixture(scope='session')
def app():
    """Session-wide test Flask application."""
    # Override FLASK_APP if it's set for dev, to ensure test config is used
    os.environ['FLASK_APP_ENV_FOR_TESTS_ONLY'] = 'testing' # Custom flag to ensure create_app uses TestConfig
    
    # Modify create_app to accept a specific config for testing if it doesn't already
    # Or ensure TestConfig is picked up based on an env variable like FLASK_ENV=testing
    # For now, assuming create_app can be made to use TestConfig.
    # If create_app uses FLASK_ENV, you might need to set that.
    # Let's assume create_app is modified or can detect 'testing'
    
    # A simple way to force test config if create_app isn't easily modifiable:
    # Directly instantiate and configure app for tests
    # from flask import Flask
    # _app = Flask(__name__)
    # _app.config.from_object(TestConfig)
    # _db.init_app(_app)
    # # register blueprints, etc.
    # from app.main import bp as main_bp
    # _app.register_blueprint(main_bp)
    # from app.auth import bp as auth_bp
    # _app.register_blueprint(auth_bp, url_prefix='/auth')
    # return _app
    
    _app = create_app(TestConfig)
    
    # If your create_app doesn't pick up TestConfig correctly, you might need:
    # _app.config.from_object(TestConfig) 
    # And then re-initialize extensions if they were already initialized with a different config.
    # This depends heavily on your create_app structure.

    # Ensure db is initialized with the test app context if create_app doesn't handle it with new config
    # _db.init_app(_app) # This might be redundant if create_app does it.

    yield _app

    # Clean up environment variable if set
    del os.environ['FLASK_APP_ENV_FOR_TESTS_ONLY']


@pytest.fixture(scope='function') # Changed to function for db isolation
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(scope='function') # Changed to function for db isolation
def db(app):
    """Session-wide test database."""
    with app.app_context():
        # Since migrations are out of sync, we use create_all.
        # This will create tables based on current models.
        _db.create_all() 
        
        yield _db

        _db.session.remove() # Clean up session
        _db.drop_all()       # Drop all tables to ensure isolation between tests
        # _db.engine.dispose() # Dispose of engine might be needed for some DBs/setups


# SocketIO Test Client Fixtures
@pytest.fixture(scope='function')
def socketio_client_factory(app): # Depends on the main app fixture
    from app import socketio # Import your socketio instance
    
    def factory():
        # Create a new SocketIO test client for each call
        # This ensures isolation if multiple clients are needed in one test
        client = socketio.test_client(app)
        return client
    
    return factory

@pytest.fixture(scope='function')
def auth_socketio_client(app, db, socketio_client_factory): # Depends on app, db for user creation
    from app.models import User # Local import to avoid issues if User model changes later
    
    # Create and log in a new user for this client
    # Using unique details to avoid clashes if multiple auth_socketio_clients are used in a test
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    username = f'testuser_sio_{unique_id}'
    email = f'test_sio_{unique_id}@example.com'
    password = 'password123'

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    # Simulate login via HTTP to establish session for SocketIO client
    # The regular Flask test client can set up the session
    http_client = app.test_client()
    http_client.post('/auth/login', data={
        'email': email,
        'password': password
    }, follow_redirects=True)

    # Now create the SocketIO client, it should pick up the session
    sio_client = socketio_client_factory()
    
    # It's useful to return the user object too, for sender_id checks etc.
    return sio_client, user


# Fixture to create a test user (existing one, can be used for HTTP tests or simple DB setup)
@pytest.fixture(scope='function')
def test_user(db):
    user = User(username='testuser', email='test@example.com')
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    return user

# Fixture for providing a logged-in client (useful for auth-required tests)
@pytest.fixture(scope='function')
def auth_client(client, test_user):
    # Log in the test_user
    # Note: This assumes your login route is '/auth/login' and uses email for login
    # Adjust if your login uses username or different field names
    client.post('/auth/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    }, follow_redirects=True)
    return client
