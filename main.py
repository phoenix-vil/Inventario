from fastapi import FastAPI, Depends, HTTPException, Query, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import datetime, timezone
import os
import json
import hashlib

from database import (get_db, init_db, Producto, Usuario, Venta, Sesion, Sucursal, StockSucursal,
                      verificar_password, hash_password, generar_token)
from schemas import (
    ProductoCreate, ProductoUpdate, ProductoOut, AjusteStock,
    AutorizarDescuento, RegistrarVenta, CrearUsuario, CambiarPassword,
    Login, LogoutReq, CrearSucursal, DescuentoCategoria, AsignarStockSucursal,
)

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
    return db.query(Sesion).filter(Sesion.token == token).first()


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


@app.post("/api/login")
def login(data: Login, db: Session = Depends(get_db)):
    u = db.query(Usuario).filter(Usuario.usuario == data.usuario).first()
    if not u or not verificar_password(data.password, u.password_hash, u.salt):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    token = generar_token()
    db.add(Sesion(token=token, usuario=u.usuario, rol=u.rol, sucursal=data.sucursal))
    db.commit()
    return {"token": token, "usuario": u.usuario, "rol": u.rol, "sucursal": data.sucursal}


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
    return {"usuario": s.usuario, "rol": s.rol, "sucursal": s.sucursal}


# ─── Sucursales ─────────────────────────────────────────────────────────────
@app.get("/api/sucursales")
def listar_sucursales(db: Session = Depends(get_db)):
    """Público (sin sesión) para que el login pueda mostrar la lista."""
    rows = db.query(Sucursal).order_by(Sucursal.nombre).all()
    return [{"id": s.id, "nombre": s.nombre} for s in rows]


@app.post("/api/sucursales", status_code=201)
def crear_sucursal(data: CrearSucursal, sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    nombre = data.nombre.strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")
    if db.query(Sucursal).filter(Sucursal.nombre == nombre).first():
        raise HTTPException(status_code=409, detail="Esa sucursal ya existe")
    s = Sucursal(nombre=nombre)
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"id": s.id, "nombre": s.nombre}


@app.delete("/api/sucursales/{sucursal_id}", status_code=204)
def eliminar_sucursal(sucursal_id: int, sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    s = db.query(Sucursal).filter(Sucursal.id == sucursal_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    if db.query(Sucursal).count() <= 1:
        raise HTTPException(status_code=400, detail="Debe quedar al menos una sucursal")
    db.delete(s)
    db.commit()


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


@app.get("/inventario-sucursales", response_class=FileResponse)
def inventario_sucursales_page():
    return FileResponse("static/inv_sucursales.html")


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
    estado: Optional[str] = Query(None, description="ok | bajo | agotado"),
    skip: int = 0,
    limit: int = 200,
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
    if estado == "agotado":
        query = query.filter(Producto.stock == 0)
    elif estado == "bajo":
        query = query.filter(Producto.stock > 0, Producto.stock <= Producto.stock_minimo)
    elif estado == "ok":
        query = query.filter(Producto.stock > Producto.stock_minimo)

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
def buscar_por_codigo(codigo: str, db: Session = Depends(get_db)):
    p = db.query(Producto).filter(Producto.codigo_barras == codigo).first()
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
    rows = db.query(StockSucursal).filter(StockSucursal.sucursal == sucursal).all()
    return {r.producto_id: r.cantidad for r in rows}


@app.post("/api/stock-sucursal")
def asignar_stock(data: AsignarStockSucursal, sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
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
        p = db.query(Producto).filter(Producto.id == item.producto_id).first()
        if not p:
            raise HTTPException(status_code=404, detail=f"Producto {item.producto_id} no existe")
        if p.stock < item.cantidad:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente de '{p.nombre}' (disponible: {p.stock})"
            )
        importe = round(item.precio_unitario * item.cantidad, 2)
        subtotal += importe
        productos_map[p.id] = p
        ahorro_item = 0.0
        if item.precio_original is not None and item.precio_original > item.precio_unitario:
            ahorro_item = round((item.precio_original - item.precio_unitario) * item.cantidad, 2)
            ahorro_productos += ahorro_item
        detalle.append({
            "producto_id": p.id,
            "nombre": p.nombre,
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
    metodo = data.metodo_pago if data.metodo_pago in ("efectivo", "tarjeta") else "efectivo"
    if metodo == "tarjeta":
        # En tarjeta no hay cambio; el pago es por el total exacto
        pago_con = total
        cambio = 0.0
    else:
        pago_con = data.pago_con
        cambio = round(pago_con - total, 2) if (pago_con is not None and pago_con >= total) else None

    # Descontar stock
    for item in data.items:
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
        tpv_referencia=data.tpv_referencia if metodo == "tarjeta" else None,
        tpv_autorizacion=data.tpv_autorizacion if metodo == "tarjeta" else None,
        tpv_terminal=data.tpv_terminal if metodo == "tarjeta" else None,
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
        "tpv_referencia": venta.tpv_referencia,
        "tpv_autorizacion": venta.tpv_autorizacion,
        "tpv_terminal": venta.tpv_terminal,
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
    if metodo_pago in ("efectivo", "tarjeta"):
        query = query.filter(Venta.metodo_pago == metodo_pago)
    if sucursal:
        query = query.filter(Venta.sucursal == sucursal)
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
    if metodo_pago in ("efectivo", "tarjeta"):
        query = query.filter(Venta.metodo_pago == metodo_pago)
    if sucursal:
        query = query.filter(Venta.sucursal == sucursal)
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
    rows = db.query(Venta.operador).distinct().all()
    return sorted([r[0] for r in rows if r[0]])


@app.get("/api/inventario/por-sucursal")
def inventario_por_sucursal(sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
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

    # Solo sucursales actualmente registradas (ignorar las borradas que aparecen en ventas)
    sucursales = sucursales_reg  # ya ordenadas

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


@app.get("/api/ventas/{venta_id}")
def obtener_venta(venta_id: int, sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    v = db.query(Venta).filter(Venta.id == venta_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    detalle = json.loads(v.detalle_json)
    ahorro_productos = round(sum(it.get("ahorro", 0) or 0 for it in detalle), 2)
    ahorro_descuento_extra = round(v.subtotal - v.total, 2)
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
        "tpv_referencia": v.tpv_referencia,
        "tpv_autorizacion": v.tpv_autorizacion,
        "tpv_terminal": v.tpv_terminal,
        "pago_con": v.pago_con,
        "cambio": v.cambio,
        "detalle": detalle,
    }


# ─── Buscar producto para POS (por nombre o código) ────────────────────────
@app.get("/api/pos/buscar")
def pos_buscar(q: str = Query(...), db: Session = Depends(get_db)):
    rows = db.query(Producto).filter(
        or_(
            Producto.nombre.ilike(f"%{q}%"),
            Producto.codigo_barras == q,
        )
    ).order_by(Producto.nombre).limit(20).all()
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
