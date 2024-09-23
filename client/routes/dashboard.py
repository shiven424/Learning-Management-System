from flask import Blueprint, render_template, redirect, url_for, session

bp = Blueprint('dashboard', __name__)

@bp.route('/dashboard')
def dashboard():
    if 'token' not in session:
        return redirect(url_for('auth.home'))
    return render_template('dashboard.html', role=session['role'])
