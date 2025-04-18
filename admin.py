from flask import Blueprint, render_template, redirect, request, url_for, flash, session,send_file
from models import db, Ticket, Attendee, Coupon, Admin
from werkzeug.security import generate_password_hash, check_password_hash
from io import StringIO,BytesIO
import csv
from models import db, Ticket, Attendee, Coupon, Admin
admin_bp = Blueprint('admin', __name__, template_folder='templates')

from flask_login import login_required, login_user, logout_user, current_user

# ---------------------------
# Admin Login Route
# ---------------------------
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        admin = Admin.query.filter_by(email=email).first()

        if admin and check_password_hash(admin.password_hash, password):
            login_user(admin)
            return redirect(url_for('admin.dashboard'))
        else:
            flash("Invalid credentials", "danger")

    return render_template('admin/login.html')

# ---------------------------
# Admin Logout Route
# ---------------------------
@admin_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('admin.login'))

# ---------------------------
# Admin Dashboard Route
# ---------------------------
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    tickets = Ticket.query.all()
    return render_template('admin/dashboard.html', tickets=tickets)

# ---------------------------
# Set New Ticket Price and Limit
# ---------------------------
@admin_bp.route('/set_ticket', methods=['POST'])
@login_required
def set_ticket():
    ticket_id = request.form['ticket_id']
    new_price = request.form['price']
    new_limit = request.form['limit']

    ticket = Ticket.query.filter_by(id=ticket_id).first()
    if ticket:
        ticket.price = float(new_price)
        ticket.limit = int(new_limit)
        db.session.commit()
        flash(f"Updated {ticket.type} ticket.", "success")
    else:
        flash("Ticket not found.", "danger")

    return redirect(url_for('admin.dashboard'))

# ---------------------------
# Add Coupon Code
# ---------------------------
@admin_bp.route('/add_coupon', methods=['POST'])
@login_required
def add_coupon():
    code = request.form['code']
    discount = request.form['discount']

    coupon = Coupon(code=code, discount_perc=float(discount))
    db.session.add(coupon)
    db.session.commit()
    flash(f"Coupon {code} added.", "success")
    return redirect(url_for('admin.dashboard'))


# ---------------------------
# Download Attendees Data
# ---------------------------
@admin_bp.route('/download_attendees')
@login_required
def download_attendees():
    attendees = Attendee.query.all()
    output = BytesIO()
    writer = csv.writer(output := BytesIO())

    # Create a CSV string first
    csv_string = StringIO()
    csv_writer = csv.writer(csv_string)
    csv_writer.writerow(['Name', 'Email', 'Phone', 'Ticket Type', 'Paid Amount', 'Coupon Code','ticket_id'])

    for attendee in attendees:
        csv_writer.writerow([
            attendee.name,
            attendee.email,
            attendee.phone,
            attendee.ticket_type,
            attendee.paid_amount,
            attendee.coupon_code_applied,
            attendee.ticket_id
        ])

    # Convert string to bytes and write to BytesIO
    output.write(csv_string.getvalue().encode('utf-8'))
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="attendees_data.csv",
        mimetype="text/csv"
    )