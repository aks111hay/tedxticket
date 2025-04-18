from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
import os
from flask_login import UserMixin

db = SQLAlchemy()

# ---------------------------
# Ticket Model
# ---------------------------
class Ticket(db.Model):
    __tablename__ = 'tickets'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    limit = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<Ticket {self.type} - ₹{self.price}>"


# ---------------------------
# Attendee Model
# ---------------------------
class Attendee(db.Model):
    __tablename__ = 'attendees'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    ticket_type = db.Column(db.String(20), db.ForeignKey('tickets.type'))
    paid_amount = db.Column(db.Float, nullable=False)
    coupon_code_applied = db.Column(db.String(20), db.ForeignKey('coupons.code'), nullable=True)
    ticket_id = db.Column(db.String(50))
        
    def __repr__(self):
        return f"<Attendee {self.name} - {self.ticket_type}>"


# ---------------------------
# Coupon Model
# ---------------------------
class Coupon(db.Model):
    __tablename__ = 'coupons'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    discount_perc = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"<Coupon {self.code} - {self.discount_perc}%>"


# ---------------------------
# Admin Model
# ---------------------------
class Admin(db.Model, UserMixin):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def __repr__(self):
        return f"<Admin {self.email}>"


# ---------------------------
# Setup Function
# ---------------------------
def init_db(app):
    with app.app_context():
        db.init_app(app)
        db.create_all()

        # Setup default admin
        default_email = "admin@tedxnielitaurangabad.com"
        default_password = "admin123@45"

        if not Admin.query.filter_by(email=default_email).first():
            admin = Admin(
                email=default_email,
                password_hash=generate_password_hash(default_password)
            )
            db.session.add(admin)
            print("[✓] Default Admin Created.")

        # Setup ticket types if not exist
        if not Ticket.query.first():
            tickets = [
                Ticket(type="Diamond", price=1699, limit=50),
                Ticket(type="Golden", price=499, limit=200),
                Ticket(type="Silver", price=299, limit=300),
            ]
            db.session.bulk_save_objects(tickets)
            print("[✓] Default Tickets Added.")

        db.session.commit()
