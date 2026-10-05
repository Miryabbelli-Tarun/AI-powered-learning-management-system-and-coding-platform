from django.conf import settings
from django.core.mail import EmailMultiAlternatives


def send_otp_email(email, first_name, otp):

    subject = "TRun Learning Platform - Email Verification"

    text_content = f"""
    Hello {first_name},

    Thank you for registering with TRun Learning Platform.

    Your OTP for email verification is:

    {otp}

    This OTP is valid for 10 minutes.

    If you did not create this account, please ignore this email.

    Regards,
    TRun Learning Platform
    """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Email Verification</title>
    </head>

    <body style="
        margin:0;
        padding:0;
        background:#f4f7fb;
        font-family:Arial, sans-serif;
    ">

        <div style="
            max-width:600px;
            margin:40px auto;
            background:#ffffff;
            border-radius:16px;
            overflow:hidden;
            box-shadow:0 10px 30px rgba(0,0,0,0.08);
        ">

            <div style="
                background:linear-gradient(135deg,#2563eb,#7c3aed);
                padding:30px;
                text-align:center;
                color:white;
            ">

                <h1 style="margin:0;">
                    TRun
                </h1>

                <p style="margin:8px 0 0;">
                    Learning Platform
                </p>

            </div>

            <div style="padding:35px;">

                <h2>
                    Hello {first_name},
                </h2>

                <p>
                    Thank you for registering with
                    <strong>TRun Learning Platform</strong>.
                </p>

                <p>
                    Use the following OTP to verify your email address:
                </p>

                <div style="
                    margin:30px 0;
                    padding:20px;
                    text-align:center;
                    background:#f1f5ff;
                    border-radius:12px;
                ">

                    <span style="
                        font-size:32px;
                        font-weight:bold;
                        letter-spacing:8px;
                        color:#2563eb;
                    ">
                        {otp}
                    </span>

                </div>

                <p>
                    This OTP is valid for
                    <strong>10 minutes</strong>.
                </p>

                <p style="color:#64748b;">
                    If you did not create this account,
                    you can safely ignore this email.
                </p>

            </div>

            <div style="
                padding:20px;
                text-align:center;
                background:#f8fafc;
                color:#64748b;
                font-size:13px;
            ">

                © TRun Learning Platform

            </div>

        </div>

    </body>
    </html>
    """

    email_message = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )

    email_message.attach_alternative(
        html_content,
        "text/html"
    )

    email_message.send(
        fail_silently=False
    )


def send_welcome_email(email, first_name):

    subject = "Welcome to TRun Learning Platform"

    text_content = f"""
    Hello {first_name},

    Welcome to TRun Learning Platform.

    Your account has been successfully created.

    You can now log in and start learning.

    Regards,
    TRun Learning Platform
    """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Welcome</title>
    </head>

    <body style="
        margin:0;
        padding:0;
        background:#f4f7fb;
        font-family:Arial, sans-serif;
    ">

        <div style="
            max-width:600px;
            margin:40px auto;
            background:#ffffff;
            border-radius:16px;
            overflow:hidden;
        ">

            <div style="
                background:linear-gradient(135deg,#2563eb,#7c3aed);
                padding:35px;
                text-align:center;
                color:white;
            ">

                <h1>Welcome to TRun!</h1>

                <p>
                    Your learning journey starts here.
                </p>

            </div>

            <div style="padding:35px;">

                <h2>
                    Hello {first_name},
                </h2>

                <p>
                    Your account has been successfully created.
                </p>

                <p>
                    You can now log in to TRun Learning Platform
                    and start learning, practicing coding,
                    and taking assessments.
                </p>

            </div>

        </div>

    </body>
    </html>
    """

    email_message = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )

    email_message.attach_alternative(
            html_content,
            "text/html"
        )

    email_message.send(
            fail_silently=False
        )