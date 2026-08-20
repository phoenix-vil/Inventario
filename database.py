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
    tienda = Column(String, nullable=True, index=True)  # submarca (Only Reef, Only Garden...). None = visible en todas
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
    transferencia_referencia = Column(String, nullable=True)
    detalle_json = Column(String, nullable=False)
    pago_con = Column(Float, nullable=True)
    cambio = Column(Float, nullable=True)
    cliente_id = Column(Integer, nullable=True)
    estado = Column(String, default="activa")  # activa | parcial | cancelada | devolucion
    venta_origen_id = Column(Integer, nullable=True)  # si es devolucion, la venta que la origino
    total_devuelto = Column(Float, default=0.0)
    devoluciones_json = Column(String, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)


class Cotizacion(Base):
    __tablename__ = "cotizaciones"

    id = Column(Integer, primary_key=True, index=True)
    cliente_nombre = Column(String, nullable=True)
    cliente_telefono = Column(String, nullable=True)
    subtotal = Column(Float, nullable=False)
    descuento_extra_pct = Column(Float, default=0.0)
    total = Column(Float, nullable=False)
    detalle_json = Column(String, nullable=False)
    operador = Column(String, nullable=True)
    sucursal = Column(String, nullable=True)
    nota = Column(String, nullable=True)
    venta_id = Column(Integer, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)


class Sucursal(Base):
    __tablename__ = "sucursales"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, unique=True)
    tiendas = Column(String, nullable=True)  # nombres de tienda separados por coma que se venden en esta sucursal
    creado_en = Column(DateTime, default=datetime.utcnow)


class Tienda(Base):
    """Submarca (Only Reef, Only Garden...). Distinta de Sucursal: una sucursal
    física puede vender de más de una tienda (ej. Imprenta = Only Reef + Only Garden)."""
    __tablename__ = "tiendas"

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
    tienda = Column(String, nullable=True)  # tienda activa, resuelta desde la sucursal al iniciar sesión
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


class VentaPendiente(Base):
    __tablename__ = "ventas_pendientes"

    id = Column(Integer, primary_key=True, index=True)
    sucursal = Column(String, nullable=True)
    operador = Column(String, nullable=True)
    nota = Column(String, nullable=True)
    carrito_json = Column(String, nullable=False)
    descuento_extra_pct = Column(Float, default=0.0)
    autorizado_por = Column(String, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)


class Gasto(Base):
    __tablename__ = "gastos"

    id = Column(Integer, primary_key=True, index=True)
    concepto = Column(String, nullable=False)
    categoria = Column(String, nullable=False)
    monto = Column(Float, nullable=False)
    metodo_pago = Column(String, default="efectivo")  # efectivo | tarjeta | transferencia
    sucursal = Column(String, nullable=True)
    operador = Column(String, nullable=True)
    nota = Column(String, nullable=True)
    fecha = Column(DateTime, default=datetime.utcnow)
    creado_en = Column(DateTime, default=datetime.utcnow)


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    telefono = Column(String, nullable=True)
    nota = Column(String, nullable=True)
    limite_credito = Column(Float, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)


class PagoCredito(Base):
    __tablename__ = "pagos_credito"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, nullable=False, index=True)
    monto = Column(Float, nullable=False)
    metodo_pago = Column(String, default="efectivo")
    operador = Column(String, nullable=True)
    sucursal = Column(String, nullable=True)
    nota = Column(String, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)


class CorteCaja(Base):
    """Cierre de caja de una sucursal. Cada corte cubre desde el corte anterior
    hasta el momento en que se hace, así que ningún movimiento se cuenta dos
    veces ni se pierde aunque un día no se cierre.

    El cajón arranca con lo que quedó del corte previo (saldo_inicial), menos lo
    que se haya retirado entonces."""

    __tablename__ = "cortes_caja"

    id = Column(Integer, primary_key=True, index=True)
    sucursal = Column(String, nullable=False, index=True)
    operador = Column(String, nullable=True)

    # Periodo que abarca: desde el corte anterior de esta sucursal hasta creado_en
    desde = Column(DateTime, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow, index=True)

    saldo_inicial = Column(Float, default=0.0)      # lo que quedó del corte anterior
    ventas_efectivo = Column(Float, default=0.0)
    abonos_efectivo = Column(Float, default=0.0)
    gastos_efectivo = Column(Float, default=0.0)
    esperado = Column(Float, default=0.0)           # inicial + ventas + abonos - gastos
    contado = Column(Float, default=0.0)            # lo que se contó físicamente
    diferencia = Column(Float, default=0.0)         # contado - esperado
    retirado = Column(Float, default=0.0)           # lo que se saca del cajón al cerrar
    nota = Column(String, nullable=True)


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
        if db.query(Tienda).count() == 0:
            for nombre in ("Only Reef", "Only Garden", "Only Reptile", "Only Pets", "El Zar del LED"):
                db.add(Tienda(nombre=nombre))
        db.commit()
    finally:
        db.close()
