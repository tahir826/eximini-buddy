from jinja2 import Environment, select_autoescape, PackageLoader
from app.core.config import settings

# You can create email templates with Jinja2
env = Environment(
    loader=PackageLoader("app", "templates"),
    autoescape=select_autoescape(['html', 'xml'])
)

def get_verification_email_template(username: str, verification_link: str):
    template = env.get_template("verification_email.html")
    return template.render(
        username=username,
        verification_link=verification_link,
        support_email=settings.EMAIL_USER
    )

# Note: You would need to create a templates folder with email templates
# This is just a sample for more advanced usage.
