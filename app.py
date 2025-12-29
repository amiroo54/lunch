from flask import Flask, render_template, request, redirect, url_for, session, abort, send_from_directory, flash, jsonify, Response, Blueprint
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from db import *
import os
import sys

app = Flask(__name__)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)
app.secret_key = "ferdowsi"


@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)
# AUTHENTICATION

@app.route("/account/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    
    form = request.form
    try:
        user = User.get_by_name(form["username"])
    except:
        flash("User not found. Please register first.")
        return render_template("login.html", form=form)
    if user.authenticate(form["password"]):
        res = login_user(user)
        if not user.is_active:
            flash("Your account is inactive. Please contact an admin.")
            return render_template("login.html", form=form)
        next_to_load = request.args.get('next')
        return redirect(next_to_load or url_for('index')) # Unsafe for now, will fix in production
    return render_template("login.html", form=form)

    
@app.route("/account/logout", methods=["GET", "POST"])
@login_required
def logout():
    if request.method == "GET":
        return render_template("logout.html")
    logout_user()
    return redirect(url_for("index"))
    

@app.route("/account/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    form = request.form
    name = form["username"].strip()
    display_name = form["displayname"].strip()
    password = form["password"].strip()
    role = "user"  # default role unless admin assigns something else

    # create the user with active = 0 (inactive until approved)
    if User.exists(name):
        flash("This username already exists.")
        return render_template("register.html", form=form)
    
    new_emp = User(name=name, display_name=display_name, role=role, password=password)
    new_emp.save()
    flash("Registration successful. Please wait for admin approval.")
    return redirect(url_for("login"))

@app.route("/account/settings")
@login_required
def account_settings():
    return render_template("settings.html")

@app.route("/account/password", methods=["POST"])
@login_required
def change_password():
    form = request.form
    old_pass, new_pass = form["old_password"], form["new_password1"]
    if current_user.authenticate(old_pass):
        current_user.set_password(new_pass)
        current_user.update()
        return redirect(url_for("index"))
    else:
        flash("Incorrect password")
        return redirect(url_for("account_settings"))
# LANDING PAGE
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/favicon.ico")
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route("/admin/users")
@login_required
def list_users():
    if not "admin" in current_user.role:
        return abort(403)
    users = User.list_all()
    return render_template("users.html", users=users)

@app.route("/admin/activate/<int:user_id>", methods=["POST"])
@login_required
def activate_user(user_id):
    if not "admin" in current_user.role:
        return abort(403)
    try:
        e = User.get_by_id(user_id)
    except:
        flash("User not found")
        return abort(409)
    e.activate()
    flash("User activated successfully.")
    return redirect(url_for("list_users"))

@app.route("/admin/deactivate/<int:user_id>", methods=["POST"])
@login_required
def deactivate_user(user_id):
    if not "admin" in current_user.role:
        return abort(403)
    try:
        e = User.get_by_id(user_id)
    except:
        flash("User not found")
        return abort(409)
    e.deactivate()
    flash("User deactivated successfully.")
    return redirect(url_for("list_users"))

@app.route("/admin/promote/<int:user_id>", methods=["POST"])
@login_required
def promote_user(user_id):
    if not current_user.role == "archadmin":
        return abort(403)
    try: 
        e = User.get_by_id(user_id)
    except:
        flash("User not found")
        return abort("409")
    e.role = "admin"
    e.update()
    return redirect(url_for("list_users"))

@app.route("/admin/reset-password/<int:user_id>", methods=["POST"])
@login_required
def reset_user_password(user_id):
    if not "admin" in current_user.role:
        return abort(403)
    try:
        e = User.get_by_id(user_id)
    except:
        flash("User not found")
        return abort(409)
    
    # Generate a simple default password
    default_password = "password123"
    e.set_password(default_password)
    e.update_password()
    flash(f"Password reset for {e.display_name}. New password: {default_password}")
    return redirect(url_for("list_users"))

@app.route("/admin/settings")
@login_required
def admin_settings():
    if not "admin" in current_user.role:
        return abort(403)
    return render_template("admin_settings.html")

# LUNCH TRACKING
@app.route("/lunch", methods=["GET", "POST"])
@login_required
def lunch():
    import jdatetime
    today = jdatetime.date.today().strftime("%Y-%m-%d")
    
    if request.method == "POST":
        action = request.form.get("action")
        event = LunchEvent.get_or_create_by_date(today)
        
        if action == "toggle_attendance":
            user_id = int(request.form.get("user_id"))
            attendees = event.get_attendees()
            attendee_ids = [a.id for a in attendees]
            if user_id in attendee_ids:
                event.remove_attendee(user_id)
            else:
                event.add_attendee(user_id)
        elif action == "set_payer":
            payer_id = int(request.form.get("payer_id"))
            event.set_payer(payer_id)
        
        return redirect(url_for("lunch"))
    
    # GET request
    event = LunchEvent.get_by_date(today)
    attendees = event.get_attendees() if event else []
    attendee_ids = [a.id for a in attendees]
    
    all_users = User.list_all()
    
    # Calculate next payer
    next_payer = None
    next_payer_user = None
    if attendee_ids:
        next_payer = LunchEvent.get_next_payer(attendee_ids)
        if next_payer:
            next_payer_user = User.get_by_id(next_payer)
    
    # Get user stats for display
    stats = LunchEvent.get_user_stats()
    
    # Recent events
    recent_events = LunchEvent.list_recent(10)
    
    return render_template("lunch.html", 
                           today=today,
                           event=event,
                           attendees=attendees,
                           attendee_ids=attendee_ids,
                           all_users=all_users,
                           next_payer=next_payer,
                           next_payer_user=next_payer_user,
                           stats=stats,
                           recent_events=recent_events)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
