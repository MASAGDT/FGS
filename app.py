import os
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, redirect, url_for, session,
    request, flash, abort
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required,
    current_user, logout_user
)
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv

# Load environment variables from .env (if present)
load_dotenv()

# -------------------------------------------------------------------
# App & Config
# -------------------------------------------------------------------

app = Flask(__name__)

# Core secrets / DB
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///franchise.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Optional: explicit SERVER_NAME for stable external URLs
# You can override via .env:
#   SERVER_NAME=localhost:5000
#   PREFERRED_URL_SCHEME=http
server_name = os.environ.get("SERVER_NAME")
if server_name:
    app.config["SERVER_NAME"] = server_name
    app.config["PREFERRED_URL_SCHEME"] = os.environ.get(
        "PREFERRED_URL_SCHEME", "http"
    )

# PayPal environment: "sandbox" or "live"
PAYPAL_ENV = os.environ.get("PAYPAL_ENV", "sandbox").lower()
if PAYPAL_ENV == "live":
    # Live endpoints
    PAYPAL_AUTHORIZE_URL = "https://www.paypal.com/signin/authorize"
    PAYPAL_TOKEN_URL = "https://api-m.paypal.com/v1/oauth2/token"
    PAYPAL_USERINFO_URL = (
        "https://api-m.paypal.com/v1/identity/oauth2/userinfo?schema=openid"
    )
    PAYPAL_API_BASE = "https://api-m.paypal.com/"
else:
    # Sandbox endpoints
    PAYPAL_AUTHORIZE_URL = "https://www.sandbox.paypal.com/signin/authorize"
    PAYPAL_TOKEN_URL = "https://api-m.sandbox.paypal.com/v1/oauth2/token"
    PAYPAL_USERINFO_URL = (
        "https://api-m.sandbox.paypal.com/v1/identity/oauth2/userinfo?schema=openid"
    )
    PAYPAL_API_BASE = "https://api-m.sandbox.paypal.com/"

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

oauth = OAuth(app)

oauth.register(
    name="paypal",
    client_id=os.environ.get("PAYPAL_CLIENT_ID", "your-sandbox-client-id"),
    client_secret=os.environ.get("PAYPAL_CLIENT_SECRET", "your-sandbox-secret"),
    access_token_url=PAYPAL_TOKEN_URL,
    authorize_url=PAYPAL_AUTHORIZE_URL,
    api_base_url=PAYPAL_API_BASE,
    client_kwargs={
        "scope": "openid profile email",
        "token_endpoint_auth_method": "client_secret_basic",
    },
)

# -------------------------------------------------------------------
# Models
# -------------------------------------------------------------------


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    paypal_id = db.Column(db.String(128), unique=True, index=True)
    email = db.Column(db.String(255), unique=False, index=True)
    name = db.Column(db.String(255))
    is_citizen = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    fu_id = db.Column(db.Integer, db.ForeignKey("franchise_units.id"), nullable=True)
    oath_accepted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    roles = db.relationship(
        "UserRole", back_populates="user", cascade="all, delete-orphan"
    )
    household = db.relationship(
        "Household",
        back_populates="owner",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def has_role(self, role_name: str) -> bool:
        return any(ur.role.name == role_name for ur in self.roles)


class Region(db.Model):
    __tablename__ = "regions"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, index=True)
    name = db.Column(db.String(100), unique=True)
    countries = db.relationship("Country", back_populates="region")

    def __repr__(self):
        return f"<Region {self.code}>"


class Country(db.Model):
    __tablename__ = "countries"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, index=True)  # ISO-like
    name = db.Column(db.String(100), unique=True)
    region_id = db.Column(db.Integer, db.ForeignKey("regions.id"))
    region = db.relationship("Region", back_populates="countries")

    franchise_units = db.relationship("FranchiseUnit", back_populates="country")


class FranchiseUnit(db.Model):
    __tablename__ = "franchise_units"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, index=True)
    name = db.Column(db.String(255))
    country_id = db.Column(db.Integer, db.ForeignKey("countries.id"))
    country = db.relationship("Country", back_populates="franchise_units")

    citizens_count = db.Column(db.Integer, default=0)
    population_count = db.Column(db.Integer, default=0)
    dues_last_month = db.Column(db.Float, default=0.0)
    benefits_last_month = db.Column(db.Float, default=0.0)

    field_office_address = db.Column(
        db.String(255), default="Digital-only (prototype)"
    )

    users = db.relationship("User", backref="franchise_unit")
    households = db.relationship("Household", back_populates="fu")


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    description = db.Column(db.String(255))

    user_roles = db.relationship("UserRole", back_populates="role")


class UserRole(db.Model):
    __tablename__ = "user_roles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"))
    fu_id = db.Column(db.Integer, db.ForeignKey("franchise_units.id"), nullable=True)

    user = db.relationship("User", back_populates="roles")
    role = db.relationship("Role", back_populates="user_roles")
    fu = db.relationship("FranchiseUnit")


