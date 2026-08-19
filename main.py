from fastapi import FastAPI, Depends, HTTPException, Query, Header, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import os
import json
import hashlib

from database import (get_db, init_db, Producto, Usuario, Venta, Sesion, Sucursal, StockSucursal,
                      verificar_password, hash_password, generar_token)
from database import Cliente, PagoCredito
from database import Gasto
from database import VentaPendiente
from database import Cotizacion
from database import Tienda
from schemas import (
    ProductoCreate, ProductoUpdate, ProductoOut, AjusteStock,
    AutorizarDescuento, RegistrarVenta, CrearUsuario, CambiarPassword,
    Login, LogoutReq, CrearSucursal, DescuentoCategoria, AsignarStockSucursal, TrasladoStock)
from schemas import CrearTienda, ClasificarProductosMasivo, EditarSucursal
from schemas import CrearCliente, CrearPagoCredito
from schemas import CrearGasto
from schemas import CrearVentaPendiente
from schemas import RegistrarCotizacion

app = FastAPI(title="Inventario", version="1.0.0")

init_db()

# Servir archivos estáticos (la app web)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


# ─── Autenticación por sesión ──────────────────────────────────────────────
def get_sesion(authorization: Optional[str], db: Session) -> Optional[Sesion]:
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        return None
    s = db.query(Sesion).filter(Sesion.token == token).first()
    if not s:
        return None
    if datetime.utcnow() - s.creado_en > timedelta(hours=8):
        db.delete(s)
        db.commit()
        return None
    return s


