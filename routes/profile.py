from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
import os
import uuid
from werkzeug.utils import secure_filename
from database.db import get_db

profile_bp = Blueprint('profile', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
HOBBY_CHOICES = [
    'Gym & Fitness', 'Painting & Art', 'Guitar & Music', 'Cooking', 'Hiking',
    'Photography', 'Reading', 'Travel', 'Dancing', 'Yoga', 'Gaming',
    'Cycling', 'Swimming', 'Writing', 'Gardening', 'Surfing', 'Climbing',
    'Pottery', 'Film & Cinema', 'Volunteering'
]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

def save_file(file):
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return filename
    return None

@profile_bp.route('/profile/build', methods=['GET', 'POST'])
@login_required
def build_profile():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    step = request.args.get('step', '1')
    
    if request.method == 'POST':
        step = request.form.get('step', '1')
        
        if step == '1':
            # Basic info
            full_name = request.form.get('full_name', '').strip()
            age = request.form.get('age', '').strip()
            gender = request.form.get('gender', '')
            interested_in = request.form.get('interested_in', '')
            bio = request.form.get('bio', '').strip()
            
            if not all([full_name, age, gender, interested_in, bio]):
                flash('Please fill in all fields.', 'error')
                return render_template('profile_build.html', step='1', user=user, hobbies=HOBBY_CHOICES)
            
            # Handle profile image
            profile_image = None
            if 'profile_image' in request.files:
                profile_image = save_file(request.files['profile_image'])
            
            db.execute('''UPDATE users SET full_name=?, age=?, gender=?, interested_in=?, bio=?, 
                         profile_image=COALESCE(?, profile_image) WHERE id=?''',
                      (full_name, int(age), gender, interested_in, bio, profile_image, session['user_id']))
            db.commit()
            return redirect(url_for('profile.build_profile', step='2'))
        
        elif step == '2':
            # Personality
            music_taste = request.form.get('music_taste', '')
            movie_taste = request.form.get('movie_taste', '')
            favorite_artists = request.form.get('favorite_artists', '')
            favorite_movies = request.form.get('favorite_movies', '')
            
            db.execute('''UPDATE users SET music_taste=?, movie_taste=?, favorite_artists=?, favorite_movies=?
                         WHERE id=?''',
                      (music_taste, movie_taste, favorite_artists, favorite_movies, session['user_id']))
            db.commit()
            return redirect(url_for('profile.build_profile', step='3'))
        
        elif step == '3':
            # Hobbies
            selected_hobbies = request.form.getlist('hobbies')
            
            if len(selected_hobbies) < 2:
                flash('Please select at least 2 hobbies.', 'error')
                return render_template('profile_build.html', step='3', user=user, hobbies=HOBBY_CHOICES)
            
            # Clear old hobbies
            db.execute('DELETE FROM hobbies WHERE user_id = ?', (session['user_id'],))
            
            for hobby in selected_hobbies:
                db.execute('INSERT INTO hobbies (user_id, hobby_name) VALUES (?, ?)',
                          (session['user_id'], hobby))
            db.commit()
            
            return redirect(url_for('profile.build_profile', step='4'))
        
        elif step == '4':
            # Hobby images
            db_hobbies = db.execute('SELECT * FROM hobbies WHERE user_id = ?', (session['user_id'],)).fetchall()
            
            all_uploaded = True
            for hobby in db_hobbies:
                file_key = f"hobby_image_{hobby['id']}"
                existing = db.execute('SELECT id FROM hobby_images WHERE hobby_id = ?', (hobby['id'],)).fetchone()
                
                if file_key in request.files and request.files[file_key].filename:
                    filename = save_file(request.files[file_key])
                    if filename:
                        # Delete old image for this hobby
                        old = db.execute('SELECT image_path FROM hobby_images WHERE hobby_id = ?', (hobby['id'],)).fetchone()
                        if old:
                            db.execute('DELETE FROM hobby_images WHERE hobby_id = ?', (hobby['id'],))
                        db.execute('INSERT INTO hobby_images (user_id, hobby_id, image_path) VALUES (?, ?, ?)',
                                  (session['user_id'], hobby['id'], filename))
                elif not existing:
                    all_uploaded = False
            
            db.commit()
            
            if not all_uploaded:
                flash('Please upload at least one image for each hobby.', 'error')
                hobbies_with_images = []
                for h in db_hobbies:
                    img = db.execute('SELECT * FROM hobby_images WHERE hobby_id = ?', (h['id'],)).fetchone()
                    hobbies_with_images.append({'hobby': h, 'image': img})
                return render_template('profile_build.html', step='4', user=user, 
                                      hobbies_with_images=hobbies_with_images)
            
            # Mark profile complete
            db.execute('UPDATE users SET is_profile_complete = 1 WHERE id = ?', (session['user_id'],))
            db.commit()
            
            flash('Your profile is ready! Start exploring.', 'success')
            return redirect(url_for('discover.discover'))
    
    # GET - render appropriate step
    hobbies_with_images = []
    if step == '4':
        db_hobbies = db.execute('SELECT * FROM hobbies WHERE user_id = ?', (session['user_id'],)).fetchall()
        for h in db_hobbies:
            img = db.execute('SELECT * FROM hobby_images WHERE hobby_id = ?', (h['id'],)).fetchone()
            hobbies_with_images.append({'hobby': h, 'image': img})
    
    return render_template('profile_build.html', step=step, user=user, 
                          hobbies=HOBBY_CHOICES, hobbies_with_images=hobbies_with_images)


@profile_bp.route('/profile/<int:user_id>')
@login_required
def view_profile(user_id):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ? AND is_active = 1', (user_id,)).fetchone()
    
    if not user:
        flash('Profile not found.', 'error')
        return redirect(url_for('discover.discover'))
    
    hobbies = db.execute('SELECT * FROM hobbies WHERE user_id = ?', (user_id,)).fetchall()
    hobby_images = db.execute('SELECT hi.*, h.hobby_name FROM hobby_images hi JOIN hobbies h ON hi.hobby_id = h.id WHERE hi.user_id = ?', (user_id,)).fetchall()
    
    # Check if current user liked this profile
    liked = db.execute('SELECT id FROM likes WHERE liker_id = ? AND liked_id = ?',
                      (session['user_id'], user_id)).fetchone()
    
    # Check if matched
    matched = db.execute('''SELECT id FROM matches WHERE 
        (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)''',
        (session['user_id'], user_id, user_id, session['user_id'])).fetchone()
    
    # Get remaining likes for today
    current_user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    from datetime import date
    today = str(date.today())
    likes_today = current_user['likes_given_today'] if current_user['likes_reset_date'] == today else 0
    remaining_likes = max(0, 20 - likes_today)
    
    return render_template('profile_view.html', 
                          profile_user=user, 
                          hobbies=hobbies,
                          hobby_images=hobby_images,
                          liked=liked,
                          matched=matched,
                          remaining_likes=remaining_likes)


@profile_bp.route('/profile/me')
@login_required
def my_profile():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    hobbies = db.execute('SELECT * FROM hobbies WHERE user_id = ?', (session['user_id'],)).fetchall()
    hobby_images = db.execute('SELECT hi.*, h.hobby_name FROM hobby_images hi JOIN hobbies h ON hi.hobby_id = h.id WHERE hi.user_id = ?', (session['user_id'],)).fetchall()
    
    return render_template('profile_view.html', 
                          profile_user=user, 
                          hobbies=hobbies,
                          hobby_images=hobby_images,
                          is_own=True)


@profile_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        bio = request.form.get('bio', '').strip()
        music_taste = request.form.get('music_taste', '')
        movie_taste = request.form.get('movie_taste', '')
        favorite_artists = request.form.get('favorite_artists', '')
        favorite_movies = request.form.get('favorite_movies', '')
        
        profile_image = None
        if 'profile_image' in request.files and request.files['profile_image'].filename:
            profile_image = save_file(request.files['profile_image'])
        
        db.execute('''UPDATE users SET bio=?, music_taste=?, movie_taste=?, 
                     favorite_artists=?, favorite_movies=?,
                     profile_image=COALESCE(?, profile_image) WHERE id=?''',
                  (bio, music_taste, movie_taste, favorite_artists, favorite_movies, 
                   profile_image, session['user_id']))
        db.commit()
        flash('Profile updated!', 'success')
        return redirect(url_for('profile.my_profile'))
    
    return render_template('profile_edit.html', user=user)