class Household(db.Model):
    __tablename__ = "households"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    fu_id = db.Column(db.Integer, db.ForeignKey("franchise_units.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    owner = db.relationship("User", back_populates="household")
    fu = db.relationship("FranchiseUnit", back_populates="households")
    members = db.relationship(
        "HouseholdMember",
        back_populates="household",
        cascade="all, delete-orphan",
    )


class HouseholdMember(db.Model):
    __tablename__ = "household_members"

    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey("households.id"))
    label = db.Column(db.String(50))  # e.g., "Member A"
    is_adult = db.Column(db.Boolean, default=True)
    is_citizen = db.Column(db.Boolean, default=False)
    relationship = db.Column(db.String(100), default="self")
    notes = db.Column(db.String(255))

    household = db.relationship("Household", back_populates="members")


class DuesLog(db.Model):
    __tablename__ = "dues_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    amount = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="dues_entries")


class BenefitLog(db.Model):
    __tablename__ = "benefit_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    amount = db.Column(db.Float)
    category = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="benefit_entries")


# -------------------------------------------------------------------
# Initial Oath Text (simple, prototype)
# -------------------------------------------------------------------

CITIZENSHIP_OATH_TEXT = """
I, a voluntary participant in the Franchise Cooperative Civilization,
affirm that I join freely, without coercion, that I recognize this as a
non-governmental cooperative, and that I will uphold its Constitution,
respect other members, and contribute, as I am able, to the shared goal
to feed, fund, and free humanity.
"""

# -------------------------------------------------------------------
# Login Manager
# -------------------------------------------------------------------


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# -------------------------------------------------------------------
# Role Decorators
# -------------------------------------------------------------------


def require_role(role_name):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapped(*args, **kwargs):
            if not current_user.has_role(role_name) and not current_user.is_admin:
                abort(403)
            return fn(*args, **kwargs)

        return wrapped

    return decorator


def require_admin(fn):
    @wraps(fn)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return fn(*args, **kwargs)

    return wrapped


# -------------------------------------------------------------------
# Helper: seed minimal geography + roles
# -------------------------------------------------------------------


def seed_minimum_data():
    if not Region.query.first():
        # Minimal world stub
        world = Region(code="WORLD", name="World")
        db.session.add(world)

        # Example country / FU using your context
        us = Country(code="US", name="United States", region=world)
        db.session.add(us)

        fu = FranchiseUnit(
            code="US-TX-DEN-01",
            name="Denison River Cluster",
            country=us,
            citizens_count=1,
            population_count=1,
            field_office_address="Digital-Only Prototype",
        )
        db.session.add(fu)

    if not Role.query.first():
        roles = [
            Role(
                name="NC_FU_OFFICER",
                description="Neighborhood Council / FU presiding officer",
            ),
            Role(
                name="TREASURY_STEWARD",
                description="Franchise Unit Treasury Steward",
            ),
            Role(
                name="ASA_LIAISON",
                description="Audit & Safety Authority liaison",
            ),
        ]
        db.session.add_all(roles)

    db.session.commit()


# -------------------------------------------------------------------
# Auth Routes (PayPal)
# -------------------------------------------------------------------


@app.route("/login")
def login():
    redirect_uri = url_for("auth_callback", _external=True)
    return oauth.paypal.authorize_redirect(redirect_uri)


