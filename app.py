from flask import Flask, request, jsonify, render_template, redirect,session,url_for
from phonepe.sdk.pg.payments.v2.standard_checkout_client import StandardCheckoutClient
from phonepe.sdk.pg.env import Env
from phonepe.sdk.pg.payments.v2.models.request.standard_checkout_pay_request import StandardCheckoutPayRequest
from uuid import uuid4
import smtplib
import qrcode
import time
import io
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from models import *
import base64
from flask_login import LoginManager
from models import Admin  # Make sure Admin model is imported
from dotenv import load_dotenv
load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tedx.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

init_db(app)
# Initialize LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))
app.secret_key = "' 
# Configure PhonePe SDK
client = StandardCheckoutClient.get_instance(
    client_id=os.getenv("CLIENT_ID"),
    client_secret=os.getenv("CLIENT_SECRET"),
    client_version=1,
    env=Env.PRODUCTION  # Change to Env.PRODUCTION when live
)

# Email config
SENDER_EMAIL = os.getenv("EMAIL")
SENDER_PASSWORD = os.getenv("APP_PASSWORD")
from email.mime.image import MIMEImage

def send_email(subject, RECEIVER_EMAIL, Ticket_id, ticket_type, name, email):
    qr_data = f"Ticket ID: {Ticket_id}\nTicket Type: {ticket_type}"
    qr = qrcode.make(qr_data)
    buffered = io.BytesIO()
    qr.save(buffered, format="PNG")
    buffered.seek(0)

    # Email body with CID reference
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f9f9f9; padding: 20px;">
      <div style="max-width: 600px; margin: auto; background-color: #fff; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1);">
        <h2 style="color: #d10024;">Thank you for registering for TEDxNIELIT Aurangabad 2025!</h2>
        <p><strong>Dear {name},</strong></p>
        <p>We’re excited to welcome you to an inspiring day of ideas worth spreading.</p>
        <p><strong>Event Details:</strong><br>
        📍 Venue: BAMU Auditorium, Chhatrapati Sambhajinagar, Maharashtra<br>
        📅 Date: 04/05/2025</p>

        <h3>Your Ticket Details:</h3>
        <ul>
          <li><strong>Ticket ID:</strong> {Ticket_id}</li>
          <li><strong>Ticket Type:</strong> {ticket_type}</li>
          <li><strong>Email:</strong> {email}</li>
        </ul>

        <p>Scan this QR Code at the entrance:</p>
        <img src="cid:qr_code" style="width: 200px; height: 200px; margin-top: 10px;"/>

        <p style="margin-top: 30px;">With gratitude,<br><strong>Team TEDxNIELIT Aurangabad</strong></p>
      </div>
    </body>
    </html>
    """

    message = MIMEMultipart("related")
    message["From"] = SENDER_EMAIL
    message["To"] = RECEIVER_EMAIL
    message["Subject"] = subject

    msg_alternative = MIMEMultipart("alternative")
    msg_alternative.attach(MIMEText(body, "html"))
    message.attach(msg_alternative)

    # Attach QR code image with CID
    img = MIMEImage(buffered.read(), _subtype="png")
    img.add_header("Content-ID", "<qr_code>")
    img.add_header("Content-Disposition", "inline", filename="qr.png")
    message.attach(img)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, message.as_string())

@app.route('/')
def home():
    return render_template("payment.html")

@app.route('/create-order', methods=['POST'])
def create_order():
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    ticket_type = request.form['ticket_type']
    coupon_code = request.form['coupon_code'].strip()

    ticket = Ticket.query.filter_by(type=ticket_type).first()
    if not ticket or ticket.limit <= 0:
        return "Ticket not available", 400

    amount = ticket.price
    if coupon_code:
        coupon = Coupon.query.filter_by(code=coupon_code).first()
        if coupon:
            amount = amount - (amount * coupon.discount_perc / 100)

    order_id = str(uuid4())

    # Store form data in session
    session['order_data'] = {
        'order_id': order_id,
        'name': name,
        'email': email,
        'phone': phone,
        'ticket_type': ticket_type,
        'coupon_code': coupon_code,
        'amount': int(amount)
    }

    redirect_url = url_for('thankyou', _external=True)
    pay_request = StandardCheckoutPayRequest.build_request(
        merchant_order_id=order_id,
        amount=int(amount * 100),  # Convert to paise
        redirect_url=redirect_url
    )
    pay_response = client.pay(pay_request)
    return redirect(pay_response.redirect_url)

@app.route('/thankyou')
def thankyou():
    order_data = session.get('order_data')
    if not order_data:
        return "Session expired or invalid", 400

    order_id = order_data['order_id']

    # Poll until success/failure or timeout
    timeout = 120  # seconds
    interval = 2
    elapsed = 0
    status = None

    while elapsed < timeout:
        order_status = client.get_order_status(merchant_order_id=order_id)
        status = order_status.state
        if status in ["COMPLETED", "FAILED"]:
            break
        time.sleep(interval)
        elapsed += interval

    if status != "COMPLETED":
        return render_template("payment_failed.html")

    # Generate ticket ID
    ticket_id = str(uuid4())[:8].upper()

    # Save to DB
    attendee = Attendee(
        name=order_data['name'],
        email=order_data['email'],
        phone=order_data['phone'],
        ticket_type=order_data['ticket_type'],
        paid_amount=order_data['amount'],
        coupon_code_applied=order_data['coupon_code'] or '',
        ticket_id=ticket_id
    )
    db.session.add(attendee)

    # Decrease ticket count
    ticket = Ticket.query.filter_by(type=order_data['ticket_type']).first()
    ticket.limit -= 1
    db.session.commit()

    # Send confirmation email with QR
    send_email(
        subject="Your TEDx Ticket Confirmation",
        RECEIVER_EMAIL=attendee.email,
        Ticket_id=ticket_id,
        ticket_type=attendee.ticket_type,
        name=attendee.name,
        email=attendee.email
    )


    return render_template("success.html",attendee=attendee)

# Register the admin blueprint
from admin import admin_bp
app.register_blueprint(admin_bp, url_prefix='/admin')


if __name__ == "__main__":
    app.run(debug=True)