def requerir_sesion(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> Sesion:
    s = get_sesion(authorization, db)
    if not s:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    return s


def requerir_gerente(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> Sesion:
    s = get_sesion(authorization, db)
    if not s:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    if s.rol != "gerente":
        raise HTTPException(status_code=403, detail="Acción permitida solo para gerentes")
    return s


def requerir_enterprise(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> Sesion:
    """Gerente con una sesión sin tienda asignada, es decir Only Enterprises.
    Para lo que gobierna la empresa entera y no una sola sucursal: dar de alta
    sucursales, clasificar productos por tienda y comparar el inventario de
    todas las sucursales."""
    s = get_sesion(authorization, db)
    if not s:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    if s.rol != "gerente":
        raise HTTPException(status_code=403, detail="Acción permitida solo para gerentes")
    if s.tienda:
        raise HTTPException(status_code=403, detail="Disponible solo desde Only Enterprises")
    return s


def sesion_opcional(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> Optional[Sesion]:
    """Igual que requerir_sesion pero sin exigir sesión válida: None si no hay token o es inválido."""
    return get_sesion(authorization, db)


@app.post("/api/login")
def login(data: Login, db: Session = Depends(get_db)):
    u = db.query(Usuario).filter(Usuario.usuario == data.usuario).first()
    if not u or not verificar_password(data.password, u.password_hash, u.salt):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    # La(s) tienda(s) activa(s) de la sesión son las de la sucursal elegida, todas a la
    # vez (ej. Imprenta = Only Reef + Only Garden simultáneo, no hay que elegir una).
    tienda_texto = None
    if data.sucursal:
        suc = db.query(Sucursal).filter(Sucursal.nombre == data.sucursal).first()
        tienda_texto = suc.tiendas if suc else None

    token = generar_token()
    db.add(Sesion(token=token, usuario=u.usuario, rol=u.rol, sucursal=data.sucursal, tienda=tienda_texto))
    db.commit()
    return {"token": token, "usuario": u.usuario, "rol": u.rol, "sucursal": data.sucursal, "tienda": texto_a_tiendas(tienda_texto)}


@app.post("/api/logout")
def logout(data: LogoutReq, db: Session = Depends(get_db)):
    s = db.query(Sesion).filter(Sesion.token == data.token).first()
    if s:
        db.delete(s)
        db.commit()
    return {"ok": True}


@app.get("/api/sesion")
def info_sesion(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    s = get_sesion(authorization, db)
    if not s:
        raise HTTPException(status_code=401, detail="Sin sesión")
    return {"usuario": s.usuario, "rol": s.rol, "sucursal": s.sucursal, "tienda": texto_a_tiendas(s.tienda)}


# ─── Sucursales ─────────────────────────────────────────────────────────────
def tiendas_a_texto(lista: Optional[List[str]]) -> Optional[str]:
    """[ "Only Reef", "Only Garden" ] -> "Only Reef,Only Garden". Vacío/None -> None."""
    if not lista:
        return None
    limpio = [t.strip() for t in lista if t and t.strip()]
    return ",".join(limpio) if limpio else None


def texto_a_tiendas(texto: Optional[str]) -> List[str]:
    return [t for t in (texto or "").split(",") if t]


def validar_tiendas(lista: Optional[List[str]], db: Session):
    if not lista:
        return
    existentes = {t.nombre for t in db.query(Tienda).all()}
    desconocidas = [t for t in lista if t.strip() and t.strip() not in existentes]
    if desconocidas:
        raise HTTPException(status_code=400, detail=f"Tienda(s) desconocida(s): {', '.join(desconocidas)}")


def aplicar_filtro_tienda(query, sesion: Optional[Sesion]):
    """Restringe un query de Producto a la(s) tienda(s) activa(s) de la sesión.
    Sin sesión, o sesión sin tienda activa (ej. Only Enterprises) -> sin restricción.
    Los productos sin tienda clasificada (None) siempre son visibles."""
    if sesion and sesion.tienda:
        tiendas_activas = texto_a_tiendas(sesion.tienda)
        query = query.filter(or_(Producto.tienda.is_(None), Producto.tienda.in_(tiendas_activas)))
    return query


def sucursal_restriccion(sesion: Optional[Sesion]) -> Optional[str]:
    """Nombre exacto de sucursal al que deben restringirse las transacciones
    (ventas, gastos, cotizaciones, créditos, dashboard...) de esta sesión.
    A diferencia del catálogo de productos (que se comparte por tienda, ej.
    Only Reef se vende igual en Plaza que en Imprenta), cada sucursal física
    lleva su propia caja: Imprenta no debe ver las ventas de Plaza aunque
    ambas vendan Only Reef. None = sin restricción (ej. Only Enterprises, o
    una sucursal todavía sin tienda asignada)."""
    if sesion and sesion.tienda and sesion.sucursal:
        return sesion.sucursal
    return None


def sucursales_visibles(db: Session, sesion: Optional[Sesion]) -> Optional[List[str]]:
    """Sucursales cuyo inventario puede consultar esta sesión: la suya y las
    demás que vendan alguna de sus mismas tiendas — desde Plaza se ve también
    Imprenta, porque las dos venden Only Reef, pero no Reptile. None = todas,
    sin restricción (Only Enterprises).

    Ojo: esto es solo para *ver*. El destino de un traslado puede ser cualquier
    sucursal: mandar producto a otra tienda es una operación física legítima,
    y no revela su inventario."""
    if not (sesion and sesion.tienda):
        return None
    mias = set(texto_a_tiendas(sesion.tienda))
    nombres = [
        s.nombre for s in db.query(Sucursal).order_by(Sucursal.nombre).all()
        if mias & set(texto_a_tiendas(s.tiendas))
    ]
    if sesion.sucursal and sesion.sucursal not in nombres:
        nombres.append(sesion.sucursal)
    return nombres


def verificar_sucursal_visible(db: Session, sesion: Optional[Sesion], sucursal: str):
    """404 si el inventario de esa sucursal no le corresponde a esta sesión."""
    visibles = sucursales_visibles(db, sesion)
    if visibles is not None and sucursal not in visibles:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")


def verificar_venta_visible(db: Session, sesion: Optional[Sesion], v: Venta):
    """404 si la venta no es de la sucursal de esta sesión (no se expone qué
    existe en otras sucursales)."""
    restriccion = sucursal_restriccion(sesion)
    if restriccion is not None and v.sucursal != restriccion:
        raise HTTPException(status_code=404, detail="Venta no encontrada")


@app.get("/api/sucursales")
def listar_sucursales(db: Session = Depends(get_db)):
    """Público (sin sesión) para que el login pueda mostrar la lista."""
    rows = db.query(Sucursal).order_by(Sucursal.nombre).all()
    return [{"id": s.id, "nombre": s.nombre, "tiendas": texto_a_tiendas(s.tiendas)} for s in rows]


@app.post("/api/sucursales", status_code=201)
def crear_sucursal(data: CrearSucursal, sesion: Sesion = Depends(requerir_enterprise), db: Session = Depends(get_db)):
    nombre = data.nombre.strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")
    if db.query(Sucursal).filter(Sucursal.nombre == nombre).first():
        raise HTTPException(status_code=409, detail="Esa sucursal ya existe")
    validar_tiendas(data.tiendas, db)
    s = Sucursal(nombre=nombre, tiendas=tiendas_a_texto(data.tiendas))
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"id": s.id, "nombre": s.nombre, "tiendas": texto_a_tiendas(s.tiendas)}


@app.patch("/api/sucursales/{sucursal_id}")
def editar_sucursal(sucursal_id: int, data: EditarSucursal, sesion: Sesion = Depends(requerir_enterprise), db: Session = Depends(get_db)):
    s = db.query(Sucursal).filter(Sucursal.id == sucursal_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    cambios = data.model_dump(exclude_unset=True)
    if "nombre" in cambios:
        nuevo_nombre = (cambios["nombre"] or "").strip()
        if not nuevo_nombre:
            raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")
        existe = db.query(Sucursal).filter(Sucursal.nombre == nuevo_nombre, Sucursal.id != sucursal_id).first()
        if existe:
            raise HTTPException(status_code=409, detail="Ya existe una sucursal con ese nombre")
        s.nombre = nuevo_nombre
    if "tiendas" in cambios:
        validar_tiendas(cambios["tiendas"], db)
        s.tiendas = tiendas_a_texto(cambios["tiendas"])
    db.commit()
    db.refresh(s)
    return {"id": s.id, "nombre": s.nombre, "tiendas": texto_a_tiendas(s.tiendas)}


@app.delete("/api/sucursales/{sucursal_id}", status_code=204)
def eliminar_sucursal(sucursal_id: int, sesion: Sesion = Depends(requerir_enterprise), db: Session = Depends(get_db)):
    s = db.query(Sucursal).filter(Sucursal.id == sucursal_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    if db.query(Sucursal).count() <= 1:
        raise HTTPException(status_code=400, detail="Debe quedar al menos una sucursal")
    db.delete(s)
    db.commit()


# ─── Tiendas (submarcas: Only Reef, Only Garden...) ────────────────────────
@app.get("/api/tiendas")
def listar_tiendas(db: Session = Depends(get_db)):
    """Público (sin sesión), igual que /api/sucursales."""
    rows = db.query(Tienda).order_by(Tienda.nombre).all()
    return [{"id": t.id, "nombre": t.nombre} for t in rows]


@app.post("/api/tiendas", status_code=201)
def crear_tienda(data: CrearTienda, sesion: Sesion = Depends(requerir_enterprise), db: Session = Depends(get_db)):
    nombre = data.nombre.strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")
    if db.query(Tienda).filter(Tienda.nombre == nombre).first():
        raise HTTPException(status_code=409, detail="Esa tienda ya existe")
    t = Tienda(nombre=nombre)
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"id": t.id, "nombre": t.nombre}


@app.delete("/api/tiendas/{tienda_id}", status_code=204)
def eliminar_tienda(tienda_id: int, sesion: Sesion = Depends(requerir_enterprise), db: Session = Depends(get_db)):
    t = db.query(Tienda).filter(Tienda.id == tienda_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tienda no encontrada")
    db.delete(t)
    db.commit()


@app.post("/api/productos/clasificar-masivo")
def clasificar_productos_masivo(data: ClasificarProductosMasivo, sesion: Sesion = Depends(requerir_enterprise), db: Session = Depends(get_db)):
    if data.tienda:
        if not db.query(Tienda).filter(Tienda.nombre == data.tienda).first():
            raise HTTPException(status_code=404, detail="Esa tienda no existe")
    actualizados = (
        db.query(Producto)
        .filter(Producto.id.in_(data.producto_ids))
        .update({"tienda": data.tienda, "actualizado_en": datetime.utcnow()}, synchronize_session=False)
    )
    db.commit()
    return {"actualizados": actualizados, "tienda": data.tienda}


# ─── Ruta raíz → app web ───────────────────────────────────────────────────
@app.get("/", response_class=FileResponse)
def root():
    return FileResponse("static/menu.html")


@app.get("/login", response_class=FileResponse)
def login_page():
    return FileResponse("static/login.html")


@app.get("/usuarios", response_class=FileResponse)
def usuarios_page():
    return FileResponse("static/usuarios.html")


@app.get("/inventario", response_class=FileResponse)
def inventario_page():
    return FileResponse("static/index.html")


@app.get("/precios", response_class=FileResponse)
def precios_page():
    return FileResponse("static/precios.html")


@app.get("/pagos", response_class=FileResponse)
def pagos_page():
    return FileResponse("static/pagos.html")


@app.get("/historial", response_class=FileResponse)
def historial_page():
    return FileResponse("static/historial.html")


@app.get("/devoluciones", response_class=FileResponse)
def devoluciones_page():
    return FileResponse("static/devoluciones.html")


@app.get("/inventario-sucursales", response_class=FileResponse)
def inventario_sucursales_page():
    return FileResponse("static/inv_sucursales.html")


@app.get("/tiendas-clasificar", response_class=FileResponse)
def tiendas_clasificar_page():
    return FileResponse("static/tiendas_clasificar.html")


# ─── Resumen / dashboard ───────────────────────────────────────────────────
@app.get("/api/resumen")
def resumen(db: Session = Depends(get_db)):
    total = db.query(func.count(Producto.id)).scalar()
    valor = db.query(func.sum(Producto.precio_venta * Producto.stock)).scalar() or 0
    stock_bajo = db.query(func.count(Producto.id)).filter(
        Producto.stock > 0, Producto.stock <= Producto.stock_minimo
    ).scalar()
    agotados = db.query(func.count(Producto.id)).filter(Producto.stock == 0).scalar()
    categorias = db.query(func.count(Producto.categoria.distinct())).scalar()
    return {
        "total_productos": total,
        "valor_inventario": round(valor, 2),
        "stock_bajo": stock_bajo,
        "agotados": agotados,
        "categorias": categorias,
    }


# ─── Listar productos ──────────────────────────────────────────────────────
@app.get("/api/productos", response_model=List[ProductoOut])
def listar(
    q: Optional[str] = Query(None, description="Buscar por nombre o categoría"),
    categoria: Optional[str] = Query(None),
    tienda: Optional[str] = Query(None),
    sin_clasificar: bool = Query(False, description="Solo productos sin tienda asignada"),
    estado: Optional[str] = Query(None, description="ok | bajo | agotado"),
    skip: int = 0,
    limit: int = 200,
    sesion: Optional[Sesion] = Depends(sesion_opcional),
    db: Session = Depends(get_db),
):
    query = db.query(Producto)
    if q:
        query = query.filter(
            or_(
                Producto.nombre.ilike(f"%{q}%"),
                Producto.categoria.ilike(f"%{q}%"),
            )
        )
    if categoria:
        query = query.filter(Producto.categoria == categoria)
    if sin_clasificar:
        query = query.filter(Producto.tienda.is_(None))
    elif tienda:
        query = query.filter(Producto.tienda == tienda)
    if estado == "agotado":
        query = query.filter(Producto.stock == 0)
    elif estado == "bajo":
        query = query.filter(Producto.stock > 0, Producto.stock <= Producto.stock_minimo)
    elif estado == "ok":
        query = query.filter(Producto.stock > Producto.stock_minimo)
    query = aplicar_filtro_tienda(query, sesion)

    return query.order_by(Producto.nombre).offset(skip).limit(limit).all()


# ─── Obtener un producto ───────────────────────────────────────────────────
@app.get("/api/productos/{id}", response_model=ProductoOut)
def obtener(id: int, db: Session = Depends(get_db)):
    p = db.query(Producto).filter(Producto.id == id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return p


# ─── Crear producto ────────────────────────────────────────────────────────
@app.post("/api/productos", response_model=ProductoOut, status_code=201)
def crear(data: ProductoCreate, sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    p = Producto(**data.model_dump())
    db.add(p)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un producto con ese código de barras")
    db.refresh(p)
    return p


# ─── Editar producto ───────────────────────────────────────────────────────
@app.patch("/api/productos/{id}", response_model=ProductoOut)
def editar(id: int, data: ProductoUpdate, sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    p = db.query(Producto).filter(Producto.id == id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    cambios = data.model_dump(exclude_unset=True)
    for k, v in cambios.items():
        setattr(p, k, v)
    p.actualizado_en = datetime.utcnow()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un producto con ese código de barras")
    db.refresh(p)
    return p


# ─── Buscar por código de barras (para el escáner) ─────────────────────────
@app.get("/api/productos/buscar/codigo/{codigo}", response_model=ProductoOut)
def buscar_por_codigo(codigo: str, sesion: Optional[Sesion] = Depends(sesion_opcional), db: Session = Depends(get_db)):
    query = aplicar_filtro_tienda(db.query(Producto).filter(Producto.codigo_barras == codigo), sesion)
    p = query.first()
    if not p:
        raise HTTPException(status_code=404, detail="No hay producto con ese código de barras")
    return p


# ─── Ajustar stock (sumar o restar) ───────────────────────────────────────
@app.post("/api/productos/{id}/stock", response_model=ProductoOut)
def ajustar_stock(id: int, data: AjusteStock, sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    p = db.query(Producto).filter(Producto.id == id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    nuevo = p.stock + data.cantidad
    if nuevo < 0:
        raise HTTPException(status_code=400, detail="El stock no puede ser negativo")
    p.stock = nuevo
    p.actualizado_en = datetime.utcnow()
    db.commit()
    db.refresh(p)
    return p


# ─── Eliminar producto ─────────────────────────────────────────────────────
@app.delete("/api/productos/{id}", status_code=204)
def eliminar(id: int, sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    p = db.query(Producto).filter(Producto.id == id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    db.delete(p)
    db.commit()


# ─── Categorías disponibles ────────────────────────────────────────────────
@app.get("/api/categorias")
def categorias(db: Session = Depends(get_db)):
    rows = db.query(Producto.categoria).distinct().order_by(Producto.categoria).all()
    return [r[0] for r in rows]


# ─── Marcas disponibles ────────────────────────────────────────────────────
@app.get("/api/marcas")
def marcas(db: Session = Depends(get_db)):
    rows = db.query(Producto.marca).filter(Producto.marca != None).distinct().order_by(Producto.marca).all()
    return [r[0] for r in rows if r[0]]


# ─── Descuento masivo por categoría ─────────────────────────────────────────
@app.post("/api/productos/descuento-categoria")
def descuento_categoria(data: DescuentoCategoria, sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    productos = db.query(Producto).filter(Producto.categoria == data.categoria).all()
    if not productos:
        raise HTTPException(status_code=404, detail="No hay productos en esa categoría")
    ahora = datetime.utcnow()
    for p in productos:
        p.descuento_pct = data.descuento_pct
        p.descuento_desde = ahora
        p.descuento_hasta = data.descuento_hasta
        p.actualizado_en = ahora
    db.commit()
    return {"actualizados": len(productos), "categoria": data.categoria, "descuento_pct": data.descuento_pct}


# ─── Stock asignado por sucursal ─────────────────────────────────────────────
@app.get("/api/stock-sucursal/{sucursal}")
def stock_sucursal(sucursal: str, sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    verificar_sucursal_visible(db, sesion, sucursal)
    rows = db.query(StockSucursal).filter(StockSucursal.sucursal == sucursal).all()
    return {r.producto_id: r.cantidad for r in rows}


@app.post("/api/stock-sucursal")
def asignar_stock(data: AsignarStockSucursal, sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    # No se asigna stock a una sucursal cuyo inventario ni siquiera se ve
    verificar_sucursal_visible(db, sesion, data.sucursal)

    # Verificar que el producto existe y tiene suficiente stock global
    p = db.query(Producto).filter(Producto.id == data.producto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # Stock ya asignado a OTRAS sucursales (no la actual)
    ya_asignado = db.query(StockSucursal).filter(
        StockSucursal.producto_id == data.producto_id,
        StockSucursal.sucursal != data.sucursal
    ).all()
    total_otras = sum(r.cantidad for r in ya_asignado)

    # Stock disponible para asignar = global - asignado a otras
    disponible = p.stock - total_otras
    if data.cantidad > disponible:
        raise HTTPException(
            status_code=400,
            detail=f"Stock insuficiente. Disponible para asignar: {round(disponible, 3)} (stock global: {p.stock}, asignado a otras: {round(total_otras, 3)})"
        )

    # Upsert
    reg = db.query(StockSucursal).filter(
        StockSucursal.producto_id == data.producto_id,
        StockSucursal.sucursal == data.sucursal
    ).first()
    if reg:
        reg.cantidad = data.cantidad
        reg.actualizado_en = datetime.utcnow()
    else:
        db.add(StockSucursal(producto_id=data.producto_id, sucursal=data.sucursal, cantidad=data.cantidad))
    db.commit()
    return {"producto_id": data.producto_id, "sucursal": data.sucursal, "cantidad": data.cantidad,
            "stock_global": p.stock, "disponible_restante": round(disponible - data.cantidad, 3)}


@app.post("/api/stock-sucursal/trasladar")
def trasladar_stock(data: TrasladoStock, sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    if data.sucursal_origen == data.sucursal_destino:
        raise HTTPException(status_code=400, detail="La sucursal de origen y destino no pueden ser la misma")

    # Una sesión de sucursal solo saca de su propio inventario — ni siquiera de
    # otra de su misma tienda, que puede consultar pero no administrar. El
    # destino, en cambio, puede ser cualquiera: mandar producto a otra tienda
    # es una operación física legítima y no revela su inventario.
    restriccion = sucursal_restriccion(sesion)
    if restriccion is not None and data.sucursal_origen != restriccion:
        raise HTTPException(
            status_code=403,
            detail=f"Solo puedes enviar producto desde tu sucursal ({restriccion})",
        )

    p = db.query(Producto).filter(Producto.id == data.producto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    origen = db.query(StockSucursal).filter(
        StockSucursal.producto_id == data.producto_id,
        StockSucursal.sucursal == data.sucursal_origen
    ).first()
    stock_origen = origen.cantidad if origen else 0

    if data.cantidad > stock_origen:
        raise HTTPException(
            status_code=400,
            detail=f"Stock insuficiente en Suc. {data.sucursal_origen} (disponible: {round(stock_origen,3)})"
        )

    # Restar de origen
    origen.cantidad = round(origen.cantidad - data.cantidad, 3)
    origen.actualizado_en = datetime.utcnow()

    # Sumar a destino (upsert)
    destino = db.query(StockSucursal).filter(
        StockSucursal.producto_id == data.producto_id,
        StockSucursal.sucursal == data.sucursal_destino
    ).first()
    if destino:
        destino.cantidad = round(destino.cantidad + data.cantidad, 3)
        destino.actualizado_en = datetime.utcnow()
    else:
        db.add(StockSucursal(
            producto_id=data.producto_id,
            sucursal=data.sucursal_destino,
            cantidad=data.cantidad,
            actualizado_en=datetime.utcnow()
        ))

    db.commit()
    return {
        "producto_id": data.producto_id,
        "producto_nombre": p.nombre,
        "sucursal_origen": data.sucursal_origen,
        "sucursal_destino": data.sucursal_destino,
        "cantidad_trasladada": data.cantidad,
        "stock_restante_origen": round(stock_origen - data.cantidad, 3),
    }


# ─── Consulta pública de precios (sin info de inventario) ─────────────────
@app.get("/api/lista-precios")
def lista_precios(q: Optional[str] = Query(None), categoria: Optional[str] = Query(None), codigo: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(Producto)
    if codigo:
        query = query.filter(Producto.codigo_barras == codigo)
    if q:
        query = query.filter(
            or_(Producto.nombre.ilike(f"%{q}%"), Producto.categoria.ilike(f"%{q}%"), Producto.codigo_barras == q)
        )
    if categoria:
        query = query.filter(Producto.categoria == categoria)
    rows = query.order_by(Producto.categoria, Producto.nombre).all()
    ahora = datetime.utcnow()
    resultado = []
    for p in rows:
        descuento_activo = False
        precio_final = p.precio_venta
        if p.descuento_pct and p.descuento_pct > 0:
            desde_ok = (p.descuento_desde is None) or (p.descuento_desde <= ahora)
            hasta_ok = (p.descuento_hasta is None) or (p.descuento_hasta >= ahora)
            if desde_ok and hasta_ok:
                descuento_activo = True
                precio_final = round(p.precio_venta * (1 - p.descuento_pct / 100), 2)
        resultado.append({
            "nombre": p.nombre,
            "categoria": p.categoria,
            "precio_venta": p.precio_venta,
            "precio_final": precio_final,
            "descuento_pct": p.descuento_pct if descuento_activo else 0,
            "unidad": p.unidad,
            "codigo_barras": p.codigo_barras,
            "vendido_por_peso": bool(p.vendido_por_peso),
            "precio_gramo": round(precio_final / 1000, 4) if p.vendido_por_peso else None,
            "imagen_url": p.imagen_url,
        })
    return resultado


# ─── Consulta de precio rápida ─────────────────────────────────────────────
@app.get("/api/precio/{nombre}")
def precio(nombre: str, db: Session = Depends(get_db)):
    resultados = db.query(Producto).filter(
        Producto.nombre.ilike(f"%{nombre}%")
    ).limit(10).all()
    if not resultados:
        raise HTTPException(status_code=404, detail="Sin resultados")
    return [
        {"id": p.id, "nombre": p.nombre, "precio_venta": p.precio_venta, "stock": p.stock}
        for p in resultados
    ]


# ─── Punto de venta: autorización de descuento ─────────────────────────────
@app.post("/api/pos/autorizar")
def autorizar_descuento(data: AutorizarDescuento, db: Session = Depends(get_db)):
    u = db.query(Usuario).filter(Usuario.usuario == data.usuario).first()
    if not u or not verificar_password(data.password, u.password_hash, u.salt):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    if u.rol != "gerente":
        raise HTTPException(status_code=403, detail="Este usuario no puede autorizar descuentos")
    return {"autorizado": True, "usuario": u.usuario, "descuento_pct": data.descuento_pct}


# ─── Punto de venta: registrar venta y descontar stock ─────────────────────
@app.post("/api/pos/venta")
def registrar_venta(data: RegistrarVenta, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    if not data.items:
        raise HTTPException(status_code=400, detail="La venta no tiene artículos")

    # Validar stock disponible y calcular subtotal
    subtotal = 0.0
    ahorro_productos = 0.0
    detalle = []
    productos_map = {}
    for item in data.items:
        importe = round(item.precio_unitario * item.cantidad, 2)
        subtotal += importe
        ahorro_item = 0.0
        if item.precio_original is not None and item.precio_original > item.precio_unitario:
            ahorro_item = round((item.precio_original - item.precio_unitario) * item.cantidad, 2)
            ahorro_productos += ahorro_item

        if item.producto_id is not None:
            # Restriccion de stock desactivada: se permite vender con stock 0 o negativo
            p = db.query(Producto).filter(Producto.id == item.producto_id).first()
            if not p:
                raise HTTPException(status_code=404, detail=f"Producto {item.producto_id} no existe")
            productos_map[p.id] = p
            nombre_item = p.nombre
            pid = p.id
        else:
            nombre_item = (item.nombre or "").strip()
            if not nombre_item:
                raise HTTPException(status_code=400, detail="Los artículos personalizados necesitan una descripción")
            pid = None

        detalle.append({
            "producto_id": pid,
            "nombre": nombre_item,
            "cantidad": item.cantidad,
            "precio_unitario": item.precio_unitario,
            "precio_original": item.precio_original,
            "ahorro": ahorro_item,
            "importe": importe,
        })

    subtotal = round(subtotal, 2)
    ahorro_productos = round(ahorro_productos, 2)
    total = round(subtotal * (1 - data.descuento_extra_pct / 100), 2)
    ahorro_descuento_extra = round(subtotal - total, 2)
    ahorro_total = round(ahorro_productos + ahorro_descuento_extra, 2)
    metodo = data.metodo_pago if data.metodo_pago in ("efectivo", "tarjeta", "credito", "transferencia") else "efectivo"

    cliente = None
    if metodo == "credito":
        if not data.cliente_id:
            raise HTTPException(status_code=400, detail="Selecciona un cliente para la venta a crédito")
        cliente = db.query(Cliente).filter(Cliente.id == data.cliente_id).first()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

    if metodo == "tarjeta" or metodo == "transferencia":
        # En tarjeta/transferencia no hay cambio; el pago es por el total exacto
        pago_con = total
        cambio = 0.0
    elif metodo == "credito":
        # En credito no se cobra en el momento de la venta
        pago_con = None
        cambio = None
    else:
        pago_con = data.pago_con
        cambio = round(pago_con - total, 2) if (pago_con is not None and pago_con >= total) else None

    # Descontar stock (solo articulos con producto real; los
    # personalizados -mano de obra, servicios- no tienen inventario)
    for item in data.items:
        if item.producto_id is None:
            continue
        p = productos_map[item.producto_id]
        p.stock = round(p.stock - item.cantidad, 3)
        p.actualizado_en = datetime.utcnow()

    # Guardar venta
    venta = Venta(
        total=total,
        subtotal=subtotal,
        descuento_extra_pct=data.descuento_extra_pct,
        autorizado_por=data.autorizado_por,
        operador=sesion.usuario,
        sucursal=sesion.sucursal,
        metodo_pago=metodo,
        cliente_id=data.cliente_id if metodo == "credito" else None,
        tpv_referencia=data.tpv_referencia if metodo == "tarjeta" else None,
        tpv_autorizacion=data.tpv_autorizacion if metodo == "tarjeta" else None,
        tpv_terminal=data.tpv_terminal if metodo == "tarjeta" else None,
        transferencia_referencia=data.transferencia_referencia if metodo == "transferencia" else None,
        detalle_json=json.dumps(detalle, ensure_ascii=False),
        pago_con=pago_con,
        cambio=cambio,
    )
    db.add(venta)
    db.commit()
    db.refresh(venta)

    return {
        "id": venta.id,
        "subtotal": subtotal,
        "descuento_extra_pct": data.descuento_extra_pct,
        "total": total,
        "ahorro_productos": ahorro_productos,
        "ahorro_descuento_extra": ahorro_descuento_extra,
        "ahorro_total": ahorro_total,
        "pago_con": pago_con,
        "cambio": cambio,
        "metodo_pago": metodo,
        "cliente_id": venta.cliente_id,
        "cliente_nombre": cliente.nombre if cliente else None,
        "tpv_referencia": venta.tpv_referencia,
        "tpv_autorizacion": venta.tpv_autorizacion,
        "tpv_terminal": venta.tpv_terminal,
        "transferencia_referencia": venta.transferencia_referencia,
        "autorizado_por": data.autorizado_por,
        "operador": sesion.usuario,
        "sucursal": sesion.sucursal,
        "detalle": detalle,
        "fecha": venta.creado_en.isoformat() + "Z",
    }


# ─── Historial de ventas ───────────────────────────────────────────────────
@app.get("/api/ventas")
def listar_ventas(
    desde: Optional[str] = Query(None, description="YYYY-MM-DD o ISO datetime"),
    hasta: Optional[str] = Query(None, description="YYYY-MM-DD o ISO datetime"),
    operador: Optional[str] = Query(None),
    metodo_pago: Optional[str] = Query(None, description="efectivo | tarjeta"),
    sucursal: Optional[str] = Query(None),
    limit: int = 500,
    sesion: Sesion = Depends(requerir_gerente),
    db: Session = Depends(get_db),
):
    query = db.query(Venta)
    if desde:
        try:
            d = datetime.fromisoformat(desde.replace("Z", "+00:00"))
            if d.tzinfo:
                d = d.astimezone(timezone.utc).replace(tzinfo=None)
            query = query.filter(Venta.creado_en >= d)
        except ValueError:
            pass
    if hasta:
        try:
            h = datetime.fromisoformat(hasta.replace("Z", "+00:00"))
            if h.tzinfo:
                h = h.astimezone(timezone.utc).replace(tzinfo=None)
            query = query.filter(Venta.creado_en <= h)
        except ValueError:
            pass
    if operador:
        query = query.filter(Venta.operador == operador)
    if metodo_pago in ("efectivo", "tarjeta", "credito", "transferencia"):
        query = query.filter(Venta.metodo_pago == metodo_pago)
    if sucursal:
        query = query.filter(Venta.sucursal == sucursal)
    restriccion = sucursal_restriccion(sesion)
    if restriccion is not None:
        query = query.filter(Venta.sucursal == restriccion)
    ventas = query.order_by(Venta.creado_en.desc()).limit(limit).all()
    return [
        {
            "id": v.id,
            "fecha": v.creado_en.isoformat() + "Z",
            "subtotal": v.subtotal,
            "descuento_extra_pct": v.descuento_extra_pct,
            "total": v.total,
            "autorizado_por": v.autorizado_por,
            "operador": v.operador,
            "sucursal": v.sucursal,
            "metodo_pago": v.metodo_pago or "efectivo",
            "estado": v.estado or "activa",
            "total_devuelto": v.total_devuelto or 0,
            "venta_origen_id": v.venta_origen_id,
            "tpv_referencia": v.tpv_referencia,
            "tpv_autorizacion": v.tpv_autorizacion,
            "pago_con": v.pago_con,
            "cambio": v.cambio,
            "num_items": len(json.loads(v.detalle_json)),
            "cantidad_total": sum(it.get("cantidad", 0) for it in json.loads(v.detalle_json)),
        }
        for v in ventas
    ]


@app.get("/api/ventas/resumen")
def resumen_ventas(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    operador: Optional[str] = Query(None),
    metodo_pago: Optional[str] = Query(None),
    sucursal: Optional[str] = Query(None),
    sesion: Sesion = Depends(requerir_gerente),
    db: Session = Depends(get_db),
):
    query = db.query(Venta)
    if desde:
        try:
            d = datetime.fromisoformat(desde.replace("Z", "+00:00"))
            if d.tzinfo:
                d = d.astimezone(timezone.utc).replace(tzinfo=None)
            query = query.filter(Venta.creado_en >= d)
        except ValueError:
            pass
    if hasta:
        try:
            h = datetime.fromisoformat(hasta.replace("Z", "+00:00"))
            if h.tzinfo:
                h = h.astimezone(timezone.utc).replace(tzinfo=None)
            query = query.filter(Venta.creado_en <= h)
        except ValueError:
            pass
    if operador:
        query = query.filter(Venta.operador == operador)
    if metodo_pago in ("efectivo", "tarjeta", "credito", "transferencia"):
        query = query.filter(Venta.metodo_pago == metodo_pago)
    if sucursal:
        query = query.filter(Venta.sucursal == sucursal)
    restriccion = sucursal_restriccion(sesion)
    if restriccion is not None:
        query = query.filter(Venta.sucursal == restriccion)
    ventas = query.all()
    total_vendido = round(sum(v.total for v in ventas), 2)
    total_efectivo = round(sum(v.total for v in ventas if (v.metodo_pago or "efectivo") == "efectivo"), 2)
    total_tarjeta = round(sum(v.total for v in ventas if v.metodo_pago == "tarjeta"), 2)

    # Desglose por operador, separando efectivo y tarjeta
    por_operador = {}
    for v in ventas:
        op = v.operador or "(sin operador)"
        if op not in por_operador:
            por_operador[op] = {"operador": op, "num_ventas": 0, "total": 0.0, "efectivo": 0.0, "tarjeta": 0.0}
        por_operador[op]["num_ventas"] += 1
        por_operador[op]["total"] += v.total
        if v.metodo_pago == "tarjeta":
            por_operador[op]["tarjeta"] += v.total
        else:
            por_operador[op]["efectivo"] += v.total
    desglose = sorted(
        [{"operador": d["operador"], "num_ventas": d["num_ventas"],
          "total": round(d["total"], 2), "efectivo": round(d["efectivo"], 2), "tarjeta": round(d["tarjeta"], 2)}
         for d in por_operador.values()],
        key=lambda x: x["total"], reverse=True
    )

    # Desglose por sucursal: ventas, monto y artículos vendidos
    por_sucursal = {}
    for v in ventas:
        suc = v.sucursal or "(sin sucursal)"
        if suc not in por_sucursal:
            por_sucursal[suc] = {"sucursal": suc, "num_ventas": 0, "total": 0.0, "items_vendidos": 0.0}
        por_sucursal[suc]["num_ventas"] += 1
        por_sucursal[suc]["total"] += v.total
        por_sucursal[suc]["items_vendidos"] += sum(it.get("cantidad", 0) for it in json.loads(v.detalle_json))
    desglose_sucursal = sorted(
        [{"sucursal": d["sucursal"], "num_ventas": d["num_ventas"],
          "total": round(d["total"], 2), "items_vendidos": round(d["items_vendidos"], 3)}
         for d in por_sucursal.values()],
        key=lambda x: x["total"], reverse=True
    )

    return {
        "num_ventas": len(ventas),
        "total_vendido": total_vendido,
        "total_efectivo": total_efectivo,
        "total_tarjeta": total_tarjeta,
        "ticket_promedio": round(total_vendido / len(ventas), 2) if ventas else 0,
        "por_operador": desglose,
        "por_sucursal": desglose_sucursal,
    }


@app.get("/api/ventas-operadores")
def operadores_con_ventas(sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    query = db.query(Venta.operador).distinct()
    restriccion = sucursal_restriccion(sesion)
    if restriccion is not None:
        query = query.filter(Venta.sucursal == restriccion)
    rows = query.all()
    return sorted([r[0] for r in rows if r[0]])


@app.get("/api/inventario/por-sucursal")
def inventario_por_sucursal(sesion: Sesion = Depends(requerir_enterprise), db: Session = Depends(get_db)):
    productos = db.query(Producto).order_by(Producto.categoria, Producto.nombre).all()
    ventas = db.query(Venta).all()
    asignaciones = db.query(StockSucursal).all()
    sucursales_reg = [s.nombre for s in db.query(Sucursal).order_by(Sucursal.nombre).all()]

    # Limpiar asignaciones huérfanas de sucursales ya eliminadas
    for a in asignaciones:
        if a.sucursal not in sucursales_reg:
            db.delete(a)
    db.commit()
    asignaciones = db.query(StockSucursal).all()

    # Vendido por producto y sucursal
    vendido: dict = {}
    sucursales_ventas: set = set()
    for v in ventas:
        suc = v.sucursal or "(sin sucursal)"
        sucursales_ventas.add(suc)
        for it in json.loads(v.detalle_json):
            pid = it.get("producto_id")
            qty = it.get("cantidad", 0)
            if pid not in vendido:
                vendido[pid] = {}
            vendido[pid][suc] = vendido[pid].get(suc, 0) + qty

    # Stock asignado por producto y sucursal
    asignado: dict = {}
    for a in asignaciones:
        if a.producto_id not in asignado:
            asignado[a.producto_id] = {}
        asignado[a.producto_id][a.sucursal] = a.cantidad

    # Solo sucursales actualmente registradas (ignorar las borradas que aparecen en ventas),
    # y de esas, únicamente las que esta sesión puede ver (las de su misma tienda).
    visibles = sucursales_visibles(db, sesion)
    sucursales = sucursales_reg if visibles is None else [s for s in sucursales_reg if s in visibles]

    resultado = []
    for p in productos:
        v_por_suc = vendido.get(p.id, {})
        a_por_suc = asignado.get(p.id, {})
        # Solo suma asignaciones de sucursales activas
        total_asignado = sum(
            cant for suc_id, cant in a_por_suc.items() if suc_id in sucursales_reg
        )
        resultado.append({
            "id": p.id,
            "nombre": p.nombre,
            "categoria": p.categoria,
            "marca": p.marca,
            "codigo_barras": p.codigo_barras,
            "unidad": p.unidad,
            "vendido_por_peso": bool(p.vendido_por_peso),
            "stock_global": p.stock,
            "stock_minimo": p.stock_minimo,
            "stock_disponible": round(p.stock - total_asignado, 3),
            "por_sucursal": {
                suc: {
                    "asignado": round(a_por_suc.get(suc, 0), 3),
                    "vendido": round(v_por_suc.get(suc, 0), 3),
                }
                for suc in sucursales
            },
        })

    return {"sucursales": sucursales, "productos": resultado, "sucursales_registradas": sucursales_reg}


@app.get("/api/inventario/buscar-en-sucursales")
def buscar_en_sucursales(
    q: str = Query(..., min_length=1, description="Nombre o código de barras"),
    sesion: Sesion = Depends(requerir_gerente),
    db: Session = Depends(get_db),
):
    """¿Queda producto en otra sucursal? Consulta puntual, no un listado que se
    pueda navegar: responde solo por lo que se busca y solo en las sucursales
    de la misma tienda (ver sucursales_visibles). Sustituye, para una sesión de
    sucursal, el inventario comparado que ahora es de Only Enterprises."""
    termino = q.strip()
    if not termino:
        return {"sucursales": [], "productos": []}

    visibles = sucursales_visibles(db, sesion)
    if visibles is None:
        visibles = [s.nombre for s in db.query(Sucursal).order_by(Sucursal.nombre).all()]

    productos = db.query(Producto).filter(
        or_(
            Producto.nombre.ilike(f"%{termino}%"),
            Producto.codigo_barras == termino,
        )
    ).order_by(Producto.nombre).limit(25).all()
    if not productos:
        return {"sucursales": visibles, "productos": []}

    ids = {p.id for p in productos}

    asignado: dict = {}
    for a in db.query(StockSucursal).filter(StockSucursal.producto_id.in_(ids)).all():
        asignado.setdefault(a.producto_id, {})[a.sucursal] = a.cantidad

    # Lo vendido sale del detalle de cada venta, que es JSON: hay que abrirlas.
    vendido: dict = {}
    for v in db.query(Venta).filter(Venta.sucursal.in_(visibles)).all():
        for it in json.loads(v.detalle_json):
            pid = it.get("producto_id")
            if pid in ids:
                por_suc = vendido.setdefault(pid, {})
                por_suc[v.sucursal] = por_suc.get(v.sucursal, 0) + it.get("cantidad", 0)

    resultado = []
    for p in productos:
        a_por_suc = asignado.get(p.id, {})
        v_por_suc = vendido.get(p.id, {})
        filas = []
        for suc in visibles:
            asig = round(a_por_suc.get(suc, 0), 3)
            vend = round(v_por_suc.get(suc, 0), 3)
            filas.append({
                "sucursal": suc,
                "asignado": asig,
                "vendido": vend,
                "restante": round(asig - vend, 3),
            })
        resultado.append({
            "id": p.id,
            "nombre": p.nombre,
            "categoria": p.categoria,
            "marca": p.marca,
            "codigo_barras": p.codigo_barras,
            "unidad": p.unidad,
            "vendido_por_peso": bool(p.vendido_por_peso),
            "stock_global": p.stock,
            "por_sucursal": filas,
        })
    return {"sucursales": visibles, "productos": resultado}


@app.get("/api/ventas/{venta_id}")
def obtener_venta(venta_id: int, sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    v = db.query(Venta).filter(Venta.id == venta_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    verificar_venta_visible(db, sesion, v)
    detalle = json.loads(v.detalle_json)
    ahorro_productos = round(sum(it.get("ahorro", 0) or 0 for it in detalle), 2)
    ahorro_descuento_extra = round(v.subtotal - v.total, 2)

    # Cuanto se ha devuelto ya de cada articulo (desde los registros negativos)
    _previas = db.query(Venta).filter(Venta.venta_origen_id == v.id).all()
    _ya_dev = {}
    for _d in _previas:
        for _it in json.loads(_d.detalle_json):
            _pid = _it.get("producto_id")
            _ya_dev[_pid] = _ya_dev.get(_pid, 0) + abs(_it.get("cantidad", 0))
    for _linea in detalle:
        _pid = _linea.get("producto_id")
        _dev = _ya_dev.get(_pid, 0)
        _linea["devuelto"] = round(_dev, 3)
        _linea["disponible_devolucion"] = round(_linea.get("cantidad", 0) - _dev, 3)

    return {
        "id": v.id,
        "fecha": v.creado_en.isoformat() + "Z",
        "subtotal": v.subtotal,
        "descuento_extra_pct": v.descuento_extra_pct,
        "total": v.total,
        "ahorro_productos": ahorro_productos,
        "ahorro_descuento_extra": ahorro_descuento_extra,
        "ahorro_total": round(ahorro_productos + ahorro_descuento_extra, 2),
        "autorizado_por": v.autorizado_por,
        "operador": v.operador,
        "sucursal": v.sucursal,
        "metodo_pago": v.metodo_pago or "efectivo",
        "estado": v.estado or "activa",
        "total_devuelto": v.total_devuelto or 0,
        "venta_origen_id": v.venta_origen_id,
        "devoluciones": json.loads(v.devoluciones_json) if v.devoluciones_json else [],
        "tpv_referencia": v.tpv_referencia,
        "tpv_autorizacion": v.tpv_autorizacion,
        "tpv_terminal": v.tpv_terminal,
        "pago_con": v.pago_con,
        "cambio": v.cambio,
        "detalle": detalle,
    }


# ─── Devoluciones y cancelaciones ──────────────────────────────────────────
@app.post("/api/ventas/{venta_id}/devolucion")
def devolver_items(
    venta_id: int,
    data: dict = Body(...),
    sesion: Sesion = Depends(requerir_gerente),
    db: Session = Depends(get_db),
):
    v = db.query(Venta).filter(Venta.id == venta_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    verificar_venta_visible(db, sesion, v)
    if (v.estado or "activa") == "devolucion":
        raise HTTPException(status_code=400, detail="Ese registro ya es una devolución")
    if (v.estado or "activa") == "devuelta":
        raise HTTPException(status_code=400, detail="Esta venta ya fue devuelta por completo")

    items = data.get("items") or []
    if not items:
        raise HTTPException(status_code=400, detail="No se indicaron artículos a devolver")
    motivo = (data.get("motivo") or "").strip()
    if not motivo:
        raise HTTPException(status_code=400, detail="Indica el motivo de la devolución")

    detalle = json.loads(v.detalle_json)

    # Cuanto se ha devuelto ya de esta venta (sumando devoluciones previas)
    previas = db.query(Venta).filter(Venta.venta_origen_id == venta_id).all()
    ya_devuelto = {}
    for d in previas:
        for it in json.loads(d.detalle_json):
            pid = it.get("producto_id")
            ya_devuelto[pid] = ya_devuelto.get(pid, 0) + abs(it.get("cantidad", 0))

    detalle_dev = []
    monto_total = 0.0
    for it in items:
        pid = it.get("producto_id")
        cant = float(it.get("cantidad") or 0)
        if cant <= 0:
            continue
        linea = next((x for x in detalle if x.get("producto_id") == pid), None)
        if not linea:
            raise HTTPException(status_code=400, detail=f"El producto {pid} no está en esta venta")
        disponible = linea.get("cantidad", 0) - ya_devuelto.get(pid, 0)
        if cant > disponible + 0.0001:
            raise HTTPException(
                status_code=400,
                detail=f"No puedes devolver {cant} de '{linea.get('nombre')}': solo quedan {round(disponible, 3)} por devolver",
            )
        factor_desc = 1 - (v.descuento_extra_pct or 0) / 100
        importe = round(linea.get("precio_unitario", 0) * cant * factor_desc, 2)
        monto_total += importe
        detalle_dev.append({
            "producto_id": pid,
            "nombre": linea.get("nombre"),
            "cantidad": -cant,
            "precio_unitario": linea.get("precio_unitario", 0),
            "precio_original": linea.get("precio_original"),
            "ahorro": 0.0,
            "importe": -importe,
        })
        p = db.query(Producto).filter(Producto.id == pid).first()
        if p:
            p.stock = round(p.stock + cant, 3)
            p.actualizado_en = datetime.utcnow()

    if not detalle_dev:
        raise HTTPException(status_code=400, detail="No se indicaron cantidades válidas")

    monto_total = round(monto_total, 2)
    subtotal_bruto = round(sum(abs(x["cantidad"]) * x["precio_unitario"] for x in detalle_dev), 2)
    dev = Venta(
        total=-monto_total,
        subtotal=-subtotal_bruto,
        descuento_extra_pct=v.descuento_extra_pct or 0.0,
        autorizado_por=motivo,
        operador=sesion.usuario,
        sucursal=sesion.sucursal,
        metodo_pago=v.metodo_pago,
        cliente_id=v.cliente_id,
        detalle_json=json.dumps(detalle_dev, ensure_ascii=False),
        pago_con=None,
        cambio=None,
        estado="devolucion",
        venta_origen_id=venta_id,
        total_devuelto=0.0,
    )
    db.add(dev)

    v.total_devuelto = round((v.total_devuelto or 0) + monto_total, 2)
    total_items = sum(x.get("cantidad", 0) for x in detalle)
    total_dev_acum = sum(ya_devuelto.values()) + sum(abs(x["cantidad"]) for x in detalle_dev)
    v.estado = "devuelta" if total_dev_acum >= total_items - 0.0001 else "parcial"

    db.commit()
    db.refresh(dev)
    return {
        "id_devolucion": dev.id,
        "venta_origen": venta_id,
        "monto_devuelto": monto_total,
        "estado_venta_origen": v.estado,
        "total_devuelto_acumulado": v.total_devuelto,
    }


@app.post("/api/ventas/{venta_id}/cancelar")
def cancelar_venta(
    venta_id: int,
    data: dict = Body(default={}),
    sesion: Sesion = Depends(requerir_gerente),
    db: Session = Depends(get_db),
):
    v = db.query(Venta).filter(Venta.id == venta_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    verificar_venta_visible(db, sesion, v)
    if (v.estado or "activa") == "devolucion":
        raise HTTPException(status_code=400, detail="Ese registro ya es una devolución")
    if (v.estado or "activa") == "devuelta":
        raise HTTPException(status_code=400, detail="Esta venta ya fue devuelta por completo")

    motivo = (data.get("motivo") or "").strip()
    if not motivo:
        raise HTTPException(status_code=400, detail="Indica el motivo de la cancelación")

    detalle = json.loads(v.detalle_json)
    previas = db.query(Venta).filter(Venta.venta_origen_id == venta_id).all()
    ya_devuelto = {}
    for d in previas:
        for it in json.loads(d.detalle_json):
            pid = it.get("producto_id")
            ya_devuelto[pid] = ya_devuelto.get(pid, 0) + abs(it.get("cantidad", 0))

    detalle_dev = []
    monto_total = 0.0
    for linea in detalle:
        pid = linea.get("producto_id")
        pendiente = linea.get("cantidad", 0) - ya_devuelto.get(pid, 0)
        if pendiente <= 0.0001:
            continue
        factor_desc = 1 - (v.descuento_extra_pct or 0) / 100
        importe = round(linea.get("precio_unitario", 0) * pendiente * factor_desc, 2)
        monto_total += importe
        detalle_dev.append({
            "producto_id": pid,
            "nombre": linea.get("nombre"),
            "cantidad": -pendiente,
            "precio_unitario": linea.get("precio_unitario", 0),
            "precio_original": linea.get("precio_original"),
            "ahorro": 0.0,
            "importe": -importe,
        })
        p = db.query(Producto).filter(Producto.id == pid).first()
        if p:
            p.stock = round(p.stock + pendiente, 3)
            p.actualizado_en = datetime.utcnow()

    if not detalle_dev:
        raise HTTPException(status_code=400, detail="Esta venta ya no tiene artículos por devolver")

    monto_total = round(monto_total, 2)
    subtotal_bruto = round(sum(abs(x["cantidad"]) * x["precio_unitario"] for x in detalle_dev), 2)
    dev = Venta(
        total=-monto_total,
        subtotal=-subtotal_bruto,
        descuento_extra_pct=v.descuento_extra_pct or 0.0,
        autorizado_por=motivo,
        operador=sesion.usuario,
        sucursal=sesion.sucursal,
        metodo_pago=v.metodo_pago,
        cliente_id=v.cliente_id,
        detalle_json=json.dumps(detalle_dev, ensure_ascii=False),
        pago_con=None,
        cambio=None,
        estado="devolucion",
        venta_origen_id=venta_id,
        total_devuelto=0.0,
    )
    db.add(dev)

    v.total_devuelto = round((v.total_devuelto or 0) + monto_total, 2)
    v.estado = "devuelta"
    db.commit()
    db.refresh(dev)
    return {
        "id_devolucion": dev.id,
        "venta_origen": venta_id,
        "monto_devuelto": monto_total,
        "estado_venta_origen": "devuelta",
    }


# ─── Cotizaciones ───────────────────────────────────────────────────────────
@app.post("/api/cotizaciones", status_code=201)
def crear_cotizacion(data: RegistrarCotizacion, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    if not data.items:
        raise HTTPException(status_code=400, detail="La cotización no tiene artículos")

    subtotal = 0.0
    detalle = []
    for item in data.items:
        importe = round(item.precio_unitario * item.cantidad, 2)
        subtotal += importe
        if item.producto_id is not None:
            p = db.query(Producto).filter(Producto.id == item.producto_id).first()
            if not p:
                raise HTTPException(status_code=404, detail=f"Producto {item.producto_id} no existe")
            nombre_item = p.nombre
            pid = p.id
        else:
            nombre_item = (item.nombre or "").strip()
            if not nombre_item:
                raise HTTPException(status_code=400, detail="Los artículos personalizados necesitan una descripción")
            pid = None
        detalle.append({
            "producto_id": pid,
            "nombre": nombre_item,
            "cantidad": item.cantidad,
            "precio_unitario": item.precio_unitario,
            "importe": importe,
        })

    subtotal = round(subtotal, 2)
    total = round(subtotal * (1 - data.descuento_extra_pct / 100), 2)

    cot = Cotizacion(
        cliente_nombre=(data.cliente_nombre or "").strip() or None,
        cliente_telefono=(data.cliente_telefono or "").strip() or None,
        subtotal=subtotal,
        descuento_extra_pct=data.descuento_extra_pct,
        total=total,
        detalle_json=json.dumps(detalle, ensure_ascii=False),
        operador=sesion.usuario,
        sucursal=sesion.sucursal,
        nota=(data.nota or "").strip() or None,
    )
    db.add(cot)
    db.commit()
    db.refresh(cot)

    return {
        "id": cot.id,
        "cliente_nombre": cot.cliente_nombre,
        "cliente_telefono": cot.cliente_telefono,
        "subtotal": subtotal,
        "descuento_extra_pct": data.descuento_extra_pct,
        "total": total,
        "operador": sesion.usuario,
        "sucursal": sesion.sucursal,
        "nota": cot.nota,
        "detalle": detalle,
        "fecha": cot.creado_en.isoformat() + "Z",
    }


@app.post("/api/cotizaciones/{cotizacion_id}/marcar-vendida")
def marcar_cotizacion_vendida(cotizacion_id: int, data: dict = Body(...), sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    c = db.query(Cotizacion).filter(Cotizacion.id == cotizacion_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    restriccion = sucursal_restriccion(sesion)
    if restriccion is not None and c.sucursal != restriccion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    venta_id = data.get("venta_id")
    if not venta_id:
        raise HTTPException(status_code=400, detail="Falta venta_id")
    c.venta_id = venta_id
    db.commit()
    return {"id": c.id, "venta_id": c.venta_id}


@app.get("/api/cotizaciones")
def listar_cotizaciones(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    sesion: Sesion = Depends(requerir_sesion),
    db: Session = Depends(get_db),
):
    d, h = _rango_utc_gastos(desde, hasta)
    q = db.query(Cotizacion)
    if d:
        q = q.filter(Cotizacion.creado_en >= d)
    if h:
        q = q.filter(Cotizacion.creado_en <= h)
    restriccion = sucursal_restriccion(sesion)
    if restriccion is not None:
        q = q.filter(Cotizacion.sucursal == restriccion)
    cots = q.order_by(Cotizacion.creado_en.desc()).all()
    return [
        {
            "id": c.id,
            "cliente_nombre": c.cliente_nombre,
            "total": c.total,
            "num_items": len(json.loads(c.detalle_json)),
            "operador": c.operador,
            "sucursal": c.sucursal,
            "venta_id": c.venta_id,
            "fecha": c.creado_en.isoformat() + "Z",
        }
        for c in cots
    ]


@app.get("/api/cotizaciones/{cotizacion_id}")
def obtener_cotizacion(cotizacion_id: int, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    c = db.query(Cotizacion).filter(Cotizacion.id == cotizacion_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    restriccion = sucursal_restriccion(sesion)
    if restriccion is not None and c.sucursal != restriccion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    return {
        "id": c.id,
        "cliente_nombre": c.cliente_nombre,
        "cliente_telefono": c.cliente_telefono,
        "subtotal": c.subtotal,
        "descuento_extra_pct": c.descuento_extra_pct,
        "total": c.total,
        "operador": c.operador,
        "sucursal": c.sucursal,
        "nota": c.nota,
        "venta_id": c.venta_id,
        "detalle": json.loads(c.detalle_json),
        "fecha": c.creado_en.isoformat() + "Z",
    }


@app.get("/cotizaciones", response_class=FileResponse)
def cotizaciones_page():
    return FileResponse("static/cotizaciones.html")


@app.get("/api/pos/producto/{producto_id}")
def pos_producto(producto_id: int, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    query = aplicar_filtro_tienda(db.query(Producto).filter(Producto.id == producto_id), sesion)
    p = query.first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    ahora = datetime.utcnow()
    precio_final = p.precio_venta
    if p.descuento_pct and p.descuento_pct > 0:
        desde_ok = (p.descuento_desde is None) or (p.descuento_desde <= ahora)
        hasta_ok = (p.descuento_hasta is None) or (p.descuento_hasta >= ahora)
        if desde_ok and hasta_ok:
            precio_final = round(p.precio_venta * (1 - p.descuento_pct / 100), 2)
    return {
        "id": p.id,
        "nombre": p.nombre,
        "categoria": p.categoria,
        "precio_venta": p.precio_venta,
        "precio_final": precio_final,
        "stock": p.stock,
        "unidad": p.unidad,
        "vendido_por_peso": bool(p.vendido_por_peso),
        "codigo_barras": p.codigo_barras,
    }


@app.get("/api/pos/buscar")
def pos_buscar(q: str = Query(...), sesion: Optional[Sesion] = Depends(sesion_opcional), db: Session = Depends(get_db)):
    query = db.query(Producto).filter(
        or_(
            Producto.nombre.ilike(f"%{q}%"),
            Producto.codigo_barras == q,
        )
    )
    rows = aplicar_filtro_tienda(query, sesion).order_by(Producto.nombre).limit(20).all()
    ahora = datetime.utcnow()
    resultado = []
    for p in rows:
        precio_final = p.precio_venta
        if p.descuento_pct and p.descuento_pct > 0:
            desde_ok = (p.descuento_desde is None) or (p.descuento_desde <= ahora)
            hasta_ok = (p.descuento_hasta is None) or (p.descuento_hasta >= ahora)
            if desde_ok and hasta_ok:
                precio_final = round(p.precio_venta * (1 - p.descuento_pct / 100), 2)
        resultado.append({
            "id": p.id,
            "nombre": p.nombre,
            "categoria": p.categoria,
            "precio_venta": p.precio_venta,
            "precio_final": precio_final,
            "stock": p.stock,
            "unidad": p.unidad,
            "vendido_por_peso": bool(p.vendido_por_peso),
            "codigo_barras": p.codigo_barras,
        })
    return resultado


# ─── Gestión de usuarios (solo gerentes) ────────────────────────────────────
@app.get("/api/usuarios")
def listar_usuarios(sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    return [
        {"id": u.id, "usuario": u.usuario, "rol": u.rol}
        for u in db.query(Usuario).order_by(Usuario.usuario).all()
    ]


@app.post("/api/usuarios", status_code=201)
def crear_usuario(data: CrearUsuario, sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    if db.query(Usuario).filter(Usuario.usuario == data.usuario).first():
        raise HTTPException(status_code=409, detail="Ese usuario ya existe")
    rol = data.rol if data.rol in ("gerente", "cajero") else "cajero"
    h, s = hash_password(data.password)
    u = Usuario(usuario=data.usuario, password_hash=h, salt=s, rol=rol)
    db.add(u)
    db.commit()
    db.refresh(u)
    return {"id": u.id, "usuario": u.usuario, "rol": u.rol}


@app.post("/api/usuarios/password")
def cambiar_password(data: CambiarPassword, sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    u = db.query(Usuario).filter(Usuario.usuario == data.usuario).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    h, s = hash_password(data.password_nuevo)
    u.password_hash = h
    u.salt = s
    db.commit()
    return {"ok": True, "usuario": u.usuario}


@app.delete("/api/usuarios/{usuario}", status_code=204)
def eliminar_usuario(usuario: str, sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    if usuario == sesion.usuario:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propio usuario")
    u = db.query(Usuario).filter(Usuario.usuario == usuario).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    # No permitir borrar el último gerente
    if u.rol == "gerente":
        gerentes = db.query(Usuario).filter(Usuario.rol == "gerente").count()
        if gerentes <= 1:
            raise HTTPException(status_code=400, detail="No puedes borrar el último gerente")
    db.delete(u)
    db.commit()


# ─── Dashboard: metricas de ventas ──────────────────────────────────────────

def _rango_utc_dash(desde):
    """Convierte una fecha ISO (con offset de horario local) a datetime UTC naive."""
    if not desde:
        return None
    try:
        d = datetime.fromisoformat(desde.replace("Z", "+00:00"))
        if d.tzinfo:
            d = d.astimezone(timezone.utc).replace(tzinfo=None)
        return d
    except ValueError:
        return None


def _costo_por_producto_dash(db, ids):
    if not ids:
        return {}
    rows = db.query(Producto.id, Producto.precio_costo).filter(Producto.id.in_(ids)).all()
    return {pid: (costo or 0) for pid, costo in rows}


def _calcular_periodo_dash(db, desde_dt, hasta_dt, restriccion=None):
    q = db.query(Venta)
    if desde_dt:
        q = q.filter(Venta.creado_en >= desde_dt)
    if hasta_dt:
        q = q.filter(Venta.creado_en < hasta_dt)
    if restriccion is not None:
        q = q.filter(Venta.sucursal == restriccion)
    ventas = q.all()

    ids = set()
    detalles = []
    for v in ventas:
        det = json.loads(v.detalle_json)
        detalles.append(det)
        for it in det:
            pid = it.get("producto_id")
            if pid is not None:
                ids.add(pid)
    costos = _costo_por_producto_dash(db, ids)

    total_vendido = round(sum(v.total for v in ventas), 2)
    total_costo = 0.0
    for det in detalles:
        for it in det:
            total_costo += costos.get(it.get("producto_id"), 0) * it.get("cantidad", 0)
    total_costo = round(total_costo, 2)
    ganancia = round(total_vendido - total_costo, 2)
    num_ventas = len(ventas)

    return {
        "num_ventas": num_ventas,
        "total_vendido": total_vendido,
        "total_costo": total_costo,
        "ganancia": ganancia,
        "margen_pct": round(ganancia / total_vendido * 100, 1) if total_vendido > 0 else 0,
        "ticket_promedio": round(total_vendido / num_ventas, 2) if num_ventas else 0,
    }


@app.get("/api/dashboard/resumen")
def dashboard_resumen(
    desde: Optional[str] = Query(None),
    periodo: str = Query("todo"),
    sesion: Sesion = Depends(requerir_gerente),
    db: Session = Depends(get_db),
):
    d = _rango_utc_dash(desde)
    restriccion = sucursal_restriccion(sesion)
    actual = _calcular_periodo_dash(db, d, None, restriccion)

    comparativo = None
    if d and periodo in ("hoy", "semana", "mes"):
        if periodo == "hoy":
            anterior_desde = d - timedelta(days=1)
            anterior_hasta = d
        elif periodo == "semana":
            anterior_desde = d - timedelta(days=7)
            anterior_hasta = d
        else:  # mes
            if d.month == 1:
                anterior_desde = d.replace(year=d.year - 1, month=12, day=1)
            else:
                anterior_desde = d.replace(month=d.month - 1, day=1)
            anterior_hasta = d

        previo = _calcular_periodo_dash(db, anterior_desde, anterior_hasta, restriccion)

        def variacion(actual_v, prev_v):
            if prev_v <= 0:
                return None
            return round((actual_v - prev_v) / prev_v * 100, 1)

        comparativo = {
            "total_vendido": previo["total_vendido"],
            "ganancia": previo["ganancia"],
            "variacion_total_pct": variacion(actual["total_vendido"], previo["total_vendido"]),
            "variacion_ganancia_pct": variacion(actual["ganancia"], previo["ganancia"]),
        }

    # Gastos del mismo periodo, para calcular la ganancia neta real
    gastos_q = db.query(Gasto)
    if d:
        gastos_q = gastos_q.filter(Gasto.fecha >= d)
    if restriccion is not None:
        gastos_q = gastos_q.filter(Gasto.sucursal == restriccion)
    gastos_total = round(sum(g.monto for g in gastos_q.all()), 2)
    actual["gastos"] = gastos_total
    actual["ganancia_neta"] = round(actual["ganancia"] - gastos_total, 2)

    # Devoluciones del periodo (registros con total negativo)
    dev_q = db.query(Venta).filter(Venta.total < 0)
    if d:
        dev_q = dev_q.filter(Venta.creado_en >= d)
    if restriccion is not None:
        dev_q = dev_q.filter(Venta.sucursal == restriccion)
    _devs = dev_q.all()
    actual["devoluciones_total"] = round(sum(abs(x.total) for x in _devs), 2)
    actual["devoluciones_num"] = len(_devs)

    actual["comparativo"] = comparativo
    return actual


@app.get("/api/dashboard/serie-diaria")
def dashboard_serie_diaria(
    dias: int = Query(14, ge=1, le=90),
    sesion: Sesion = Depends(requerir_gerente),
    db: Session = Depends(get_db),
):
    ahora = datetime.utcnow()
    desde = (ahora - timedelta(days=dias - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    ventas_q = db.query(Venta).filter(Venta.creado_en >= desde)
    restriccion = sucursal_restriccion(sesion)
    if restriccion is not None:
        ventas_q = ventas_q.filter(Venta.sucursal == restriccion)
    ventas = ventas_q.all()

    ids = set()
    for v in ventas:
        for it in json.loads(v.detalle_json):
            ids.add(it.get("producto_id"))
    costos = _costo_por_producto_dash(db, ids)

    dias_map = {}
    for i in range(dias):
        fecha = (desde + timedelta(days=i)).strftime("%Y-%m-%d")
        dias_map[fecha] = {"total": 0.0, "ganancia": 0.0, "num_ventas": 0}

    for v in ventas:
        fecha = v.creado_en.strftime("%Y-%m-%d")
        if fecha not in dias_map:
            continue
        costo_venta = sum(
            costos.get(it.get("producto_id"), 0) * it.get("cantidad", 0)
            for it in json.loads(v.detalle_json)
        )
        dias_map[fecha]["total"] += v.total
        dias_map[fecha]["ganancia"] += (v.total - costo_venta)
        dias_map[fecha]["num_ventas"] += 1

    serie = []
    for fecha in sorted(dias_map.keys()):
        dd = dias_map[fecha]
        serie.append({
            "fecha": fecha,
            "total": round(dd["total"], 2),
            "ganancia": round(dd["ganancia"], 2),
            "num_ventas": dd["num_ventas"],
        })
    return serie


@app.get("/api/dashboard/top-productos")
def dashboard_top_productos(
    desde: Optional[str] = Query(None),
    limit: int = Query(5, ge=1, le=20),
    sesion: Sesion = Depends(requerir_gerente),
    db: Session = Depends(get_db),
):
    d = _rango_utc_dash(desde)
    q = db.query(Venta)
    if d:
        q = q.filter(Venta.creado_en >= d)
    restriccion = sucursal_restriccion(sesion)
    if restriccion is not None:
        q = q.filter(Venta.sucursal == restriccion)
    ventas = q.all()

    acumulado = {}
    for v in ventas:
        for it in json.loads(v.detalle_json):
            pid = it.get("producto_id")
            if pid is None:
                continue
            if pid not in acumulado:
                acumulado[pid] = {"cantidad": 0.0, "total": 0.0, "nombre": it.get("nombre", "Producto")}
            acumulado[pid]["cantidad"] += it.get("cantidad", 0)
            acumulado[pid]["total"] += it.get("importe", 0)

    ids = list(acumulado.keys())
    info = {}
    if ids:
        rows = db.query(Producto.id, Producto.imagen_url, Producto.marca, Producto.precio_costo).filter(Producto.id.in_(ids)).all()
        info = {r[0]: {"imagen_url": r[1], "marca": r[2], "precio_costo": r[3] or 0} for r in rows}

    resultado = []
    for pid, dprod in acumulado.items():
        i = info.get(pid, {})
        ganancia = dprod["total"] - i.get("precio_costo", 0) * dprod["cantidad"]
        resultado.append({
            "producto_id": pid,
            "nombre": dprod["nombre"],
            "marca": i.get("marca"),
            "imagen_url": i.get("imagen_url"),
            "cantidad_vendida": round(dprod["cantidad"], 3),
            "total_vendido": round(dprod["total"], 2),
            "ganancia": round(ganancia, 2),
        })

    resultado.sort(key=lambda x: x["cantidad_vendida"], reverse=True)
    return resultado[:limit]


@app.get("/dashboard", response_class=FileResponse)
def dashboard_page():
    return FileResponse("static/dashboard.html")


# ─── Ventas en espera ───────────────────────────────────────────────────────
def _limpiar_pendientes_vencidas(db: Session, sucursal, hoy_inicio_str):
    """Elimina ventas en espera creadas antes de la medianoche de hoy (vencidas)."""
    if not hoy_inicio_str:
        return
    try:
        hoy_inicio = datetime.fromisoformat(hoy_inicio_str.replace("Z", "+00:00"))
        if hoy_inicio.tzinfo:
            hoy_inicio = hoy_inicio.astimezone(timezone.utc).replace(tzinfo=None)
    except ValueError:
        return
    q = db.query(VentaPendiente).filter(VentaPendiente.creado_en < hoy_inicio)
    if sucursal:
        q = q.filter(VentaPendiente.sucursal == sucursal)
    q.delete(synchronize_session=False)
    db.commit()


@app.post("/api/pos/pendientes")
def crear_pendiente(data: CrearVentaPendiente, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    _limpiar_pendientes_vencidas(db, sesion.sucursal, data.hoy_inicio)

    q_actual = db.query(VentaPendiente)
    if sesion.sucursal:
        q_actual = q_actual.filter(VentaPendiente.sucursal == sesion.sucursal)
    if q_actual.count() >= 2:
        raise HTTPException(
            status_code=400,
            detail="Ya hay 2 ventas en espera en esta sucursal. Cobra o elimina alguna antes de dejar otra en espera."
        )

    vp = VentaPendiente(
        sucursal=sesion.sucursal,
        operador=sesion.usuario,
        nota=data.nota,
        carrito_json=json.dumps(data.carrito, ensure_ascii=False),
        descuento_extra_pct=data.descuento_extra_pct,
        autorizado_por=data.autorizado_por,
    )
    db.add(vp)
    db.commit()
    db.refresh(vp)
    return {"id": vp.id}


@app.get("/api/pos/pendientes")
def listar_pendientes(hoy_inicio: Optional[str] = Query(None), sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    _limpiar_pendientes_vencidas(db, sesion.sucursal, hoy_inicio)
    q = db.query(VentaPendiente)
    if sesion.sucursal:
        q = q.filter(VentaPendiente.sucursal == sesion.sucursal)
    rows = q.order_by(VentaPendiente.creado_en.desc()).all()
    resultado = []
    for v in rows:
        carrito = json.loads(v.carrito_json)
        total = sum((it.get('precio', 0) or 0) * (it.get('cantidad', 0) or 0) for it in carrito)
        resultado.append({
            "id": v.id,
            "operador": v.operador,
            "nota": v.nota,
            "num_items": len(carrito),
            "total_aprox": round(total, 2),
            "creado_en": v.creado_en.isoformat() + "Z",
        })
    return resultado


@app.get("/api/pos/pendientes/{pid}")
def obtener_pendiente(pid: int, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    v = db.query(VentaPendiente).filter(VentaPendiente.id == pid).first()
    if not v:
        raise HTTPException(status_code=404, detail="No encontrada")
    return {
        "id": v.id,
        "carrito": json.loads(v.carrito_json),
        "descuento_extra_pct": v.descuento_extra_pct,
        "autorizado_por": v.autorizado_por,
        "nota": v.nota,
    }


@app.delete("/api/pos/pendientes/{pid}", status_code=204)
def borrar_pendiente(pid: int, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    v = db.query(VentaPendiente).filter(VentaPendiente.id == pid).first()
    if v:
        db.delete(v)
        db.commit()


# ─── Gastos del negocio ─────────────────────────────────────────────────────
def _rango_utc_gastos(desde, hasta):
    d = h = None
    if desde:
        try:
            d = datetime.fromisoformat(desde.replace("Z", "+00:00"))
            if d.tzinfo:
                d = d.astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError:
            pass
    if hasta:
        try:
            h = datetime.fromisoformat(hasta.replace("Z", "+00:00"))
            if h.tzinfo:
                h = h.astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError:
            pass
    return d, h


@app.post("/api/gastos", status_code=201)
def crear_gasto(data: CrearGasto, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    metodo = data.metodo_pago if data.metodo_pago in ("efectivo", "tarjeta", "transferencia") else "efectivo"
    g = Gasto(
        concepto=data.concepto.strip(),
        categoria=data.categoria.strip(),
        monto=data.monto,
        metodo_pago=metodo,
        sucursal=sesion.sucursal,
        operador=sesion.usuario,
        nota=data.nota,
        fecha=data.fecha or datetime.utcnow(),
    )
    db.add(g)
    db.commit()
    db.refresh(g)
    return {"id": g.id}


@app.get("/api/gastos")
def listar_gastos(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    sucursal: Optional[str] = Query(None),
    sesion: Sesion = Depends(requerir_gerente),
    db: Session = Depends(get_db),
):
    d, h = _rango_utc_gastos(desde, hasta)
    q = db.query(Gasto)
    if d:
        q = q.filter(Gasto.fecha >= d)
    if h:
        q = q.filter(Gasto.fecha <= h)
    if categoria:
        q = q.filter(Gasto.categoria == categoria)
    if sucursal:
        q = q.filter(Gasto.sucursal == sucursal)
    restriccion = sucursal_restriccion(sesion)
    if restriccion is not None:
        q = q.filter(Gasto.sucursal == restriccion)
    rows = q.order_by(Gasto.fecha.desc()).all()
    return [{
        "id": g.id,
        "concepto": g.concepto,
        "categoria": g.categoria,
        "monto": g.monto,
        "metodo_pago": g.metodo_pago,
        "sucursal": g.sucursal,
        "operador": g.operador,
        "nota": g.nota,
        "fecha": g.fecha.isoformat() + "Z",
    } for g in rows]


@app.get("/api/gastos/categorias")
def categorias_gastos(sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    rows = db.query(Gasto.categoria).distinct().order_by(Gasto.categoria).all()
    return [r[0] for r in rows if r[0]]


@app.get("/api/gastos/resumen")
def resumen_gastos(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    sesion: Sesion = Depends(requerir_gerente),
    db: Session = Depends(get_db),
):
    d, h = _rango_utc_gastos(desde, hasta)
    q = db.query(Gasto)
    if d:
        q = q.filter(Gasto.fecha >= d)
    if h:
        q = q.filter(Gasto.fecha <= h)
    restriccion = sucursal_restriccion(sesion)
    if restriccion is not None:
        q = q.filter(Gasto.sucursal == restriccion)
    gastos = q.all()
    total = round(sum(g.monto for g in gastos), 2)

    por_cat = {}
    for g in gastos:
        por_cat.setdefault(g.categoria, 0.0)
        por_cat[g.categoria] += g.monto
    desglose = sorted(
        [{"categoria": k, "total": round(v, 2)} for k, v in por_cat.items()],
        key=lambda x: x["total"], reverse=True
    )
    return {"total": total, "num_gastos": len(gastos), "por_categoria": desglose}


@app.delete("/api/gastos/{gasto_id}", status_code=204)
def borrar_gasto(gasto_id: int, sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    g = db.query(Gasto).filter(Gasto.id == gasto_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    db.delete(g)
    db.commit()


@app.get("/gastos", response_class=FileResponse)
def gastos_page():
    return FileResponse("static/gastos.html")


# ─── Clientes y ventas a credito ────────────────────────────────────────────
def normalizar_telefono(valor: Optional[str]) -> Optional[str]:
    """Deja el teléfono en 10 dígitos pelados, o lanza 400 si no es válido.

    Se aceptan las formas en que la gente lo escribe de verdad —"55 2767 1391",
    "(55) 2767-1391", "+52 55 2767 1391"— y se guarda siempre igual, para que
    dos veces el mismo número no queden como dos textos distintos. El campo es
    opcional: vacío se guarda como None.

    Un número mexicano son 10 dígitos (LADA + número) y ninguna LADA empieza
    con 0 ni con 1, así que eso también se rechaza.
    """
    if valor is None:
        return None
    digitos = "".join(c for c in valor if c.isdigit())
    if not digitos:
        # Vacío = el cliente no dio teléfono. Pero si escribió algo que no
        # tiene ni un dígito, es un error suyo: mejor decírselo que guardar
        # el campo en blanco a sus espaldas.
        if valor.strip():
            raise HTTPException(status_code=400, detail="El teléfono debe tener 10 dígitos (escribiste 0)")
        return None
    # Lada de país opcional: +52 (12 dígitos) o el viejo +521 de celular (13).
    if len(digitos) == 13 and digitos.startswith("521"):
        digitos = digitos[3:]
    elif len(digitos) == 12 and digitos.startswith("52"):
        digitos = digitos[2:]
    if len(digitos) != 10:
        raise HTTPException(
            status_code=400,
            detail=f"El teléfono debe tener 10 dígitos (escribiste {len(digitos)})",
        )
    if digitos[0] in "01":
        raise HTTPException(status_code=400, detail="El teléfono no puede empezar con 0 ni con 1")
    return digitos


def _saldo_cliente(db, cliente_id):
    ventas = db.query(Venta).filter(Venta.cliente_id == cliente_id, Venta.metodo_pago == "credito").all()
    suma_ventas = sum(v.total for v in ventas)
    pagos = db.query(PagoCredito).filter(PagoCredito.cliente_id == cliente_id).all()
    suma_pagos = sum(p.monto for p in pagos)
    return round(suma_ventas - suma_pagos, 2)


@app.post("/api/clientes", status_code=201)
def crear_cliente(data: CrearCliente, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    c = Cliente(
        nombre=data.nombre.strip(),
        telefono=normalizar_telefono(data.telefono),
        nota=data.nota,
        limite_credito=data.limite_credito,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"id": c.id, "nombre": c.nombre, "telefono": c.telefono, "limite_credito": c.limite_credito, "saldo": 0.0}


@app.get("/api/clientes")
def listar_clientes(q: Optional[str] = Query(None), sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    query = db.query(Cliente)
    if q:
        query = query.filter(Cliente.nombre.ilike(f"%{q}%"))
    clientes = query.order_by(Cliente.nombre).all()
    return [{
        "id": c.id,
        "nombre": c.nombre,
        "telefono": c.telefono,
        "limite_credito": c.limite_credito,
        "saldo": _saldo_cliente(db, c.id),
    } for c in clientes]


def _asignar_pagos_fifo(ventas, total_pagos):
    """Aplica los pagos a las ventas mas antiguas primero (FIFO)."""
    ventas_orden_asc = sorted(ventas, key=lambda v: v.creado_en)
    restante = total_pagos
    resultado = {}
    for v in ventas_orden_asc:
        if restante >= v.total:
            pagado = v.total
            restante = round(restante - v.total, 2)
        else:
            pagado = restante
            restante = 0.0
        resultado[v.id] = {"pagado": round(pagado, 2), "saldo": round(v.total - pagado, 2)}
    return resultado


# Declarado ANTES que /api/clientes/{cliente_id}: FastAPI resuelve las rutas en
# orden y "abonos-periodo" encajaría como cliente_id, dando un 422 de entero.
@app.get("/api/clientes/abonos-periodo")
def abonos_periodo(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    sucursal: Optional[str] = Query(None),
    sesion: Sesion = Depends(requerir_gerente),
    db: Session = Depends(get_db),
):
    d, h = _rango_utc_gastos(desde, hasta)
    q = db.query(PagoCredito)
    if d:
        q = q.filter(PagoCredito.creado_en >= d)
    if h:
        q = q.filter(PagoCredito.creado_en <= h)
    if sucursal:
        q = q.filter(PagoCredito.sucursal == sucursal)
    restriccion = sucursal_restriccion(sesion)
    if restriccion is not None:
        q = q.filter(PagoCredito.sucursal == restriccion)
    pagos = q.order_by(PagoCredito.creado_en.desc()).all()
    total = round(sum(p.monto for p in pagos), 2)

    cliente_ids = list(set(p.cliente_id for p in pagos))
    clientes_map = {}
    if cliente_ids:
        rows = db.query(Cliente.id, Cliente.nombre).filter(Cliente.id.in_(cliente_ids)).all()
        clientes_map = {r[0]: r[1] for r in rows}

    return {
        "total": total,
        "num_abonos": len(pagos),
        "abonos": [{
            "id": p.id,
            "cliente_nombre": clientes_map.get(p.cliente_id, "Cliente"),
            "monto": p.monto,
            "metodo_pago": p.metodo_pago,
            "operador": p.operador,
            "sucursal": p.sucursal,
            "fecha": p.creado_en.isoformat() + "Z",
            "nota": p.nota,
        } for p in pagos],
    }


@app.get("/api/clientes/{cliente_id}")
def detalle_cliente(cliente_id: int, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    ventas = db.query(Venta).filter(Venta.cliente_id == cliente_id, Venta.metodo_pago == "credito").order_by(Venta.creado_en.desc()).all()
    pagos = db.query(PagoCredito).filter(PagoCredito.cliente_id == cliente_id).order_by(PagoCredito.creado_en.desc()).all()
    total_pagos = sum(p.monto for p in pagos)
    asignacion = _asignar_pagos_fifo(ventas, total_pagos)
    return {
        "id": c.id,
        "nombre": c.nombre,
        "telefono": c.telefono,
        "nota": c.nota,
        "limite_credito": c.limite_credito,
        "saldo": _saldo_cliente(db, cliente_id),
        "ventas": [{
            "id": v.id, "total": v.total, "fecha": v.creado_en.isoformat() + "Z",
            "operador": v.operador, "sucursal": v.sucursal,
            "pagado": asignacion[v.id]["pagado"], "saldo": asignacion[v.id]["saldo"],
        } for v in ventas],
        "pagos": [{
            "id": p.id, "monto": p.monto, "metodo_pago": p.metodo_pago,
            "fecha": p.creado_en.isoformat() + "Z", "operador": p.operador, "nota": p.nota,
        } for p in pagos],
    }


@app.patch("/api/clientes/{cliente_id}")
def editar_cliente(cliente_id: int, data: CrearCliente, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    c.nombre = data.nombre.strip()
    c.telefono = normalizar_telefono(data.telefono)
    c.nota = data.nota
    c.limite_credito = data.limite_credito
    db.commit()
    return {"ok": True}


@app.delete("/api/clientes/{cliente_id}", status_code=204)
def eliminar_cliente(cliente_id: int, sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    saldo = _saldo_cliente(db, cliente_id)
    if saldo > 0:
        raise HTTPException(status_code=400, detail=f"No se puede eliminar: el cliente debe {saldo}")
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if c:
        db.delete(c)
        db.commit()


@app.post("/api/clientes/{cliente_id}/pagos", status_code=201)
def registrar_pago_credito(cliente_id: int, data: CrearPagoCredito, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    metodo = data.metodo_pago if data.metodo_pago in ("efectivo", "tarjeta", "transferencia") else "efectivo"
    p = PagoCredito(
        cliente_id=cliente_id,
        monto=data.monto,
        metodo_pago=metodo,
        operador=sesion.usuario,
        sucursal=sesion.sucursal,
        nota=data.nota,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return {
        "id": p.id,
        "saldo_restante": _saldo_cliente(db, cliente_id),
        "cliente_nombre": c.nombre,
        "monto": p.monto,
        "metodo_pago": p.metodo_pago,
        "operador": p.operador,
        "sucursal": p.sucursal,
        "nota": p.nota,
        "fecha": p.creado_en.isoformat() + "Z",
    }


@app.get("/api/reporte-completo")
def reporte_completo(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    sesion: Sesion = Depends(requerir_gerente),
    db: Session = Depends(get_db),
):
    d, h = _rango_utc_gastos(desde, hasta)
    restriccion = sucursal_restriccion(sesion)

    ventas_q = db.query(Venta)
    if d:
        ventas_q = ventas_q.filter(Venta.creado_en >= d)
    if h:
        ventas_q = ventas_q.filter(Venta.creado_en <= h)
    if restriccion is not None:
        ventas_q = ventas_q.filter(Venta.sucursal == restriccion)
    ventas = ventas_q.all()

    total_vendido = round(sum(v.total for v in ventas), 2)

    por_metodo = {}
    for v in ventas:
        m = v.metodo_pago or "efectivo"
        if m not in por_metodo:
            por_metodo[m] = {"cantidad": 0, "total": 0.0}
        por_metodo[m]["cantidad"] += 1
        por_metodo[m]["total"] += v.total
    desglose_metodos = sorted(
        [{"metodo": k, "cantidad": v["cantidad"], "total": round(v["total"], 2)} for k, v in por_metodo.items()],
        key=lambda x: x["total"], reverse=True
    )

    gastos_q = db.query(Gasto)
    if d:
        gastos_q = gastos_q.filter(Gasto.fecha >= d)
    if h:
        gastos_q = gastos_q.filter(Gasto.fecha <= h)
    if restriccion is not None:
        gastos_q = gastos_q.filter(Gasto.sucursal == restriccion)
    gastos_lista = gastos_q.all()
    gastos_total = round(sum(g.monto for g in gastos_lista), 2)

    ganancia_neta = round(total_vendido - gastos_total, 2)

    # ─── Cuadre de caja ──────────────────────────────────────────────────────
    # Lo que debería haber físicamente en el cajón al cerrar no es lo mismo que
    # "ventas en efectivo": hay que sumar los abonos que se cobraron en efectivo
    # y restar los gastos que se pagaron sacando dinero de ahí. Sin esas dos
    # piezas el reporte y el conteo del cajón nunca cuadran.
    pagos_q = db.query(PagoCredito)
    if d:
        pagos_q = pagos_q.filter(PagoCredito.creado_en >= d)
    if h:
        pagos_q = pagos_q.filter(PagoCredito.creado_en <= h)
    if restriccion is not None:
        pagos_q = pagos_q.filter(PagoCredito.sucursal == restriccion)
    abonos_lista = pagos_q.all()

    ventas_efectivo = round(sum(v.total for v in ventas if (v.metodo_pago or "efectivo") == "efectivo"), 2)
    abonos_efectivo = round(sum(p.monto for p in abonos_lista if (p.metodo_pago or "efectivo") == "efectivo"), 2)
    gastos_efectivo = round(sum(g.monto for g in gastos_lista if (g.metodo_pago or "efectivo") == "efectivo"), 2)

    cuadre_caja = {
        "ventas_efectivo": ventas_efectivo,
        "abonos_efectivo": abonos_efectivo,
        "gastos_efectivo": gastos_efectivo,
        "esperado_en_caja": round(ventas_efectivo + abonos_efectivo - gastos_efectivo, 2),
    }

    _devs = [x for x in ventas if x.total < 0]
    devoluciones_total = round(sum(abs(x.total) for x in _devs), 2)
    devoluciones_num = len(_devs)

    clientes = db.query(Cliente).all()
    detalle_clientes = []
    for c in clientes:
        saldo = _saldo_cliente(db, c.id)
        ventas_credito_periodo = [v for v in ventas if v.cliente_id == c.id and v.metodo_pago == "credito"]
        monto_ventas_credito = round(sum(v.total for v in ventas_credito_periodo), 2)
        pagos_q = db.query(PagoCredito).filter(PagoCredito.cliente_id == c.id)
        if d:
            pagos_q = pagos_q.filter(PagoCredito.creado_en >= d)
        if h:
            pagos_q = pagos_q.filter(PagoCredito.creado_en <= h)
        monto_pagos_periodo = round(sum(p.monto for p in pagos_q.all()), 2)

        if saldo > 0 or monto_ventas_credito > 0 or monto_pagos_periodo > 0:
            detalle_clientes.append({
                "cliente_id": c.id,
                "nombre": c.nombre,
                "saldo_actual": round(saldo, 2),
                "ventas_credito_periodo": monto_ventas_credito,
                "pagos_periodo": monto_pagos_periodo,
            })
    detalle_clientes = sorted(detalle_clientes, key=lambda x: x["saldo_actual"], reverse=True)

    return {
        "desde": desde,
        "hasta": hasta,
        "total_vendido": total_vendido,
        "num_ventas": len(ventas),
        "gastos": gastos_total,
        "num_gastos": len(gastos_lista),
        "devoluciones_total": devoluciones_total,
        "devoluciones_num": devoluciones_num,
        "ganancia_neta": ganancia_neta,
        "abonos_total": round(sum(p.monto for p in abonos_lista), 2),
        "num_abonos": len(abonos_lista),
        "cuadre_caja": cuadre_caja,
        "desglose_metodos_pago": desglose_metodos,
        "clientes_detalle": detalle_clientes,
        "total_por_cobrar": round(sum(c["saldo_actual"] for c in detalle_clientes if c["saldo_actual"] > 0), 2),
    }


@app.get("/api/clientes-resumen")
def resumen_clientes(sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    clientes = db.query(Cliente).all()
    total_por_cobrar = 0.0
    num_con_saldo = 0
    for c in clientes:
        saldo = _saldo_cliente(db, c.id)
        if saldo > 0:
            total_por_cobrar += saldo
            num_con_saldo += 1
    return {"total_por_cobrar": round(total_por_cobrar, 2), "num_clientes_con_saldo": num_con_saldo}


@app.get("/clientes", response_class=FileResponse)
def clientes_page():
    return FileResponse("static/clientes.html")

@app.get("/sucursales", response_class=FileResponse)
def sucursales_page():
    return FileResponse("static/sucursales.html")