@app.route("/auth/callback")
def auth_callback():
    try:
        token = oauth.paypal.authorize_access_token()
    except Exception:
        app.logger.exception("PayPal auth failed")
        flash("PayPal login failed. Please try again.", "danger")
        return redirect(url_for("index"))

    # Fetch user info
    try:
        resp = oauth.paypal.get(PAYPAL_USERINFO_URL, token=token)
        profile = resp.json()
    except Exception:
        profile = {}

    # Attempt to pull some stable keys
    paypal_id = (
        profile.get("user_id")
        or profile.get("payer_id")
        or profile.get("sub")
        or profile.get("user_id", "unknown")
    )
    email = profile.get("email")
    name = profile.get("name") or profile.get("given_name") or "Unnamed"

    if not paypal_id:
        flash("Could not get PayPal user information.", "danger")
        return redirect(url_for("index"))

    user = User.query.filter_by(paypal_id=paypal_id).first()
    if not user:
        # Attach to default FU for now
        default_fu = FranchiseUnit.query.first()
        user = User(
            paypal_id=paypal_id,
            email=email,
            name=name,
            fu_id=default_fu.id if default_fu else None,
            is_citizen=False,
            is_admin=False,
        )
        db.session.add(user)
        db.session.commit()

    login_user(user)
    flash("Logged in via PayPal.", "success")
    # If user has not accepted oath, redirect there first
    if not user.is_citizen or user.oath_accepted_at is None:
        return redirect(url_for("oath"))

    return redirect(url_for("dashboard"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# -------------------------------------------------------------------
# Public Pages
# -------------------------------------------------------------------


@app.route("/")
def index():
    regions = Region.query.all()
    total_citizens = User.query.filter_by(is_citizen=True).count()
    total_fus = FranchiseUnit.query.count()
    total_dues = db.session.query(
        db.func.coalesce(db.func.sum(DuesLog.amount), 0.0)
    ).scalar()
    total_benefits = db.session.query(
        db.func.coalesce(db.func.sum(BenefitLog.amount), 0.0)
    ).scalar()

    return render_template(
        "index.html",
        regions=regions,
        total_citizens=total_citizens,
        total_fus=total_fus,
        total_dues=total_dues,
        total_benefits=total_benefits,
    )


@app.route("/regions")
def regions():
    regions = Region.query.all()
    return render_template("regions.html", regions=regions)


@app.route("/region/<code>")
def region_view(code):
    region = Region.query.filter_by(code=code).first_or_404()
    return render_template("region.html", region=region)


@app.route("/country/<code>")
def country_view(code):
    country = Country.query.filter_by(code=code).first_or_404()
    return render_template("country.html", country=country)


@app.route("/fu/<code>")
def fu_view(code):
    fu = FranchiseUnit.query.filter_by(code=code).first_or_404()
    citizens_count = User.query.filter_by(fu_id=fu.id, is_citizen=True).count()
    # Placeholder population_count: better would be sum of members, but that requires joins.
    population_count = db.session.query(db.func.count(HouseholdMember.id)).scalar()

    dues_last_month = fu.dues_last_month
    benefits_last_month = fu.benefits_last_month

    return render_template(
        "fu.html",
        fu=fu,
        citizens_count=citizens_count,
        population_count=population_count,
        dues_last_month=dues_last_month,
        benefits_last_month=benefits_last_month,
    )


# -------------------------------------------------------------------
# Citizen Flows
# -------------------------------------------------------------------


@app.route("/oath", methods=["GET", "POST"])
@login_required
def oath():
    if current_user.is_citizen and current_user.oath_accepted_at:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        accepted = request.form.get("accept") == "yes"
        if accepted:
            current_user.is_citizen = True
            current_user.oath_accepted_at = datetime.utcnow()
            # Ensure a household exists
            if not current_user.household:
                default_fu = current_user.franchise_unit or FranchiseUnit.query.first()
                hh = Household(owner=current_user, fu=default_fu)
                member = HouseholdMember(
                    household=hh,
                    label="Member A",
                    is_adult=True,
                    is_citizen=True,
                    relationship="self",
                    notes="Primary account holder",
                )
                db.session.add(hh)
                db.session.add(member)
            db.session.commit()
            flash("Oath accepted. Welcome, citizen.", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("You must accept the oath to become a citizen.", "warning")
    return render_template("oath.html", oath_text=CITIZENSHIP_OATH_TEXT)


@app.route("/dashboard")
@login_required
def dashboard():
    dues_paid = db.session.query(
        db.func.coalesce(db.func.sum(DuesLog.amount), 0.0)
    ).filter_by(user_id=current_user.id).scalar()
    benefits_received = db.session.query(
        db.func.coalesce(db.func.sum(BenefitLog.amount), 0.0)
    ).filter_by(user_id=current_user.id).scalar()

    return render_template(
        "dashboard.html",
        dues_paid=dues_paid,
        benefits_received=benefits_received,
    )


@app.route("/household", methods=["GET", "POST"])
@login_required
def household():
    if not current_user.household:
        default_fu = current_user.franchise_unit or FranchiseUnit.query.first()
        hh = Household(owner=current_user, fu=default_fu)
        db.session.add(hh)
        db.session.commit()

    hh = current_user.household

    if request.method == "POST":
        # Very basic handling: overwrite notes / statuses
        for member in hh.members:
            prefix = f"member_{member.id}_"
            member.is_adult = request.form.get(prefix + "is_adult") == "on"
            member.is_citizen = request.form.get(prefix + "is_citizen") == "on"
            member.relationship = request.form.get(
                prefix + "relationship", member.relationship
            )
            member.notes = request.form.get(prefix + "notes", member.notes)
        db.session.commit()
        flash("Household updated.", "success")
        return redirect(url_for("household"))

    return render_template("household.html", household=hh)


# -------------------------------------------------------------------
# Admin Views
# -------------------------------------------------------------------


@app.route("/admin/users")
@require_admin
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin_users.html", users=users)


@app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
@require_admin
def admin_delete_user(user_id):
    if current_user.id == user_id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("admin_users"))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("User deleted.", "info")
    return redirect(url_for("admin_users"))


# -------------------------------------------------------------------
# CLI / Init
# -------------------------------------------------------------------


@app.cli.command("init-db")
def init_db_command():
    """Initialize the database and seed minimum data."""
    db.create_all()
    seed_minimum_data()

    # Ensure you have at least one admin (firstgit add . user who signs in)
    first_user = User.query.first()
    if first_user and not first_user.is_admin:
        first_user.is_admin = True
        db.session.commit()
        print(f"User {first_user.email or first_user.paypal_id} set as admin.")
    print("Database initialized.")


if __name__ == "__main__":
    with app.app_context():
        db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
        if db_uri.startswith("sqlite:///"):
            db_file = db_uri.replace("sqlite:///", "", 1)
            if not os.path.exists(db_file):
                db.create_all()
                seed_minimum_data()
        else:
            # Non-sqlite: you can keep this or remove it and use migrations later
            db.create_all()
            seed_minimum_data()
    app.run(host="0.0.0.0", port=5000, debug=True)
