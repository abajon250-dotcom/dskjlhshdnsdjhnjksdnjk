from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Float, Text, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from config import ADMIN_IDS
engine = create_engine('sqlite:///database.db', echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    tg_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    balance = Column(Float, default=0.0)
    referral_balance = Column(Float, default=0.0)
    total_referral_earnings = Column(Float, default=0.0)
    referral_count = Column(Integer, default=0)
    referred_by = Column(Integer, ForeignKey('users.tg_id'), nullable=True)
    purchases = relationship("Purchase", back_populates="user")
    invoices = relationship("Invoice", back_populates="user")
    logs = relationship("Log", back_populates="user")

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    currency = Column(String, default="USDT")
    is_active = Column(Boolean, default=True)
    sessions = relationship("Session", back_populates="product")

class Session(Base):
    __tablename__ = 'sessions'
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    data = Column(Text, nullable=True)
    file_data = Column(LargeBinary, nullable=True)
    filename = Column(String, nullable=True)
    is_file = Column(Boolean, default=False)
    contacts_count = Column(Integer, default=0)
    is_sold = Column(Boolean, default=False)
    product = relationship("Product", back_populates="sessions")

class Invoice(Base):
    __tablename__ = 'invoices'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=True)
    session_id = Column(Integer, ForeignKey('sessions.id'), nullable=True)
    crypto_invoice_id = Column(Integer, unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    status = Column(String, default='active')
    is_deposit = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    user = relationship("User", back_populates="invoices")
    product = relationship("Product")

class Purchase(Base):
    __tablename__ = 'purchases'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    session_id = Column(Integer, ForeignKey('sessions.id'), nullable=False)
    paid_with_balance = Column(Boolean, default=False)
    purchased_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")
    product = relationship("Product")
    session = relationship("Session")

class Log(Base):
    __tablename__ = 'logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    action = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="logs")

class PromoCode(Base):
    __tablename__ = 'promocodes'
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    max_activations = Column(Integer, nullable=False)
    current_activations = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, nullable=False)
    activations = relationship("PromoCodeActivation", back_populates="promo")

class PromoCodeActivation(Base):
    __tablename__ = 'promo_activations'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    promo_id = Column(Integer, ForeignKey('promocodes.id'), nullable=False)
    activated_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")
    promo = relationship("PromoCode", back_populates="activations")

class Backup(Base):
    __tablename__ = 'backups'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    data = Column(Text, nullable=False)
    note = Column(String, nullable=True)

def init_db():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for admin_id in ADMIN_IDS:
            user = db.query(User).filter_by(tg_id=admin_id).first()
            if not user:
                user = User(tg_id=admin_id, is_admin=True, balance=0.0)
                db.add(user)
            else:
                user.is_admin = True
        db.commit()