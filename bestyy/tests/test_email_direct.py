#!/usr/bin/env python
"""
Direct email test script to bypass Django settings caching
"""
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_email_ssl():
    """Test email using SSL (port 465)"""
    try:
        smtp_server = "smtp.gmail.com"
        port = 465
        sender_email = os.getenv('EMAIL_HOST_USER', 'Bestieai535@gmail.com')
        password = os.getenv('EMAIL_HOST_PASSWORD', 'vttg bqrp sovf ccef')
        receiver_email = "chukwuagoziesolomon@gmail.com"

        print(f"Testing SSL connection to {smtp_server}:{port}")
        print(f"From: {sender_email}")
        print(f"To: {receiver_email}")

        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = "[Bestyy] Direct SSL Email Test"
        message["From"] = sender_email
        message["To"] = receiver_email

        # HTML content
        html = """
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #f8f9fa; padding: 20px; text-align: center;">
                <h1 style="color: #333; margin: 0;">Bestyy Direct Email Test</h1>
                <p style="color: #666; margin: 10px 0;">SSL Connection Test (Port 465)</p>
            </div>
            <div style="padding: 20px;">
                <h2 style="color: #333;">Hello!</h2>
                <p>This email was sent using direct SSL connection to Gmail SMTP.</p>
                <p>If you received this, the email configuration is working correctly!</p>
                <div style="background-color: #e9ecef; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <strong>Test Details:</strong><br>
                    • SMTP Host: smtp.gmail.com<br>
                    • Port: 465 (SSL)<br>
                    • From Email: """ + sender_email + """<br>
                </div>
                <p>Best regards,<br><strong>Bestyy Team</strong></p>
            </div>
        </body>
        </html>
        """

        # Create plain text version
        text = """
        Bestyy Direct Email Test - SSL Connection Test (Port 465)

        Hello!

        This email was sent using direct SSL connection to Gmail SMTP.

        If you received this, the email configuration is working correctly!

        Test Details:
        • SMTP Host: smtp.gmail.com
        • Port: 465 (SSL)
        • From Email: """ + sender_email + """

        Best regards,
        Bestyy Team
        """

        # Attach parts
        message.attach(MIMEText(text, "plain"))
        message.attach(MIMEText(html, "html"))

        # Create SSL context
        context = ssl.create_default_context()

        # Send email
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())

        print("Email sent successfully via SSL!")
        return True

    except Exception as e:
        print(f"SSL Email failed: {str(e)}")
        return False

def test_email_tls():
    """Test email using TLS (port 587)"""
    try:
        smtp_server = "smtp.gmail.com"
        port = 587
        sender_email = os.getenv('EMAIL_HOST_USER', 'Bestieai535@gmail.com')
        password = os.getenv('EMAIL_HOST_PASSWORD', 'vttg bqrp sovf ccef')
        receiver_email = "chukwuagoziesolomon@gmail.com"

        print(f"\nTesting TLS connection to {smtp_server}:{port}")

        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = "[Bestyy] Direct TLS Email Test"
        message["From"] = sender_email
        message["To"] = receiver_email

        html = """
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #f8f9fa; padding: 20px; text-align: center;">
                <h1 style="color: #333; margin: 0;">Bestyy Direct Email Test</h1>
                <p style="color: #666; margin: 10px 0;">TLS Connection Test (Port 587)</p>
            </div>
            <div style="padding: 20px;">
                <h2 style="color: #333;">Hello!</h2>
                <p>This email was sent using direct TLS connection to Gmail SMTP.</p>
                <p>If you received this, TLS connection works!</p>
                <div style="background-color: #e9ecef; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <strong>Test Details:</strong><br>
                    • SMTP Host: smtp.gmail.com<br>
                    • Port: 587 (TLS)<br>
                    • From Email: """ + sender_email + """<br>
                </div>
                <p>Best regards,<br><strong>Bestyy Team</strong></p>
            </div>
        </body>
        </html>
        """

        text = """
        Bestyy Direct Email Test - TLS Connection Test (Port 587)

        Hello!

        This email was sent using direct TLS connection to Gmail SMTP.

        If you received this, TLS connection works!

        Test Details:
        • SMTP Host: smtp.gmail.com
        • Port: 587 (TLS)
        • From Email: """ + sender_email + """

        Best regards,
        Bestyy Team
        """

        message.attach(MIMEText(text, "plain"))
        message.attach(MIMEText(html, "html"))

        # Send email
        with smtplib.SMTP(smtp_server, port) as server:
            server.ehlo()
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())

        print("Email sent successfully via TLS!")
        return True

    except Exception as e:
        print(f"TLS Email failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing Gmail SMTP connections...")
    print("=" * 50)

    # Test SSL first (port 465)
    ssl_success = test_email_ssl()

    # Test TLS (port 587)
    tls_success = test_email_tls()

    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"SSL (Port 465): {'SUCCESS' if ssl_success else 'FAILED'}")
    print(f"TLS (Port 587): {'SUCCESS' if tls_success else 'FAILED'}")

    if ssl_success or tls_success:
        print("\nEmail configuration is working!")
        print("Check your inbox for the test emails.")
    else:
        print("\nBoth SSL and TLS connections failed.")
        print("Check your Gmail settings and app password.")