from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import hashlib
import os
import secrets

DATABASE_URL = "sqlite:///./inventario.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    categoria = Column(String, nullable=False)
    marca = Column(String, nullable=True)
    codigo_barras = Column(String, nullable=True, unique=True, index=True)
    precio_venta = Column(Float, nullable=False)
    precio_costo = Column(Float, default=0.0)
    stock = Column(Float, default=0)
    stock_minimo = Column(Float, default=5)
    unidad = Column(String, default="pieza")
    vendido_por_peso = Column(Integer, default=0)
    descuento_pct = Column(Float, default=0.0)
    descuento_desde = Column(DateTime, nullable=True)
    descuento_hasta = Column(DateTime, nullable=True)
    imagen_url = Column(String, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StockSucursal(Base):
    """Stock asignado de cada producto en cada sucursal (tomado del inventario general)."""
    __tablename__ = "stock_sucursal"
    __table_args__ = (UniqueConstraint("producto_id", "sucursal", name="uq_prod_suc"),)

    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, nullable=False, index=True)
    sucursal = Column(String, nullable=False, index=True)
    cantidad = Column(Float, default=0)
    actualizado_en = Column(DateTime, default=datetime.utcnow)


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    usuario = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    rol = Column(String, default="gerente")  # gerente | cajero
    creado_en = Column(DateTime, default=datetime.utcnow)


class Venta(Base):
    __tablename__ = "ventas"

    id = Column(Integer, primary_key=True, index=True)
    total = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    descuento_extra_pct = Column(Float, default=0.0)
    autorizado_por = Column(String, nullable=True)
    operador = Column(String, nullable=True)
    sucursal = Column(String, nullable=True)
    metodo_pago = Column(String, default="efectivo")  # efectivo | tarjeta
    tpv_referencia = Column(String, nullable=True)
    tpv_autorizacion = Column(String, nullable=True)
    tpv_terminal = Column(String, nullable=True)
    detalle_json = Column(String, nullable=False)
    pago_con = Column(Float, nullable=True)
    cambio = Column(Float, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)


class Sucursal(Base):
    __tablename__ = "sucursales"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, unique=True)
    creado_en = Column(DateTime, default=datetime.utcnow)


class Sesion(Base):
    __tablename__ = "sesiones"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    usuario = Column(String, nullable=False)
    rol = Column(String, nullable=False)
    sucursal = Column(String, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)


def hash_password(password: str, salt: str = None):
    if salt is None:
        salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 100_000)
    return dk.hex(), salt


def verificar_password(password: str, password_hash: str, salt: str) -> bool:
    calc, _ = hash_password(password, salt)
    return calc == password_hash


def generar_token() -> str:
    return secrets.token_urlsafe(32)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Usuario).count() == 0:
            h, s = hash_password("admin123")
            db.add(Usuario(usuario="admin", password_hash=h, salt=s, rol="gerente"))
        if db.query(Sucursal).count() == 0:
            db.add(Sucursal(nombre="1"))
        db.commit()
    finally:
        db.close()
