"""Movie Ratings."""

from jinja2 import StrictUndefined

from flask import (Flask, render_template, redirect, request, flash, session)
from flask_debugtoolbar import DebugToolbarExtension

from model import connect_to_db, db, User, Rating, Movie


app = Flask(__name__)

# Required to use Flask sessions and the debug toolbar
app.secret_key = "ABC"

# Normally, if you use an undefined variable in Jinja2, it fails
# silently. This is horrible. Fix this so that, instead, it raises an
# error.
app.jinja_env.undefined = StrictUndefined


@app.route('/')
def index():
    """Homepage."""

    return render_template('homepage.html')


@app.route('/users')
def user_list():
    """Show list of users"""

    users = User.query.all()
    return render_template('user_list.html', users=users)


@app.route('/users/<user_id>')
def display_user_info(user_id):
    user = User.query.get(user_id)
    ratings = {}
    for rating in user.ratings:
        ratings[rating.movie_id] = {'title': rating.movie.title, 'score': rating.score, 'movie_id': rating.movie.movie_id}

    print ratings
    # users = User.query.options(db.joinedload('user_id')).all()
    # for user in users:
    #     if user. is not None:
    user_info = {'age': user.age, 'zipcode': user.zipcode, 'ratings': ratings}
    return render_template('user_info.html', user_info=user_info, user_id=user_id)


@app.route('/movies')
def movie_list():
    """Show list of movies"""

    movies = Movie.query.order_by('title').all()
    return render_template('movie_list.html', movies=movies)


@app.route('/movies/<movie_id>')
def display_movie_info(movie_id):
    user_id = session.get('user_id')

    if user_id:
        user_rating = Rating.query.filter_by(movie_id=movie_id, user_id=user_id).first()
    else:
        user_rating = None

    movie = Movie.query.get(movie_id)

    ratings = {}
    total_ratings = 0
    score_sum = 0.0
    for rating in movie.ratings:
        ratings[rating.rating_id] = rating.score
        total_ratings += 1
        score_sum += rating.score
    average = '{:.2f}'.format((score_sum/total_ratings))

    prediction = None
    if (not user_rating) and user_id:
        user = User.query.get(user_id)
        if user:
            prediction = user.predict_rating(movie)

    if prediction:
        effective_rating = prediction
    elif user_rating:
        effective_rating = user_rating.score
    else:
        effective_rating = None

    the_eye = (User.query.filter_by(email='the-eye@of-judgment.com').one())
    eye_rating = Rating.query.filter_by(user_id=the_eye.user_id, movie_id=movie.movie_id).first()

    if eye_rating is None:
        eye_rating = the_eye.predict_rating(movie)
    else:
        eye_rating = eye_rating.score

    if eye_rating and effective_rating:
        difference = abs(eye_rating - effective_rating)
    else:
        difference = None

    BERATEMENT_MESSAGES = [
        "I suppose you don't have such bad taste after all.",
        "I regret every decision that I've ever made that has brought me to listen to your opinion.",
        "Words fail me, as your taste in movies has clearly failed you.",
        "That movie is great. For a clown to watch. Idiot.",
        "Words cannot express the awfulness of your taste."
    ]

    if difference is not None:
        beratement = BERATEMENT_MESSAGES[int(difference)]
    else:
        beratement = None

    release = movie.released_at.strftime('%B %d, %Y')
    movie_info = {'title': movie.title, 'url': movie.imdb_url, 'released_at': release, 'movie_id': movie.movie_id}
    print 'prediction', prediction
    return render_template('movie_info.html',
                           movie_info=movie_info,
                           total=total_ratings,
                           average=average,
                           ratings=ratings,
                           prediction=prediction,
                           beratement=beratement)


@app.route('/rate-movie/<movie_id>', methods=['POST'])
def rate_movie(movie_id):
    rating = request.form.get('rating')
    movie_id = movie_id
    user = User.query.filter(User.email == session['email']).first()
    if Rating.query.filter(Rating.user_id == user.user_id, Rating.movie_id == movie_id).first():
        user_rating = Rating.query.filter(Rating.user_id == user.user_id, Rating.movie_id == movie_id).first()
        user_rating.score = rating
        flash('We have updated your review')
    else:
        user_rating = Rating(movie_id=movie_id, user_id=user.user_id, score=rating)
        db.session.add(user_rating)
        flash('We have added your review')
    db.session.commit()

    return redirect('/movies/' + movie_id)


@app.route('/registration-form')
def show_registration_form():
    """Shows registration form"""

    return render_template('registration.html')


@app.route('/register', methods=['POST'])
def register():
    """Adds user to database if not an existing user"""

    email = request.form.get('email')
    password = request.form.get('password')

    if User.query.filter(User.email == email).first():
        flash('Account already exists! Please sign in')
    else:
        user = User(email=email, password=password)

        db.session.add(user)
        db.session.commit()
        flash('User added!')
        session['email'] = email
        user = User.query.filter(User.email == email).first()
        session['user_id'] = user.user_id

    return redirect('/')  # change redirect route


@app.route('/login-form')
def show_login_form():
    """Shows login form"""

    return render_template('login.html')


@app.route('/login')
def login():
    """ Logs in the user, queries the db"""
    email = request.args.get('email')
    password = request.args.get('password')
    u = User.query

    if u.filter(User.email == email).first():
        current_user = u.filter(User.email == email).first()

        if current_user.password == password:
            flash('You have been logged in')
            session['email'] = email
            user = User.query.filter(User.email == email).first()
            session['user_id'] = user.user_id
            return redirect('/')
        else:
            flash('Confirm that you have entered the correct password')
            return redirect('login-form')
    else:
        flash('We couldn\'t find your email in our records - please register for an account')
        return redirect('/registration-form')


@app.route('/logout')
def logout():
    flash('You have logged out!')
    session.pop('email', None)

    return redirect('/')

if __name__ == "__main__":
    # We have to set debug=True here, since it has to be True at the
    # point that we invoke the DebugToolbarExtension
    app.debug = True
    app.jinja_env.auto_reload = app.debug  # make sure templates, etc. are not cached in debug mode

    connect_to_db(app)

    # Use the DebugToolbar
    # DebugToolbarExtension(app)
    # DEBUG_TB_INTERCEPT_REDIRECTS = False

    app.run(port=5000, host='0.0.0.0')
