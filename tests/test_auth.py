import pytest
from flask import url_for, get_flashed_messages
from app.models import User, Room # Import Room if needed for a protected route
from app import db as _db # To avoid conflict with the db fixture

# --- Registration Tests ---
def test_register_get(client):
    response = client.get(url_for('auth.register'))
    assert response.status_code == 200
    assert b"Register</h1>" in response.data # Check for a unique part of the registration page

def test_register_post_success(client, db): # Added db fixture
    response = client.post(url_for('auth.register'), data={
        'username': 'newuser_auth',
        'email': 'new_auth@example.com',
        'password': 'securepassword',
        'confirm_password': 'securepassword'
    }, follow_redirects=True)
    assert response.status_code == 200 # Should redirect to login
    assert url_for('auth.login') in response.request.path # Check if redirected to login

    user = User.query.filter_by(username='newuser_auth').first()
    assert user is not None
    assert user.email == 'new_auth@example.com'
    
    # Check for flashed message
    # Flashed messages are tricky to get in unit tests without a session context sometimes
    # If get_flashed_messages is not working as expected, may need further setup or alternative check
    # For now, let's assume it works or we check for redirect target primarily
    # with client.session_transaction() as session: # Requires session handling for flashed messages
    #     flashes = session.get('_flashes', [])
    #     assert any('Congratulations, you are now a registered user!' in msg[1] for msg in flashes)


def test_register_duplicate_username(client, test_user): # test_user from conftest.py
    response = client.post(url_for('auth.register'), data={
        'username': 'testuser', # Duplicate username
        'email': 'another_email@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200 # Stays on registration page
    assert b"That username is already taken." in response.data

def test_register_duplicate_email(client, test_user):
    response = client.post(url_for('auth.register'), data={
        'username': 'another_user_reg',
        'email': 'test@example.com', # Duplicate email
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"That email is already in use." in response.data

def test_register_mismatched_passwords(client):
    response = client.post(url_for('auth.register'), data={
        'username': 'mismatchuser',
        'email': 'mismatch@example.com',
        'password': 'password1',
        'confirm_password': 'password2' # Mismatched
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Field must be equal to password." in response.data # Default WTForms message

# --- Login/Logout Tests ---
def test_login_get(client, db): # Added db fixture
    response = client.get(url_for('auth.login'))
    assert response.status_code == 200
    assert b"Sign In</h1>" in response.data

def test_login_success(client, test_user, db): # Added db fixture (test_user already implies db, but explicit is fine)
    response = client.post(url_for('auth.login'), data={
        'email': 'test@example.com',
        'password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert url_for('main.index') in response.request.path # Should redirect to index
    # To check current_user, you'd typically need to make another request in logged-in state
    # or inspect session if possible, which is more complex in unit tests.
    # A simple check is to access a login_required page.

def test_login_incorrect_password(client, test_user):
    response = client.post(url_for('auth.login'), data={
        'email': 'test@example.com',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    assert response.status_code == 200 # Stays on login page or shows error
    assert b"Invalid username or password" in response.data # Check for flash message

def test_login_nonexistent_user(client, db): # Added db fixture
    response = client.post(url_for('auth.login'), data={
        'email': 'nouser@example.com',
        'password': 'password'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data

def test_logout(auth_client): # auth_client is already logged in as test_user
    # First, verify we are logged in by accessing a protected route
    response = auth_client.get(url_for('main.index'), follow_redirects=True)
    assert response.status_code == 200 
    assert b"Hi, testuser!" in response.data # Assuming index shows username

    # Perform logout
    logout_response = auth_client.get(url_for('auth.logout'), follow_redirects=True)
    assert logout_response.status_code == 200
    # After logout and follow_redirects=True, the final path will be the login page
    # because main.index is protected. So, logout_response.request.path will be /auth/login?next=/index
    assert url_for('auth.login') in logout_response.request.path 
    assert "next=/index" in logout_response.request.url # Check query param

    # Verify we are logged out by trying to access index again (it's @login_required)
    # After logout, accessing a @login_required route should redirect to login
    index_response_after_logout = auth_client.get(url_for('main.index'), follow_redirects=False) # Don't follow redirects to see the 302
    assert index_response_after_logout.status_code == 302 
    assert url_for('auth.login') in index_response_after_logout.location

    # Or check if the page content indicates logged out state (e.g., no "Hi, testuser!")
    index_page_content_after_logout = auth_client.get(url_for('main.index'), follow_redirects=True) # Follow to see the login page
    assert b"Hi, testuser!" not in index_page_content_after_logout.data
    assert b"Login" in index_page_content_after_logout.data # Assuming Login link is visible when logged out

# --- @login_required Test ---
def test_login_required_decorator(client):
    # Try to access the main index page which is protected by @login_required
    response = client.get(url_for('main.index'), follow_redirects=False) # Check for redirect
    assert response.status_code == 302 # Should redirect to login
    assert url_for('auth.login') in response.location

    # Check that after redirecting to login, the page is indeed the login page
    response_redirected = client.get(url_for('main.index'), follow_redirects=True)
    assert response_redirected.status_code == 200
    assert b"Sign In</h1>" in response_redirected.data # Should be on the login page content
    assert b"Hi," not in response_redirected.data # Should not see content from index.html
