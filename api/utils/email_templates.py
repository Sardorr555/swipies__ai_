#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

"""
Reusable HTML email templates and registry.
"""

# Invitation email template
INVITE_EMAIL_TMPL = """
Hi {{email}},
{{inviter}} has invited you to join their team (ID: {{tenant_id}}).
Click the link below to complete your registration:
{{invite_url}}
If you did not request this, please ignore this email.
"""

# Password reset code template
RESET_CODE_EMAIL_TMPL = """
Hello,
Your password reset code is: {{ code }}
This code will expire in {{ ttl_min }} minutes.
"""

# Account activation code template
ACTIVATION_CODE_EMAIL_TMPL = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 40px 20px; }
  .card { max-width: 500px; margin: 0 auto; background: #1e293b; border-radius: 16px; padding: 40px; border: 1px solid #334155; text-align: center; }
  .logo { font-size: 24px; font-weight: bold; color: #00beb4; margin-bottom: 24px; }
  .title { font-size: 20px; font-weight: 600; color: #ffffff; margin-bottom: 12px; }
  .text { font-size: 14px; color: #94a3b8; line-height: 1.6; margin-bottom: 24px; }
  .code-box { background: #0f172a; border: 2px dashed #00beb4; border-radius: 12px; padding: 18px; font-size: 32px; font-weight: 800; letter-spacing: 10px; color: #00beb4; margin: 24px 0; }
  .footer { font-size: 12px; color: #64748b; margin-top: 32px; }
</style>
</head>
<body>
  <div class="card">
    <div class="logo">Swipies AI</div>
    <div class="title">Verify Your Email Address</div>
    <div class="text">Hello {{ nickname or email }},<br>Welcome to Swipies AI! Use the 6-digit verification code below to activate your account:</div>
    <div class="code-box">{{ code }}</div>
    <div class="text">This verification code will expire in {{ ttl_min }} minutes.</div>
    <div class="footer">If you did not request this email, you can safely ignore it.</div>
  </div>
</body>
</html>"""

# Template registry
EMAIL_TEMPLATES = {
    "invite": INVITE_EMAIL_TMPL,
    "reset_code": RESET_CODE_EMAIL_TMPL,
    "activation_code": ACTIVATION_CODE_EMAIL_TMPL,
}
