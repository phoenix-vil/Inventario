from fastapi import FastAPI, Depends, HTTPException, Query, Header, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
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
from database import CorteCaja
from schemas import (
    ProductoCreate, ProductoUpdate, ProductoOut, AjusteStock,
    AutorizarDescuento, RegistrarVenta, CrearUsuario, CambiarPassword,
    Login, LogoutReq, CrearSucursal, DescuentoCategoria, AsignarStockSucursal, TrasladoStock)
from schemas import CrearTienda, ClasificarProductosMasivo, EditarSucursal
from schemas import CrearCliente, CrearPagoCredito, LiquidarCuenta
from schemas import CrearGasto
from schemas import CrearVentaPendiente
from schemas import RegistrarCotizacion
from schemas import RegistrarCorteCaja
from schemas import AccesoEnterprise

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
    suc = None
    if data.sucursal:
        suc = db.query(Sucursal).filter(Sucursal.nombre == data.sucursal).first()
        tienda_texto = suc.tiendas if suc else None

    # Una sucursal sin tienda asignada (Only Enterprises) no está restringida:
    # ve el negocio completo y administra sucursales, tiendas e inventario
    # comparado. Entrar por ahí exige permiso explícito, no basta ser gerente.
    if data.sucursal and not tienda_texto and not u.acceso_enterprise:
        raise HTTPException(
            status_code=403,
            detail=f"{u.usuario} no tiene acceso a {data.sucursal}. Entra por tu sucursal.",
        )

    # Algunas sucursales limitan quién puede entrar. Sin lista, entra cualquiera:
    # así las que ya existían siguen funcionando igual que siempre.
    if data.sucursal and suc is not None:
        permitidos = texto_a_usuarios(suc.usuarios_permitidos)
        if permitidos and u.usuario not in permitidos:
            raise HTTPException(
                status_code=403,
                detail=f"{u.usuario} no tiene acceso a {data.sucursal}.",
            )

    token = generar_token()
    db.add(Sesion(token=token, usuario=u.usuario, rol=u.rol, sucursal=data.sucursal, tienda=tienda_texto,
                  catalogo_exclusivo=bool(suc.catalogo_exclusivo) if suc else False))
    db.commit()
    return {"token": token, "usuario": u.usuario, "rol": u.rol, "sucursal": data.sucursal,
            "tienda": texto_a_tiendas(tienda_texto),
            "usa_niveles_precio": bool(suc.usa_niveles_precio) if suc else False,
            "catalogo_exclusivo": bool(suc.catalogo_exclusivo) if suc else False}


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
    suc = db.query(Sucursal).filter(Sucursal.nombre == s.sucursal).first() if s.sucursal else None
    return {"usuario": s.usuario, "rol": s.rol, "sucursal": s.sucursal, "tienda": texto_a_tiendas(s.tienda),
            "usa_niveles_precio": bool(suc.usa_niveles_precio) if suc else False,
            "catalogo_exclusivo": bool(suc.catalogo_exclusivo) if suc else False}


# ─── Sucursales ─────────────────────────────────────────────────────────────
def tiendas_a_texto(lista: Optional[List[str]]) -> Optional[str]:
    """[ "Only Reef", "Only Garden" ] -> "Only Reef,Only Garden". Vacío/None -> None."""
    if not lista:
        return None
    limpio = [t.strip() for t in lista if t and t.strip()]
    return ",".join(limpio) if limpio else None


def texto_a_tiendas(texto: Optional[str]) -> List[str]:
    return [t for t in (texto or "").split(",") if t]


def texto_a_usuarios(texto: Optional[str]) -> List[str]:
    """Misma convención que las tiendas: nombres separados por coma."""
    return [u.strip() for u in (texto or "").split(",") if u.strip()]


def validar_usuarios(lista: Optional[List[str]], db: Session):
    if not lista:
        return
    existentes = {u.usuario for u in db.query(Usuario).all()}
    desconocidos = [u for u in lista if u.strip() and u.strip() not in existentes]
    if desconocidos:
        raise HTTPException(status_code=400, detail="Usuarios desconocidos: " + ", ".join(desconocidos))


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
    Los productos sin tienda clasificada (None) normalmente siempre son
    visibles -es el catálogo general compartido entre Only Reef/Garden/
    Reptile/Pets-, salvo que la sucursal sea de catálogo exclusivo (un
    negocio sin relación con las demás, ej. El Zar del LED): ahí solo se ven
    los productos de su(s) propia(s) tienda(s)."""
    if sesion and sesion.tienda:
        tiendas_activas = texto_a_tiendas(sesion.tienda)
        if sesion.catalogo_exclusivo:
            query = query.filter(Producto.tienda.in_(tiendas_activas))
        else:
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


def requerir_sucursal_operativa(sesion: Sesion) -> str:
    """La sucursal física donde ocurre una operación de piso: vender, devolver,
    cancelar. Only Enterprises no es una sucursal —no tiene caja ni inventario
    propios que descontar—, se usa administrativamente para ver y comparar
    las demás. `sesion.sucursal` para Only Enterprises SÍ trae el texto
    "Only Enterprises" (no es None), así que un `if not sesion.sucursal` no
    la detecta: hay que pasar por sucursal_restriccion(), que es quien de
    verdad distingue una sucursal operativa de una sesión sin restricción."""
    restriccion = sucursal_restriccion(sesion)
    if restriccion is None:
        raise HTTPException(
            status_code=403,
            detail="Only Enterprises no puede hacer ventas ni devoluciones; entra desde una sucursal.",
        )
    return restriccion


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
        s.nombre for s in db.query(Sucursal).order_by(Sucursal.orden, Sucursal.nombre).all()
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
def listar_sucursales(sesion: Optional[Sesion] = Depends(sesion_opcional), db: Session = Depends(get_db)):
    """Público (sin sesión) para que el login pueda mostrar la lista.

    Quién puede entrar en cada sucursal solo se revela a una sesión de Only
    Enterprises, que es quien administra eso; para el resto sería decirle a
    cualquiera qué usuarios existen y dónde entran."""
    administra = sesion is not None and sesion.rol == "gerente" and not sesion.tienda
    rows = db.query(Sucursal).order_by(Sucursal.orden, Sucursal.nombre).all()
    salida = []
    for s in rows:
        item = {"id": s.id, "nombre": s.nombre, "tiendas": texto_a_tiendas(s.tiendas)}
        if administra:
            item["usuarios_permitidos"] = texto_a_usuarios(s.usuarios_permitidos)
        salida.append(item)
    return salida


@app.post("/api/sucursales", status_code=201)
def crear_sucursal(data: CrearSucursal, sesion: Sesion = Depends(requerir_enterprise), db: Session = Depends(get_db)):
    nombre = data.nombre.strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")
    if db.query(Sucursal).filter(Sucursal.nombre == nombre).first():
        raise HTTPException(status_code=409, detail="Esa sucursal ya existe")
    validar_tiendas(data.tiendas, db)
    validar_usuarios(data.usuarios_permitidos, db)
    s = Sucursal(
        nombre=nombre,
        tiendas=tiendas_a_texto(data.tiendas),
        usuarios_permitidos=tiendas_a_texto(data.usuarios_permitidos),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"id": s.id, "nombre": s.nombre, "tiendas": texto_a_tiendas(s.tiendas),
            "usuarios_permitidos": texto_a_usuarios(s.usuarios_permitidos)}


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
    if "usuarios_permitidos" in cambios:
        validar_usuarios(cambios["usuarios_permitidos"], db)
        s.usuarios_permitidos = tiendas_a_texto(cambios["usuarios_permitidos"])
    db.commit()
    db.refresh(s)
    return {"id": s.id, "nombre": s.nombre, "tiendas": texto_a_tiendas(s.tiendas),
            "usuarios_permitidos": texto_a_usuarios(s.usuarios_permitidos)}


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
def resumen(sesion: Optional[Sesion] = Depends(sesion_opcional), db: Session = Depends(get_db)):
    # Mismo alcance que /api/productos: sin esto, el resumen contaba TODO el
    # catálogo sin importar la sesión, así que una sucursal de catálogo
    # exclusivo (El Zar del LED) veía el total de todo el negocio arriba y
    # solo lo suyo en la lista de abajo -contradictorio-.
    base = aplicar_filtro_tienda(db.query(Producto), sesion)
    total = base.count()
    valor = base.with_entities(func.sum(Producto.precio_venta * Producto.stock)).scalar() or 0
    stock_bajo = base.filter(
        Producto.stock > 0, Producto.stock <= Producto.stock_minimo
    ).count()
    agotados = base.filter(Producto.stock == 0).count()
    categorias = base.with_entities(func.count(Producto.categoria.distinct())).scalar()
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
                Producto.clave.ilike(f"%{q}%"),
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
        raise HTTPException(status_code=409, detail="Ya existe un producto con ese código de barras o esa clave")
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
        raise HTTPException(status_code=409, detail="Ya existe un producto con ese código de barras o esa clave")
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
def categorias(sesion: Optional[Sesion] = Depends(sesion_opcional), db: Session = Depends(get_db)):
    query = aplicar_filtro_tienda(db.query(Producto.categoria).distinct(), sesion)
    rows = query.order_by(Producto.categoria).all()
    return [r[0] for r in rows]


# ─── Marcas disponibles ────────────────────────────────────────────────────
@app.get("/api/marcas")
def marcas(sesion: Optional[Sesion] = Depends(sesion_opcional), db: Session = Depends(get_db)):
    query = aplicar_filtro_tienda(
        db.query(Producto.marca).filter(Producto.marca != None).distinct(), sesion
    )
    rows = query.order_by(Producto.marca).all()
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
            "clave": p.clave,
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
    sucursal_venta = requerir_sucursal_operativa(sesion)
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

    # Los pedidos en dos pagos son exclusivos de El Zar del LED. La interfaz
    # ya oculta esos botones en las demás tiendas, pero la API también debe
    # impedir que se creen manipulando la petición desde el navegador.
    if data.es_anticipo and "El Zar del LED" not in texto_a_tiendas(sesion.tienda):
        raise HTTPException(status_code=403, detail="Los anticipos solo están disponibles en El Zar del LED")

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
        sucursal=sucursal_venta,
        metodo_pago=metodo,
        cliente_id=data.cliente_id if metodo == "credito" else None,
        tpv_referencia=data.tpv_referencia if metodo == "tarjeta" else None,
        tpv_autorizacion=data.tpv_autorizacion if metodo == "tarjeta" else None,
        tpv_terminal=data.tpv_terminal if metodo == "tarjeta" else None,
        transferencia_referencia=data.transferencia_referencia if metodo == "transferencia" else None,
        detalle_json=json.dumps(detalle, ensure_ascii=False),
        pago_con=pago_con,
        cambio=cambio,
        es_anticipo=data.es_anticipo if metodo == "credito" else False,
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
        "es_anticipo": venta.es_anticipo,
        "tpv_referencia": venta.tpv_referencia,
        "tpv_autorizacion": venta.tpv_autorizacion,
        "tpv_terminal": venta.tpv_terminal,
        "transferencia_referencia": venta.transferencia_referencia,
        "autorizado_por": data.autorizado_por,
        "operador": sesion.usuario,
        "sucursal": sucursal_venta,
        "detalle": detalle,
        "fecha": venta.creado_en.isoformat() + "Z",
    }


# ─── Historial de ventas ───────────────────────────────────────────────────
def _fecha_contable_venta(v: Venta):
    """Fecha en que una operación cuenta como venta.

    Una venta normal cuenta al registrarse. Un pedido con anticipo cuenta hasta
    quedar totalmente liquidado; creado_en sigue indicando cuándo se pidió."""
    return v.liquidado_en if v.es_anticipo else v.creado_en


def _acotar_ventas_contabilizadas(query, desde=None, hasta=None):
    """Excluye pedidos pendientes y filtra cada venta por su fecha contable."""
    normal = or_(Venta.es_anticipo == False, Venta.es_anticipo.is_(None))
    pedido_liquidado = and_(Venta.es_anticipo == True, Venta.liquidado_en.is_not(None))
    query = query.filter(or_(normal, pedido_liquidado))
    if desde:
        query = query.filter(or_(
            and_(normal, Venta.creado_en >= desde),
            and_(Venta.es_anticipo == True, Venta.liquidado_en >= desde),
        ))
    if hasta:
        query = query.filter(or_(
            and_(normal, Venta.creado_en <= hasta),
            and_(Venta.es_anticipo == True, Venta.liquidado_en <= hasta),
        ))
    return query


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
    d = None
    h = None
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
    query = _acotar_ventas_contabilizadas(query, d, h)
    if operador:
        query = query.filter(Venta.operador == operador)
    if metodo_pago in ("efectivo", "tarjeta", "credito", "transferencia"):
        query = query.filter(Venta.metodo_pago == metodo_pago)
    if sucursal:
        query = query.filter(Venta.sucursal == sucursal)
    restriccion = sucursal_restriccion(sesion)
    if restriccion is not None:
        query = query.filter(Venta.sucursal == restriccion)
    ventas = sorted(query.all(), key=_fecha_contable_venta, reverse=True)[:limit]
    return [
        {
            "id": v.id,
            "fecha": _fecha_contable_venta(v).isoformat() + "Z",
            "fecha_pedido": v.creado_en.isoformat() + "Z" if v.es_anticipo else None,
            "fecha_liquidacion": v.liquidado_en.isoformat() + "Z" if v.liquidado_en else None,
            "es_anticipo": bool(v.es_anticipo),
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
    d = None
    h = None
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
    query = _acotar_ventas_contabilizadas(query, d, h)
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
        elif (v.metodo_pago or "efectivo") == "efectivo":
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
    sucursales_reg = [s.nombre for s in db.query(Sucursal).order_by(Sucursal.orden, Sucursal.nombre).all()]

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
            "clave": p.clave,
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
        visibles = [s.nombre for s in db.query(Sucursal).order_by(Sucursal.orden, Sucursal.nombre).all()]

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
            "clave": p.clave,
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
    requerir_sucursal_operativa(sesion)
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
    requerir_sucursal_operativa(sesion)
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


def _cliente_de(db: Session, cliente_id: Optional[int]) -> Optional[Cliente]:
    return db.query(Cliente).filter(Cliente.id == cliente_id).first() if cliente_id else None


def calcular_precio_final(p: Producto, cliente: Optional[Cliente] = None, nivel_override: Optional[int] = None) -> float:
    """Precio que se le cobra a este cliente por este producto.

    Un precio de mayoreo pactado manda sobre la promoción del momento: si el
    cliente tiene nivel y el producto lo trae capturado, ese es el precio.
    nivel_override manda sobre todo: es elegir el precio a mano para esta
    venta (El Zar del LED), sin tocar el nivel guardado del cliente."""
    de_mayoreo = precio_por_nivel(p, nivel_override) if nivel_override else precio_para_cliente(p, cliente)
    if de_mayoreo is not None:
        return de_mayoreo
    if p.descuento_pct and p.descuento_pct > 0:
        ahora = datetime.utcnow()
        desde_ok = (p.descuento_desde is None) or (p.descuento_desde <= ahora)
        hasta_ok = (p.descuento_hasta is None) or (p.descuento_hasta >= ahora)
        if desde_ok and hasta_ok:
            return round(p.precio_venta * (1 - p.descuento_pct / 100), 2)
    return p.precio_venta


@app.get("/api/pos/producto/{producto_id}")
def pos_producto(
    producto_id: int,
    cliente_id: Optional[int] = Query(None),
    sesion: Sesion = Depends(requerir_sesion),
    db: Session = Depends(get_db),
):
    query = aplicar_filtro_tienda(db.query(Producto).filter(Producto.id == producto_id), sesion)
    p = query.first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    cliente = _cliente_de(db, cliente_id)
    precio_final = calcular_precio_final(p, cliente)
    return {
        "nivel_precio": cliente.nivel_precio if cliente else None,
        "id": p.id,
        "nombre": p.nombre,
        "categoria": p.categoria,
        "precio_venta": p.precio_venta,
        "precio_final": precio_final,
        "stock": p.stock,
        "unidad": p.unidad,
        "vendido_por_peso": bool(p.vendido_por_peso),
        "codigo_barras": p.codigo_barras,
        "clave": p.clave,
    }


@app.get("/api/pos/buscar")
def pos_buscar(
    q: str = Query(...),
    cliente_id: Optional[int] = Query(None),
    sesion: Optional[Sesion] = Depends(sesion_opcional),
    db: Session = Depends(get_db),
):
    query = db.query(Producto).filter(
        or_(
            Producto.nombre.ilike(f"%{q}%"),
            Producto.codigo_barras == q,
            Producto.clave.ilike(f"%{q}%"),
        )
    )
    # Antes el límite era 20: con nombres largos y varias variantes del mismo
    # producto (tallas, colores, %s, etc.) una sola palabra podía tener más
    # de 20 coincidencias y las de más abajo (alfabéticamente) no aparecían
    # nunca en la búsqueda, aunque sí coincidieran. 100 es margen de sobra
    # para cualquier búsqueda razonable sin mandar el catálogo completo.
    rows = aplicar_filtro_tienda(query, sesion).order_by(Producto.nombre).limit(100).all()
    cliente = _cliente_de(db, cliente_id)
    resultado = []
    for p in rows:
        precio_final = calcular_precio_final(p, cliente)
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
            "clave": p.clave,
        })
    return resultado


@app.get("/api/pos/mas-vendidos")
def pos_mas_vendidos(
    cliente_id: Optional[int] = Query(None),
    dias: int = Query(30, ge=1, le=365),
    limit: int = Query(12, ge=1, le=30),
    sesion: Optional[Sesion] = Depends(sesion_opcional),
    db: Session = Depends(get_db),
):
    """Los productos más vendidos de esta sucursal en los últimos `dias`, en
    el mismo formato que /api/pos/buscar —para que el buscador de pagos.html
    pueda mostrarlos con el mismo renderResultados()/agregar() de siempre,
    sin código aparte—. Se usan cuando el buscador está vacío, en vez de
    dejar esa columna en blanco."""
    desde = datetime.utcnow() - timedelta(days=dias)
    q = db.query(Venta).filter(Venta.creado_en >= desde, Venta.total > 0)
    restriccion = sucursal_restriccion(sesion)
    if restriccion is not None:
        q = q.filter(Venta.sucursal == restriccion)

    acumulado = {}
    for v in q.all():
        for it in json.loads(v.detalle_json):
            pid = it.get("producto_id")
            if pid is None:  # los artículos personalizados no tienen inventario que sugerir
                continue
            acumulado[pid] = acumulado.get(pid, 0) + (it.get("cantidad") or 0)

    if not acumulado:
        return []

    top_ids = sorted(acumulado, key=lambda pid: acumulado[pid], reverse=True)[:limit]
    query = aplicar_filtro_tienda(db.query(Producto).filter(Producto.id.in_(top_ids)), sesion)
    por_id = {p.id: p for p in query.all()}
    cliente = _cliente_de(db, cliente_id)

    resultado = []
    for pid in top_ids:  # conserva el orden de más vendido primero
        p = por_id.get(pid)
        if not p:
            continue
        resultado.append({
            "id": p.id,
            "nombre": p.nombre,
            "categoria": p.categoria,
            "precio_venta": p.precio_venta,
            "precio_final": calcular_precio_final(p, cliente),
            "stock": p.stock,
            "unidad": p.unidad,
            "vendido_por_peso": bool(p.vendido_por_peso),
            "codigo_barras": p.codigo_barras,
            "clave": p.clave,
        })
    return resultado


@app.post("/api/pos/precios-cliente")
def precios_para_cliente(data: dict = Body(...), sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    """Precios que le tocan a un cliente para los productos que ya están en el
    carrito. Se usa al elegir o quitar el cliente a media venta, para no tener
    que volver a capturar todo.

    nivel_override (El Zar del LED): elegir el precio 1/2/3 a mano para esta
    venta nada más, sin importar (ni tocar) el nivel guardado del cliente."""
    cliente = _cliente_de(db, data.get("cliente_id"))
    nivel_override = data.get("nivel_override")
    if nivel_override not in (1, 2, 3):
        nivel_override = None
    ids = [i for i in (data.get("producto_ids") or []) if isinstance(i, int)]
    nivel_mostrado = nivel_override or (cliente.nivel_precio if cliente else None)
    if not ids:
        return {"nivel_precio": nivel_mostrado, "precios": {}}
    productos = db.query(Producto).filter(Producto.id.in_(ids)).all()
    return {
        "nivel_precio": nivel_mostrado,
        "precios": {str(p.id): calcular_precio_final(p, cliente, nivel_override) for p in productos},
    }


# ─── Gestión de usuarios (solo gerentes) ────────────────────────────────────
@app.get("/api/usuarios")
def listar_usuarios(sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    return [
        {"id": u.id, "usuario": u.usuario, "rol": u.rol,
         "acceso_enterprise": bool(u.acceso_enterprise)}
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


@app.post("/api/usuarios/acceso-enterprise")
def cambiar_acceso_enterprise(
    data: AccesoEnterprise,
    sesion: Sesion = Depends(requerir_enterprise),
    db: Session = Depends(get_db),
):
    """Concede o quita el acceso a las sucursales sin tienda. Solo puede hacerlo
    quien ya entró por una de ellas: si no, un gerente de sucursal podría
    dárselo a sí mismo."""
    u = db.query(Usuario).filter(Usuario.usuario == data.usuario).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if u.usuario == sesion.usuario and not data.permitir:
        raise HTTPException(status_code=400, detail="No puedes quitarte a ti mismo el acceso")
    u.acceso_enterprise = bool(data.permitir)
    db.commit()
    return {"usuario": u.usuario, "acceso_enterprise": bool(u.acceso_enterprise)}


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
    limite = hasta_dt - timedelta(microseconds=1) if hasta_dt else None
    q = _acotar_ventas_contabilizadas(db.query(Venta), desde_dt, limite)
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
    ventas_q = _acotar_ventas_contabilizadas(db.query(Venta), desde)
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
        fecha = _fecha_contable_venta(v).strftime("%Y-%m-%d")
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
    q = _acotar_ventas_contabilizadas(db.query(Venta), d)
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


# ─── Corte de caja ──────────────────────────────────────────────────────────
def _sucursal_de_corte(sesion: Sesion) -> str:
    """La caja que se cierra es la de la sesión. Only Enterprises no tiene caja
    propia: no vende, así que no hay nada que cortar desde ahí."""
    if not sesion.sucursal:
        raise HTTPException(status_code=400, detail="Esta sesión no tiene una sucursal con caja")
    return sesion.sucursal


def _calcular_corte(db: Session, sucursal: str):
    """Movimientos de efectivo desde el último corte de esa sucursal hasta ahora.
    Tomar como inicio el corte anterior —y no el día natural— evita que se
    pierdan o se dupliquen movimientos si un día no se cierra la caja."""
    anterior = (
        db.query(CorteCaja)
        .filter(CorteCaja.sucursal == sucursal)
        .order_by(CorteCaja.creado_en.desc())
        .first()
    )
    desde = anterior.creado_en if anterior else None
    # Lo que quedó en el cajón: lo contado menos lo que se retiró al cerrar
    saldo_inicial = round((anterior.contado or 0) - (anterior.retirado or 0), 2) if anterior else 0.0

    ventas_q = db.query(Venta).filter(Venta.sucursal == sucursal, Venta.metodo_pago == "efectivo")
    gastos_q = db.query(Gasto).filter(Gasto.sucursal == sucursal, Gasto.metodo_pago == "efectivo")
    abonos_q = db.query(PagoCredito).filter(PagoCredito.sucursal == sucursal, PagoCredito.metodo_pago == "efectivo")
    if desde:
        ventas_q = ventas_q.filter(Venta.creado_en > desde)
        gastos_q = gastos_q.filter(Gasto.fecha > desde)
        abonos_q = abonos_q.filter(PagoCredito.creado_en > desde)

    ventas_efectivo = round(sum(v.total for v in ventas_q.all()), 2)
    gastos_efectivo = round(sum(g.monto for g in gastos_q.all()), 2)
    abonos_efectivo = round(sum(p.monto for p in abonos_q.all()), 2)
    esperado = round(saldo_inicial + ventas_efectivo + abonos_efectivo - gastos_efectivo, 2)

    return {
        "sucursal": sucursal,
        "desde": desde.isoformat() + "Z" if desde else None,
        "corte_anterior_id": anterior.id if anterior else None,
        "saldo_inicial": saldo_inicial,
        "ventas_efectivo": ventas_efectivo,
        "abonos_efectivo": abonos_efectivo,
        "gastos_efectivo": gastos_efectivo,
        "esperado": esperado,
    }


@app.get("/api/corte-caja/preview")
def preview_corte(sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    """Qué se cerraría si se hiciera el corte ahora mismo. Un cajero también
    puede cerrar su caja, no solo un gerente."""
    return _calcular_corte(db, _sucursal_de_corte(sesion))


@app.post("/api/corte-caja", status_code=201)
def registrar_corte(data: RegistrarCorteCaja, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    sucursal = _sucursal_de_corte(sesion)
    calc = _calcular_corte(db, sucursal)

    if data.retirado > data.contado:
        raise HTTPException(status_code=400, detail="No puedes retirar más de lo que contaste")

    corte = CorteCaja(
        sucursal=sucursal,
        operador=sesion.usuario,
        desde=datetime.fromisoformat(calc["desde"][:-1]) if calc["desde"] else None,
        saldo_inicial=calc["saldo_inicial"],
        ventas_efectivo=calc["ventas_efectivo"],
        abonos_efectivo=calc["abonos_efectivo"],
        gastos_efectivo=calc["gastos_efectivo"],
        esperado=calc["esperado"],
        contado=round(data.contado, 2),
        diferencia=round(data.contado - calc["esperado"], 2),
        retirado=round(data.retirado, 2),
        nota=(data.nota or "").strip() or None,
    )
    db.add(corte)
    db.commit()
    db.refresh(corte)
    return {
        "id": corte.id,
        "sucursal": corte.sucursal,
        "operador": corte.operador,
        "fecha": corte.creado_en.isoformat() + "Z",
        "saldo_inicial": corte.saldo_inicial,
        "ventas_efectivo": corte.ventas_efectivo,
        "abonos_efectivo": corte.abonos_efectivo,
        "gastos_efectivo": corte.gastos_efectivo,
        "esperado": corte.esperado,
        "contado": corte.contado,
        "diferencia": corte.diferencia,
        "retirado": corte.retirado,
        "queda_en_caja": round(corte.contado - corte.retirado, 2),
        "nota": corte.nota,
    }


@app.get("/api/cortes-caja")
def listar_cortes(
    limit: int = Query(60, le=365),
    sesion: Sesion = Depends(requerir_sesion),
    db: Session = Depends(get_db),
):
    q = db.query(CorteCaja)
    restriccion = sucursal_restriccion(sesion)
    if restriccion is not None:
        q = q.filter(CorteCaja.sucursal == restriccion)
    cortes = q.order_by(CorteCaja.creado_en.desc()).limit(limit).all()
    return [{
        "id": c.id,
        "sucursal": c.sucursal,
        "operador": c.operador,
        "fecha": c.creado_en.isoformat() + "Z",
        "saldo_inicial": c.saldo_inicial,
        "ventas_efectivo": c.ventas_efectivo,
        "abonos_efectivo": c.abonos_efectivo,
        "gastos_efectivo": c.gastos_efectivo,
        "esperado": c.esperado,
        "contado": c.contado,
        "diferencia": c.diferencia,
        "retirado": c.retirado,
        "queda_en_caja": round((c.contado or 0) - (c.retirado or 0), 2),
        "nota": c.nota,
    } for c in cortes]


def _rango_dia_local(fecha: Optional[str], tz_min: int):
    """Rango [desde, hasta) en UTC naive para un día en hora local.
    tz_min es el getTimezoneOffset() del navegador (360 para México)."""
    if fecha:
        try:
            dia = datetime.strptime(fecha[:10], "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Fecha inválida, se espera AAAA-MM-DD")
    else:
        dia = (datetime.utcnow() - timedelta(minutes=tz_min)).replace(
            hour=0, minute=0, second=0, microsecond=0)
    inicio = dia.replace(hour=0, minute=0, second=0, microsecond=0)
    return (inicio + timedelta(minutes=tz_min),
            inicio + timedelta(days=1) + timedelta(minutes=tz_min),
            inicio.date().isoformat())


def _csv_linea(campos) -> str:
    """Una fila de CSV. Entrecomilla solo lo que lo necesita y duplica las
    comillas internas, que es como lo esperan Excel y Numbers."""
    salida = []
    for c in campos:
        t = "" if c is None else str(c)
        if any(ch in t for ch in (',', '"', '\n', '\r')):
            t = '"' + t.replace('"', '""') + '"'
        salida.append(t)
    return ",".join(salida)


@app.get("/api/corte-caja/reporte")
def reporte_del_dia(
    fecha: Optional[str] = Query(None, description="Día a reportar, AAAA-MM-DD en hora local (o inicio del rango, si se manda 'hasta')"),
    hasta: Optional[str] = Query(None, description="Fin del rango, AAAA-MM-DD en hora local. Si no se manda, el reporte es de un solo día (fecha)."),
    tz_offset_min: int = Query(360, description="getTimezoneOffset() del navegador"),
    formato: str = Query("json", description="json para armar el PDF, csv para hoja de cálculo"),
    sesion: Sesion = Depends(requerir_sesion),
    db: Session = Depends(get_db),
):
    """Todo el periodo: ventas, gastos, abonos, los cortes de caja y cuánto
    quedó en el cajón. En JSON alimenta el PDF que arma la pantalla de corte de
    caja; en CSV se abre en Excel o Numbers. Los dos salen de los mismos datos.

    Sin 'hasta', es el reporte de un solo día de siempre. Con 'hasta', junta
    varios días —reutiliza _rango_dia_local dos veces: una para el inicio del
    día de 'fecha' y otra para el fin del día de 'hasta'—.

    Un cajero también puede cerrar su caja, pero solo ve el reporte de un
    solo día (nunca por rango) y reducido: cuadre de efectivo y los cortes,
    sin ganancia, sin desglose de métodos de pago ni el detalle de cada
    venta/gasto/abono —eso es información de dueño, no de cajero—."""
    reducido = sesion.rol != "gerente"
    desde, hasta_dt, desde_iso = _rango_dia_local(fecha, tz_offset_min)
    es_rango = bool(hasta) and hasta[:10] != desde_iso
    if es_rango and reducido:
        raise HTTPException(status_code=403, detail="El reporte por rango de fechas es solo para gerentes")
    if es_rango:
        _, hasta_dt, hasta_iso = _rango_dia_local(hasta, tz_offset_min)
        if hasta_dt <= desde:
            raise HTTPException(status_code=400, detail="La fecha final debe ser posterior a la inicial")
        dia_iso = f"{desde_iso}_a_{hasta_iso}"
        etiqueta_periodo = f"Del {desde_iso} al {hasta_iso}"
    else:
        dia_iso = desde_iso
        etiqueta_periodo = desde_iso
    periodo_txt = "este periodo" if es_rango else "este día"
    restriccion = sucursal_restriccion(sesion)
    ambito = restriccion or "Todas las sucursales"

    def acotar(q, campo):
        q = q.filter(campo >= desde, campo < hasta_dt)
        return q

    ventas_q = _acotar_ventas_contabilizadas(
        db.query(Venta), desde, hasta_dt - timedelta(microseconds=1))
    gastos_q = acotar(db.query(Gasto), Gasto.fecha)
    abonos_q = acotar(db.query(PagoCredito), PagoCredito.creado_en)
    cortes_q = acotar(db.query(CorteCaja), CorteCaja.creado_en)
    if restriccion is not None:
        ventas_q = ventas_q.filter(Venta.sucursal == restriccion)
        gastos_q = gastos_q.filter(Gasto.sucursal == restriccion)
        abonos_q = abonos_q.filter(PagoCredito.sucursal == restriccion)
        cortes_q = cortes_q.filter(CorteCaja.sucursal == restriccion)

    ventas = sorted(ventas_q.all(), key=_fecha_contable_venta)
    gastos = gastos_q.order_by(Gasto.fecha).all()
    abonos = abonos_q.order_by(PagoCredito.creado_en).all()
    cortes = cortes_q.order_by(CorteCaja.creado_en).all()

    # Mismas cifras que el reporte general: un solo criterio para todo
    bloque = _bloque_reporte(ventas, gastos, abonos)

    nombres_cliente = {}
    ids = {v.cliente_id for v in ventas if v.cliente_id} | {p.cliente_id for p in abonos if p.cliente_id}
    if ids:
        nombres_cliente = {c.id: c.nombre for c in db.query(Cliente).filter(Cliente.id.in_(ids)).all()}

    def hora(dt):
        return (dt - timedelta(minutes=tz_offset_min)).strftime("%H:%M") if dt else ""

    # Lo que queda en el cajón es el último corte de CADA sucursal, no el último
    # de la lista: en el consolidado de Only Enterprises hay varias cajas y
    # quedarse con una sola deja fuera el fondo de las demás.
    ultimo_de = {}
    for c in cortes:                       # ya vienen ordenados por fecha
        ultimo_de[c.sucursal] = c
    queda_por_sucursal = {s: round((c.contado or 0) - (c.retirado or 0), 2)
                          for s, c in ultimo_de.items()}

    # Sin cortes hoy, lo que se puede decir del cajón depende de si alguna vez
    # se cortó: sin un corte previo, _calcular_corte suma todo el histórico y
    # presentarlo como "fondo del día" sería engañoso.
    caja_ahora = None
    if not cortes and restriccion is not None:
        calc = _calcular_corte(db, restriccion)
        caja_ahora = {"monto": calc["esperado"], "hubo_corte_antes": bool(calc["desde"]),
                      "desde": calc["desde"]}

    datos = {
        "fecha": dia_iso,
        "es_rango": es_rango,
        "etiqueta_periodo": etiqueta_periodo,
        "reducido": reducido,
        "sucursal": ambito,
        "generado_por": sesion.usuario,
        "generado_el": (datetime.utcnow() - timedelta(minutes=tz_offset_min)).strftime("%Y-%m-%d %H:%M"),
        # Un cajero ve el cuadre de efectivo y el desglose por método de pago,
        # pero no la ganancia ni el detalle de cada venta/gasto/abono —eso
        # queda para "resumen" completo del gerente—.
        "resumen": {
            "cuadre_caja": bloque["cuadre_caja"],
            "desglose_metodos_pago": bloque["desglose_metodos_pago"],
            "desglose_metodos_abonos": bloque["desglose_metodos_abonos"],
        } if reducido else bloque,
        "cortes": [{
            "hora": hora(c.creado_en), "sucursal": c.sucursal, "operador": c.operador,
            "saldo_inicial": c.saldo_inicial, "ventas_efectivo": c.ventas_efectivo,
            "abonos_efectivo": c.abonos_efectivo, "gastos_efectivo": c.gastos_efectivo,
            "esperado": c.esperado, "contado": c.contado, "diferencia": c.diferencia,
            "retirado": c.retirado,
            "queda_en_caja": round((c.contado or 0) - (c.retirado or 0), 2),
            "nota": c.nota or "",
        } for c in cortes],
        "queda_por_sucursal": queda_por_sucursal,
        "queda_en_caja": round(sum(queda_por_sucursal.values()), 2),
        "retirado_total": round(sum(c.retirado or 0 for c in cortes), 2),
        "caja_ahora": caja_ahora,
        # None (no []) a propósito: en el PDF/CSV distingue "no te toca verlo"
        # de "no hubo ninguno este día", que se verían idénticos con [].
        "ventas": None if reducido else [{
            "hora": hora(_fecha_contable_venta(v)), "folio": v.id, "sucursal": v.sucursal,
            "operador": v.operador, "metodo": v.metodo_pago or "efectivo",
            "cliente": nombres_cliente.get(v.cliente_id, ""), "estado": v.estado or "activa",
            "devuelto": v.total_devuelto or 0, "total": v.total,
            "es_anticipo": bool(v.es_anticipo),
        } for v in ventas],
        "gastos": None if reducido else [{
            "hora": hora(g.fecha), "sucursal": g.sucursal, "concepto": g.concepto,
            "categoria": g.categoria, "metodo": g.metodo_pago or "efectivo",
            "operador": g.operador, "monto": g.monto,
        } for g in gastos],
        "abonos": None if reducido else [{
            "hora": hora(p.creado_en), "sucursal": p.sucursal,
            "cliente": nombres_cliente.get(p.cliente_id, ""), "metodo": p.metodo_pago or "efectivo",
            "operador": p.operador, "monto": p.monto,
        } for p in abonos],
    }

    if formato != "csv":
        return datos

    # ─── Mismos datos, en CSV para hoja de cálculo ───
    cc = bloque["cuadre_caja"]
    L = [
        _csv_linea(["Reporte por rango de fechas" if es_rango else "Reporte del día"]),
        _csv_linea(["Periodo" if es_rango else "Fecha", etiqueta_periodo]),
        _csv_linea(["Sucursal", datos["sucursal"]]),
        _csv_linea(["Generado por", datos["generado_por"]]),
        _csv_linea(["Generado el", datos["generado_el"]]),
        "",
    ]
    # Ganancia y detalle de cada movimiento son información de dueño, no de
    # cajero: con reducido=True se saltan por completo. El desglose por
    # método de pago sí se queda para los dos —no es más de lo que ya se ve
    # sumado en el cuadre de caja de abajo—.
    if not reducido:
        L += [
            _csv_linea(["RESUMEN"]),
            _csv_linea(["Concepto", "Cantidad", "Monto"]),
            _csv_linea(["Ventas", bloque["num_ventas"], bloque["total_vendido"]]),
            _csv_linea(["Devoluciones", bloque["devoluciones_num"], bloque["devoluciones_total"]]),
            _csv_linea(["Gastos", bloque["num_gastos"], bloque["gastos"]]),
            _csv_linea(["Abonos de clientes", bloque["num_abonos"], bloque["abonos_total"]]),
            _csv_linea(["Ganancia neta (ventas - gastos)", "", bloque["ganancia_neta"]]),
            "",
        ]
    L += [
        _csv_linea(["VENTAS POR MÉTODO DE PAGO"]),
        _csv_linea(["Método", "Tickets", "Monto"]),
    ]
    for m in bloque["desglose_metodos_pago"]:
        L.append(_csv_linea([m["metodo"], m["cantidad"], m["total"]]))
    L.append("")
    if bloque["desglose_metodos_abonos"]:
        L.append(_csv_linea(["ABONOS DE CLIENTES POR MÉTODO DE PAGO"]))
        L.append(_csv_linea(["Método", "Abonos", "Monto"]))
        for m in bloque["desglose_metodos_abonos"]:
            L.append(_csv_linea([m["metodo"], m["cantidad"], m["total"]]))
        L.append("")
    L += [
        _csv_linea(["EFECTIVO DEL DÍA"]),
        _csv_linea(["Ventas en efectivo", cc["ventas_efectivo"]]),
        _csv_linea(["Abonos cobrados en efectivo", cc["abonos_efectivo"]]),
        _csv_linea(["Gastos pagados en efectivo",
                    -cc["gastos_efectivo"] if cc["gastos_efectivo"] else 0]),
        _csv_linea(["Movimiento neto de efectivo", cc["esperado_en_caja"]]),
        "",
        _csv_linea(["CORTES DE CAJA DEL DÍA"]),
    ]
    if datos["cortes"]:
        # Un corte cuenta desde el corte anterior, no desde la medianoche: si el
        # día anterior no se cerró la caja, sus cifras no coinciden con las de
        # arriba. Se avisa aquí para que nadie lo lea como un descuadre.
        L.append(_csv_linea(["Nota", "Las cifras de cada corte abarcan desde el corte anterior, "
                             f"que puede no coincidir con {periodo_txt}"]))
        L.append(_csv_linea(["Hora", "Sucursal", "Operador", "Fondo inicial", "Ventas efectivo",
                             "Abonos efectivo", "Gastos efectivo", "Debía haber", "Contado",
                             "Diferencia", "Retirado", "Se quedó en caja", "Nota"]))
        for c in datos["cortes"]:
            L.append(_csv_linea([c["hora"], c["sucursal"], c["operador"], c["saldo_inicial"],
                                 c["ventas_efectivo"], c["abonos_efectivo"], c["gastos_efectivo"],
                                 c["esperado"], c["contado"], c["diferencia"], c["retirado"],
                                 c["queda_en_caja"], c["nota"]]))
        L.append("")
        if len(queda_por_sucursal) > 1:
            for s in sorted(queda_por_sucursal):
                L.append(_csv_linea([f"Se quedó en la caja de {s}", queda_por_sucursal[s]]))
        L.append(_csv_linea(["Efectivo que se quedó en la caja", datos["queda_en_caja"]]))
        L.append(_csv_linea(["Efectivo retirado en el día", datos["retirado_total"]]))
    else:
        L.append(_csv_linea([f"Sin cortes registrados {periodo_txt}"]))
        if caja_ahora and caja_ahora["hubo_corte_antes"]:
            L.append(_csv_linea(["Debería haber ahora en el cajón (sin cerrar)", caja_ahora["monto"]]))
        elif caja_ahora:
            L.append(_csv_linea(["Efectivo acumulado sin cortar nunca", caja_ahora["monto"]]))
            L.append(_csv_linea(["Aviso", "Esta sucursal no tiene ningún corte registrado: "
                                 f"la cifra anterior abarca todo el histórico, no solo {periodo_txt}"]))
    if not reducido:
        L += ["", _csv_linea(["DETALLE DE VENTAS"])]
        if datos["ventas"]:
            L.append(_csv_linea(["Hora", "Folio", "Sucursal", "Operador", "Método", "Cliente",
                                 "Estado", "Devuelto", "Total"]))
            for v in datos["ventas"]:
                L.append(_csv_linea([v["hora"], v["folio"], v["sucursal"], v["operador"], v["metodo"],
                                     v["cliente"], v["estado"], v["devuelto"], v["total"]]))
        else:
            L.append(_csv_linea([f"Sin ventas {periodo_txt}"]))
        L += ["", _csv_linea(["DETALLE DE GASTOS"])]
        if datos["gastos"]:
            L.append(_csv_linea(["Hora", "Sucursal", "Concepto", "Categoría", "Método", "Operador", "Monto"]))
            for g in datos["gastos"]:
                L.append(_csv_linea([g["hora"], g["sucursal"], g["concepto"], g["categoria"],
                                     g["metodo"], g["operador"], g["monto"]]))
        else:
            L.append(_csv_linea([f"Sin gastos {periodo_txt}"]))
        L += ["", _csv_linea(["ABONOS DE CLIENTES"])]
        if datos["abonos"]:
            L.append(_csv_linea(["Hora", "Sucursal", "Cliente", "Método", "Operador", "Monto"]))
            for a in datos["abonos"]:
                L.append(_csv_linea([a["hora"], a["sucursal"], a["cliente"], a["metodo"],
                                     a["operador"], a["monto"]]))
        else:
            L.append(_csv_linea([f"Sin abonos {periodo_txt}"]))

    # BOM al inicio: sin él, Excel abre los acentos como basura
    cuerpo = "\ufeff" + "\r\n".join(L) + "\r\n"
    nombre = f"reporte-{dia_iso}-{(restriccion or 'todas').replace(' ', '_')}.csv"
    return Response(
        content=cuerpo.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )



@app.get("/corte-caja", response_class=FileResponse)
def corte_caja_page():
    # no-cache (no "no-store"): el navegador puede guardar una copia, pero
    # siempre debe revalidar con el servidor antes de usarla —con ETag/
    # Last-Modified de por medio, eso es una respuesta 304 casi instantánea
    # si no cambió nada—. Sin esto, un cambio en este archivo (como el de
    # hoy, que quitó un redirect que rompía la pantalla para cajero) puede
    # tardar en verse si el navegador ya tenía la versión vieja en caché.
    return FileResponse("static/corte_caja.html", headers={"Cache-Control": "no-cache"})


@app.get("/gastos", response_class=FileResponse)
def gastos_page():
    return FileResponse("static/gastos.html")


# ─── Clientes y ventas a credito ────────────────────────────────────────────
def precio_por_nivel(p: Producto, nivel: Optional[int]) -> Optional[float]:
    """Precio de mayoreo para un nivel 1/2/3 directo, sin pasar por un cliente
    -para cuando se elige el precio a mano al cobrar (El Zar del LED), sin
    que dependa de (ni cambie) el nivel guardado del cliente."""
    precio = {1: p.precio_1, 2: p.precio_2, 3: p.precio_3}.get(nivel)
    return precio if precio and precio > 0 else None


def precio_para_cliente(p: Producto, cliente: Optional[Cliente]) -> Optional[float]:
    """Precio de mayoreo que le toca a un cliente, o None si no aplica.

    Solo cuenta si el cliente trae nivel y el producto tiene capturado ese
    nivel; en cualquier otro caso se cobra el precio de siempre. Así las tiendas
    que no usan niveles no cambian de comportamiento."""
    if cliente is None:
        return None
    return precio_por_nivel(p, cliente.nivel_precio)



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


def clientes_visibles_query(db: Session, sesion: Sesion):
    """Query de Cliente ya filtrado por lo que puede ver esta sesión.

    La cartera general (cliente.sucursal es NULL) se comparte entre casi todas
    las sucursales. La excepción son las que venden con niveles de precio (El
    Zar): esas llevan su propia cartera aparte —son clientes de mayoreo con
    condiciones distintas— y no ven la general. Sin restricción (Only
    Enterprises) se ven todos. Un solo sitio para esta regla: repetirla en cada
    endpoint es como se coló el bug de que El Zar veía la cartera de las demás."""
    query = db.query(Cliente)
    restriccion = sucursal_restriccion(sesion)
    if restriccion is None:
        return query
    suc_actual = db.query(Sucursal).filter(Sucursal.nombre == restriccion).first()
    if suc_actual and suc_actual.usa_niveles_precio:
        return query.filter(Cliente.sucursal == restriccion)
    return query.filter(or_(Cliente.sucursal == restriccion, Cliente.sucursal.is_(None)))


def _saldo_cliente(db, cliente_id):
    ventas = db.query(Venta).filter(Venta.cliente_id == cliente_id, Venta.metodo_pago == "credito").all()
    suma_ventas = sum(v.total for v in ventas)
    pagos = db.query(PagoCredito).filter(PagoCredito.cliente_id == cliente_id).all()
    suma_pagos = sum(p.monto for p in pagos)
    return round(suma_ventas - suma_pagos, 2)


def _resumen_cuentas_cliente(db, cliente_id):
    """Separa la cuenta corriente de los pedidos con anticipo."""
    ventas = db.query(Venta).filter(
        Venta.cliente_id == cliente_id, Venta.metodo_pago == "credito").all()
    pagos = db.query(PagoCredito).filter(PagoCredito.cliente_id == cliente_id).all()
    asignacion = _saldo_por_venta_credito(ventas, pagos)
    pedidos = [v for v in ventas if v.es_anticipo]
    saldo_pedidos = round(sum(asignacion[v.id]["saldo"] for v in pedidos), 2)
    saldo_credito = round(sum(
        asignacion[v.id]["saldo"] for v in ventas if not v.es_anticipo), 2)
    return {
        "saldo": round(saldo_pedidos + saldo_credito, 2),
        "saldo_credito": saldo_credito,
        "saldo_pedidos": saldo_pedidos,
        "pedidos_pendientes": sum(1 for v in pedidos if asignacion[v.id]["saldo"] > 0.005),
        "pedidos_liquidados": sum(1 for v in pedidos if asignacion[v.id]["saldo"] <= 0.005),
    }


@app.post("/api/clientes", status_code=201)
def crear_cliente(data: CrearCliente, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    if data.nivel_precio is not None and data.nivel_precio not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="El nivel de precio debe ser 1, 2 o 3")
    c = Cliente(
        nombre=data.nombre.strip(),
        telefono=normalizar_telefono(data.telefono),
        nota=data.nota,
        limite_credito=data.limite_credito,
        # Cada sucursal lleva su propia cartera; queda con la de quien lo da de alta
        sucursal=sesion.sucursal,
        nivel_precio=data.nivel_precio,
        temporal=data.temporal,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"id": c.id, "nombre": c.nombre, "telefono": c.telefono, "limite_credito": c.limite_credito,
            "sucursal": c.sucursal, "nivel_precio": c.nivel_precio, "temporal": c.temporal, "saldo": 0.0}


@app.get("/api/clientes")
def listar_clientes(q: Optional[str] = Query(None), sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    query = clientes_visibles_query(db, sesion)
    if q:
        query = query.filter(Cliente.nombre.ilike(f"%{q}%"))
    clientes = query.order_by(Cliente.nombre).all()
    resultado = []
    for c in clientes:
        cuentas = _resumen_cuentas_cliente(db, c.id)
        resultado.append({
            "id": c.id,
            "nombre": c.nombre,
            "telefono": c.telefono,
            "limite_credito": c.limite_credito,
            "sucursal": c.sucursal,
            "nivel_precio": c.nivel_precio,
            "temporal": bool(c.temporal),
            "es_cliente_credito": not bool(c.temporal),
            "tiene_pedidos": cuentas["pedidos_pendientes"] + cuentas["pedidos_liquidados"] > 0,
            **cuentas,
        })
    return resultado


def _descripcion_venta(v):
    """Nombre corto para mostrar un pedido en la caja de anticipos: el
    artículo si es uno solo, o un resumen si son varios."""
    try:
        items = json.loads(v.detalle_json)
    except (TypeError, ValueError):
        return f"Venta #{v.id}"
    if not items:
        return f"Venta #{v.id}"
    if len(items) == 1:
        return items[0].get("nombre") or f"Venta #{v.id}"
    return f"{items[0].get('nombre', 'Artículo')} y {len(items) - 1} más"


def _saldo_por_venta_credito(ventas, pagos):
    """Saldo pendiente de cada venta a crédito de un mismo cliente.

    Los pagos con venta_id (el anticipo o la liquidación de un pedido
    concreto, ej. El Zar del LED) aplican directo a ESA venta. El resto -sin
    venta_id, como siempre fue el abono genérico- se reparte FIFO entre las
    ventas más antiguas que les vaya quedando saldo. Compatible con pagos
    viejos, que nunca traen venta_id: se comportan exactamente igual que antes."""
    ids_ventas = {v.id for v in ventas}
    pagado_directo = {}
    total_sin_asignar = 0.0
    for p in pagos:
        if p.venta_id is not None and p.venta_id in ids_ventas:
            pagado_directo[p.venta_id] = pagado_directo.get(p.venta_id, 0.0) + p.monto
        else:
            total_sin_asignar += p.monto

    ventas_orden_asc = sorted(ventas, key=lambda v: v.creado_en)
    restante = total_sin_asignar
    resultado = {}
    for v in ventas_orden_asc:
        directo = round(pagado_directo.get(v.id, 0.0), 2)
        saldo_tras_directo = max(0.0, round(v.total - directo, 2))
        if restante >= saldo_tras_directo:
            fifo = saldo_tras_directo
            restante = round(restante - saldo_tras_directo, 2)
        else:
            fifo = max(0.0, restante)
            restante = 0.0
        pagado_total = round(directo + fifo, 2)
        resultado[v.id] = {"pagado": pagado_total, "saldo": round(v.total - pagado_total, 2)}
    return resultado


def _tipos_pago_pedido(pagos, ventas_pedido_ids):
    """Distingue el primer cobro (anticipo) de los posteriores (liquidación)."""
    tipos = {}
    vistos = set()
    for p in sorted(pagos, key=lambda x: x.creado_en):
        if p.venta_id in ventas_pedido_ids:
            tipos[p.id] = "liquidacion" if p.venta_id in vistos else "anticipo"
            vistos.add(p.venta_id)
        else:
            tipos[p.id] = "abono"
    return tipos


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
    venta_ids = {p.venta_id for p in pagos if p.venta_id is not None}
    ventas_map = {}
    if venta_ids:
        ventas_map = {v.id: v for v in db.query(Venta).filter(Venta.id.in_(venta_ids)).all()}
    pedidos_ids = {vid for vid, v in ventas_map.items() if v.es_anticipo}
    pagos_pedidos = db.query(PagoCredito).filter(PagoCredito.venta_id.in_(pedidos_ids)).all() if pedidos_ids else []
    tipos_pago = _tipos_pago_pedido(pagos_pedidos, pedidos_ids)

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
            "tpv_referencia": p.tpv_referencia,
            "tpv_autorizacion": p.tpv_autorizacion,
            "tpv_terminal": p.tpv_terminal,
            "transferencia_referencia": p.transferencia_referencia,
            "autorizado_por": p.autorizado_por,
            "venta_id": p.venta_id,
            "tipo_movimiento": tipos_pago.get(p.id, "abono"),
            "descripcion_pedido": _descripcion_venta(ventas_map[p.venta_id]) if p.venta_id in pedidos_ids else None,
        } for p in pagos],
    }


@app.get("/api/clientes/{cliente_id}")
def detalle_cliente(cliente_id: int, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    ventas = db.query(Venta).filter(Venta.cliente_id == cliente_id, Venta.metodo_pago == "credito").order_by(Venta.creado_en.desc()).all()
    pagos = db.query(PagoCredito).filter(PagoCredito.cliente_id == cliente_id).order_by(PagoCredito.creado_en.desc()).all()
    asignacion = _saldo_por_venta_credito(ventas, pagos)
    pedidos_ventas = [v for v in ventas if v.es_anticipo]
    tipos_pago = _tipos_pago_pedido(pagos, {v.id for v in pedidos_ventas})
    saldo_pedidos = round(sum(asignacion[v.id]["saldo"] for v in pedidos_ventas), 2)
    saldo_credito = round(sum(
        asignacion[v.id]["saldo"] for v in ventas if not v.es_anticipo), 2)

    # Todos los pedidos se conservan en Clientes; anticipos mantiene solo los
    # pendientes porque también alimenta el selector "Liquidar anticipo".
    pedidos = [{
        "venta_id": v.id,
        "descripcion": _descripcion_venta(v),
        "total": v.total,
        "pagado": asignacion[v.id]["pagado"],
        "saldo": asignacion[v.id]["saldo"],
        "fecha": v.creado_en.isoformat() + "Z",
        "liquidado_en": v.liquidado_en.isoformat() + "Z" if v.liquidado_en else None,
        "estado": "liquidado" if asignacion[v.id]["saldo"] <= 0.005 else "pendiente",
        "sucursal": v.sucursal,
    } for v in pedidos_ventas]
    anticipos = [p for p in pedidos if p["estado"] == "pendiente"]

    return {
        "id": c.id,
        "nombre": c.nombre,
        "telefono": c.telefono,
        "nota": c.nota,
        "limite_credito": c.limite_credito,
        "sucursal": c.sucursal,
        "nivel_precio": c.nivel_precio,
        "temporal": bool(c.temporal),
        "saldo": round(saldo_credito + saldo_pedidos, 2),
        "saldo_credito": saldo_credito,
        "saldo_pedidos": saldo_pedidos,
        "ventas": [{
            "id": v.id, "total": v.total, "fecha": v.creado_en.isoformat() + "Z",
            "operador": v.operador, "sucursal": v.sucursal, "es_anticipo": v.es_anticipo,
            "pagado": asignacion[v.id]["pagado"], "saldo": asignacion[v.id]["saldo"],
        } for v in ventas],
        "anticipos": anticipos,
        "pedidos": pedidos,
        "pagos": [{
            "id": p.id, "monto": p.monto, "metodo_pago": p.metodo_pago,
            "fecha": p.creado_en.isoformat() + "Z", "operador": p.operador, "nota": p.nota,
            "tpv_referencia": p.tpv_referencia, "tpv_autorizacion": p.tpv_autorizacion,
            "tpv_terminal": p.tpv_terminal, "transferencia_referencia": p.transferencia_referencia,
            "autorizado_por": p.autorizado_por, "venta_id": p.venta_id,
            "tipo_movimiento": tipos_pago.get(p.id, "abono"),
        } for p in pagos],
    }


@app.patch("/api/clientes/{cliente_id}")
def editar_cliente(cliente_id: int, data: CrearCliente, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    if data.nivel_precio is not None and data.nivel_precio not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="El nivel de precio debe ser 1, 2 o 3")
    c.nombre = data.nombre.strip()
    c.telefono = normalizar_telefono(data.telefono)
    c.nota = data.nota
    c.limite_credito = data.limite_credito
    c.nivel_precio = data.nivel_precio
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
    if metodo == "tarjeta" and (not data.tpv_referencia or not data.tpv_autorizacion):
        raise HTTPException(status_code=400, detail="Ingresa la referencia y autorización de la TPV")

    venta_ref = None
    saldo_venta = None
    if data.venta_id is not None:
        venta_ref = db.query(Venta).filter(Venta.id == data.venta_id).first()
        if not venta_ref or venta_ref.cliente_id != cliente_id or venta_ref.metodo_pago != "credito":
            raise HTTPException(status_code=404, detail="Esa venta a crédito no es de este cliente")
        ventas_cli = db.query(Venta).filter(Venta.cliente_id == cliente_id, Venta.metodo_pago == "credito").all()
        pagos_cli = db.query(PagoCredito).filter(PagoCredito.cliente_id == cliente_id).all()
        saldo_venta = _saldo_por_venta_credito(ventas_cli, pagos_cli)[data.venta_id]["saldo"]
        if data.monto > saldo_venta + 0.01:
            raise HTTPException(status_code=400, detail=f"El monto ({data.monto}) es mayor al saldo pendiente de esa venta ({saldo_venta})")

    p = PagoCredito(
        cliente_id=cliente_id,
        monto=data.monto,
        metodo_pago=metodo,
        operador=sesion.usuario,
        sucursal=sesion.sucursal,
        nota=data.nota,
        tpv_referencia=data.tpv_referencia if metodo == "tarjeta" else None,
        tpv_autorizacion=data.tpv_autorizacion if metodo == "tarjeta" else None,
        tpv_terminal=data.tpv_terminal if metodo == "tarjeta" else None,
        transferencia_referencia=data.transferencia_referencia if metodo == "transferencia" else None,
        venta_id=data.venta_id,
    )
    db.add(p)
    if venta_ref and venta_ref.es_anticipo and data.monto >= saldo_venta - 0.01:
        venta_ref.liquidado_en = datetime.utcnow()
    db.commit()
    db.refresh(p)

    saldo_restante = _saldo_cliente(db, cliente_id)
    cliente_nombre = c.nombre

    return {
        "id": p.id,
        "saldo_restante": saldo_restante,
        "cliente_nombre": cliente_nombre,
        "cliente_eliminado": False,
        "monto": p.monto,
        "metodo_pago": p.metodo_pago,
        "operador": p.operador,
        "sucursal": p.sucursal,
        "nota": p.nota,
        "tpv_referencia": p.tpv_referencia,
        "tpv_autorizacion": p.tpv_autorizacion,
        "tpv_terminal": p.tpv_terminal,
        "transferencia_referencia": p.transferencia_referencia,
        "venta_id": p.venta_id,
        "fecha": p.creado_en.isoformat() + "Z",
    }


# El negocio pidió que condonar/liquidar una cuenta a $0 sin que de verdad
# entre el dinero quede reservado a una sola persona (no "cualquier gerente"),
# porque es una decisión de negocio, no una autorización operativa como el
# descuento en el punto de venta. Por eso se valida el usuario exacto, no el rol.
USUARIO_AUTORIZA_LIQUIDACION = "Daniel Mondragon"


@app.post("/api/clientes/{cliente_id}/liquidar", status_code=201)
def liquidar_cuenta_cliente(cliente_id: int, data: LiquidarCuenta, sesion: Sesion = Depends(requerir_sesion), db: Session = Depends(get_db)):
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    saldo = _saldo_cliente(db, cliente_id)
    if saldo <= 0:
        raise HTTPException(status_code=400, detail="Este cliente no tiene saldo pendiente")

    u = db.query(Usuario).filter(Usuario.usuario == data.usuario).first()
    if not u or not verificar_password(data.password, u.password_hash, u.salt):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    if u.usuario != USUARIO_AUTORIZA_LIQUIDACION:
        raise HTTPException(status_code=403, detail=f"Solo {USUARIO_AUTORIZA_LIQUIDACION} puede autorizar liquidar una cuenta")

    p = PagoCredito(
        cliente_id=cliente_id,
        monto=saldo,
        metodo_pago="condonado",
        operador=sesion.usuario,
        sucursal=sesion.sucursal,
        nota=data.nota,
        autorizado_por=u.usuario,
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
        "autorizado_por": p.autorizado_por,
        "fecha": p.creado_en.isoformat() + "Z",
    }


def _bloque_reporte(ventas_b, gastos_b, abonos_b):
    """Las cifras de un conjunto de movimientos: sirve igual para una sola
    sucursal que para el consolidado de todas, así los dos siempre se calculan
    con el mismo criterio."""
    total_vendido = round(sum(v.total for v in ventas_b), 2)
    gastos_total = round(sum(g.monto for g in gastos_b), 2)

    por_metodo = {}
    for v in ventas_b:
        m = v.metodo_pago or "efectivo"
        if m not in por_metodo:
            por_metodo[m] = {"cantidad": 0, "total": 0.0}
        por_metodo[m]["cantidad"] += 1
        por_metodo[m]["total"] += v.total
    desglose_metodos = sorted(
        [{"metodo": k, "cantidad": v["cantidad"], "total": round(v["total"], 2)} for k, v in por_metodo.items()],
        key=lambda x: x["total"], reverse=True
    )

    devs = [x for x in ventas_b if x.total < 0]

    por_metodo_abonos = {}
    for p in abonos_b:
        m = p.metodo_pago or "efectivo"
        if m not in por_metodo_abonos:
            por_metodo_abonos[m] = {"cantidad": 0, "total": 0.0}
        por_metodo_abonos[m]["cantidad"] += 1
        por_metodo_abonos[m]["total"] += p.monto
    desglose_metodos_abonos = sorted(
        [{"metodo": k, "cantidad": v["cantidad"], "total": round(v["total"], 2)} for k, v in por_metodo_abonos.items()],
        key=lambda x: x["total"], reverse=True
    )

    ventas_efectivo = round(sum(v.total for v in ventas_b if (v.metodo_pago or "efectivo") == "efectivo"), 2)
    abonos_efectivo = round(sum(p.monto for p in abonos_b if (p.metodo_pago or "efectivo") == "efectivo"), 2)
    gastos_efectivo = round(sum(g.monto for g in gastos_b if (g.metodo_pago or "efectivo") == "efectivo"), 2)

    return {
        "total_vendido": total_vendido,
        "num_ventas": len(ventas_b),
        "gastos": gastos_total,
        "num_gastos": len(gastos_b),
        "devoluciones_total": round(sum(abs(x.total) for x in devs), 2),
        "devoluciones_num": len(devs),
        "ganancia_neta": round(total_vendido - gastos_total, 2),
        "abonos_total": round(sum(p.monto for p in abonos_b), 2),
        "num_abonos": len(abonos_b),
        "desglose_metodos_pago": desglose_metodos,
        "desglose_metodos_abonos": desglose_metodos_abonos,
        # Lo que debe haber en el cajón no son solo las ventas en efectivo: los
        # abonos cobrados en efectivo entran, y los gastos pagados en efectivo salen.
        "cuadre_caja": {
            "ventas_efectivo": ventas_efectivo,
            "abonos_efectivo": abonos_efectivo,
            "gastos_efectivo": gastos_efectivo,
            "esperado_en_caja": round(ventas_efectivo + abonos_efectivo - gastos_efectivo, 2),
        },
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

    ventas_q = _acotar_ventas_contabilizadas(db.query(Venta), d, h)
    if restriccion is not None:
        ventas_q = ventas_q.filter(Venta.sucursal == restriccion)
    ventas = ventas_q.all()

    gastos_q = db.query(Gasto)
    if d:
        gastos_q = gastos_q.filter(Gasto.fecha >= d)
    if h:
        gastos_q = gastos_q.filter(Gasto.fecha <= h)
    if restriccion is not None:
        gastos_q = gastos_q.filter(Gasto.sucursal == restriccion)
    gastos_lista = gastos_q.all()

    pagos_q = db.query(PagoCredito)
    if d:
        pagos_q = pagos_q.filter(PagoCredito.creado_en >= d)
    if h:
        pagos_q = pagos_q.filter(PagoCredito.creado_en <= h)
    if restriccion is not None:
        pagos_q = pagos_q.filter(PagoCredito.sucursal == restriccion)
    abonos_lista = pagos_q.all()

    consolidado = _bloque_reporte(ventas, gastos_lista, abonos_lista)

    # Desglose por sucursal, solo para quien ve el negocio completo (Only
    # Enterprises): una sesión de sucursal ya recibe únicamente lo suyo, así que
    # repetírselo sucursal por sucursal no aportaría nada.
    # Va por sucursal y no por tienda porque cada venta guarda la sucursal donde
    # se hizo; la tienda no se puede deducir (Imprenta vende dos a la vez).
    por_sucursal = []
    if restriccion is None:
        tiendas_de = {s.nombre: texto_a_tiendas(s.tiendas) for s in db.query(Sucursal).all()}
        nombres = {v.sucursal for v in ventas} | {g.sucursal for g in gastos_lista} | {p.sucursal for p in abonos_lista}
        for nombre in sorted(n for n in nombres if n):
            bloque = _bloque_reporte(
                [v for v in ventas if v.sucursal == nombre],
                [g for g in gastos_lista if g.sucursal == nombre],
                [p for p in abonos_lista if p.sucursal == nombre],
            )
            bloque["sucursal"] = nombre
            bloque["tiendas"] = tiendas_de.get(nombre, [])
            por_sucursal.append(bloque)

    # Para explicar el total de pagos de cada cliente, distinguimos los
    # movimientos ligados a pedidos: primer cobro = anticipo; posteriores =
    # liquidación. Se consultan también los cobros anteriores al periodo para
    # clasificar correctamente una liquidación hecha hoy.
    venta_ids_pagos = {p.venta_id for p in abonos_lista if p.venta_id is not None}
    pedidos_map = {}
    if venta_ids_pagos:
        pedidos_map = {
            v.id: v for v in db.query(Venta).filter(
                Venta.id.in_(venta_ids_pagos), Venta.es_anticipo == True).all()
        }
    pagos_pedidos_todos = (
        db.query(PagoCredito).filter(PagoCredito.venta_id.in_(pedidos_map)).all()
        if pedidos_map else []
    )
    tipos_pago_pedido = _tipos_pago_pedido(pagos_pedidos_todos, set(pedidos_map))

    clientes = clientes_visibles_query(db, sesion).all()
    detalle_clientes = []
    for c in clientes:
        saldo = _saldo_cliente(db, c.id)
        ventas_credito_periodo = [v for v in ventas if v.cliente_id == c.id and v.metodo_pago == "credito"]
        monto_ventas_credito = round(sum(v.total for v in ventas_credito_periodo), 2)
        pagos_cliente_periodo = [p for p in abonos_lista if p.cliente_id == c.id]
        monto_pagos_periodo = round(sum(p.monto for p in pagos_cliente_periodo), 2)

        if saldo > 0 or monto_ventas_credito > 0 or monto_pagos_periodo > 0:
            # Un cliente puede comprar en más de una sucursal (todas comparten
            # cartera salvo El Zar): en el consolidado de Only Enterprises
            # interesa saber en cuáles, no solo el total.
            sucursales_compra = sorted({v.sucursal for v in ventas_credito_periodo if v.sucursal})
            detalle_clientes.append({
                "cliente_id": c.id,
                "nombre": c.nombre,
                "saldo_actual": round(saldo, 2),
                "ventas_credito_periodo": monto_ventas_credito,
                "pagos_periodo": monto_pagos_periodo,
                "sucursales": sucursales_compra,
                "movimientos_pedidos": [{
                    "tipo": tipos_pago_pedido[p.id],
                    "pedido_id": p.venta_id,
                    "monto": p.monto,
                    "fecha": p.creado_en.isoformat() + "Z",
                } for p in sorted(pagos_cliente_periodo, key=lambda x: x.creado_en)
                  if p.id in tipos_pago_pedido],
            })
    detalle_clientes = sorted(detalle_clientes, key=lambda x: x["saldo_actual"], reverse=True)

    return {
        "desde": desde,
        "hasta": hasta,
        **consolidado,
        "por_sucursal": por_sucursal,
        "clientes_detalle": detalle_clientes,
        "total_por_cobrar": round(sum(c["saldo_actual"] for c in detalle_clientes if c["saldo_actual"] > 0), 2),
    }


@app.get("/api/clientes-resumen")
def resumen_clientes(sesion: Sesion = Depends(requerir_gerente), db: Session = Depends(get_db)):
    clientes = clientes_visibles_query(db, sesion).all()
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


# ─── Chatbot: asistente con IA (modelo local vía Ollama) ────────────────────
# El modelo NUNCA calcula ni inventa cifras: solo decide a qué consulta llamar
# y redacta. Todos los números salen de la base, y cada consulta se filtra con
# los mismos helpers de permisos que el resto de la API (aplicar_filtro_tienda,
# sucursal_restriccion, clientes_visibles_query), para que el asistente no
# pueda ver lo que su sesión no puede ver.
import re
import urllib.error
import urllib.request

CHAT_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
CHAT_MODELO = os.getenv("OLLAMA_MODELO", "llama3.2:3b")
CHAT_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))

# Con esto en 1 el modelo redacta la respuesta final; en 0 se responde con el
# texto que arma el código. Apagado por omisión a propósito: en las pruebas el
# modelo redactando llegó a decir "10 unidades a $1,620.00 cada una" cuando esa
# cifra era el importe *total* de la línea. No inventó el número —lo sacó de los
# datos— pero le cambió el significado, y aquí eso es dinero. Encendido, la
# redacción todavía tiene que pasar _chat_redaccion_confiable().
CHAT_REDACTAR = os.getenv("OLLAMA_REDACTAR", "0") == "1"

# Ollama descarga el modelo de la GPU tras 5 minutos sin uso, y volver a
# cargarlo cuesta ~20 s: la primera pregunta de la mañana se sentiría rota.
# Con esto se queda residente (2.8 GB de VRAM, que de todos modos nadie usa).
CHAT_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "2h")

CHAT_SISTEMA = (
    "Eres el asistente del sistema de inventario y punto de venta de una tienda "
    "de acuarismo y reptiles. Respondes en español de México, en una o dos "
    "frases, sin rodeos.\n\n"
    "Nunca calcules ni inventes cifras: para cualquier dato de precios, "
    "existencias, ventas, gastos o deudas usa la herramienta correspondiente y "
    "repite tal cual los números que te devuelva. El dinero se escribe así: "
    "$1,250.00"
)

# El 3B se equivoca con la charla suelta: llama a una herramienta al azar o
# escribe un JSON falso como texto. Se ataja antes de llegar al modelo.
CHAT_CORTESIA = re.compile(
    r"^\W*(hola|holi|buenas|buenos d|buen d|hey|qu[eé] onda|qu[eé] tal|saludos|"
    r"gracias|graci|ok|okey|va|listo|adi[oó]s|hasta luego|nos vemos|"
    r"qu[eé] puedes|qu[eé] sabes|ay[uú]dame|ayuda|qui[eé]n eres)\b",
    re.I,
)

# Ruido típico de un modelo chico: razonamiento en inglés o un JSON crudo.
CHAT_RUIDO = re.compile(
    r"^\s*[\{\[]|\b(the user|is asking|let me |okay,|i should|i need to|"
    r"according to the|based on the tool)\b",
    re.I,
)

# El modelo a veces contesta "no tengo acceso a esa información" aunque la
# consulta sí devolvió datos. Confunde al usuario y se descarta.
CHAT_EXCUSA = re.compile(
    r"no (tengo|dispongo de|cuento con) (acceso|informaci[oó]n|datos)|"
    r"verificar si tienes acceso|proporcionarme m[aá]s contexto|"
    r"no puedo (acceder|consultar)",
    re.I,
)

CHAT_NUMERO = re.compile(r"\d[\d,]*(?:\.\d+)?")

# A un operador no se le declaran las consultas de gerente, así que el modelo
# intenta responder con la única que tiene a la mano y acaba diciendo "no
# encontré ningún producto que coincida con «ventas»". Se detecta el tema antes
# y se le dice lo que realmente pasa. Esto es cortesía, no el candado: el
# candado está en _chat_esquema y en la verificación de rol del endpoint.
CHAT_TEMA_GERENTE = re.compile(
    r"\b(vent[ao]s?|vendi(?:do|mos|ó)|ganancia|margen|utilidad|ingreso|"
    r"deud[ao]s?|debe[nm]?|cobrar|cr[eé]dito|adeudo|saldo|"
    r"gast[oó]s?|gastado|corte de caja|ticket)\b",
    re.I,
)


def _chat_cifras_de(obj) -> set:
    """Todas las cifras que contiene el resultado de una consulta, incluidas
    las que van dentro de un texto (p. ej. 'Waste away 240ml')."""
    if obj is None or isinstance(obj, bool):
        return set()
    if isinstance(obj, (int, float)):
        return {round(float(obj), 2)}
    if isinstance(obj, str):
        return {round(float(n.replace(",", "")), 2) for n in CHAT_NUMERO.findall(obj)}
    if isinstance(obj, dict):
        return set().union(*(_chat_cifras_de(v) for v in obj.values())) if obj else set()
    if isinstance(obj, list):
        return set().union(*(_chat_cifras_de(v) for v in obj)) if obj else set()
    return set()


def _chat_redaccion_confiable(texto: str, datos) -> bool:
    """¿Se puede mostrar lo que redactó el modelo? Solo si no es ruido, no se
    excusa, y toda cifra de negocio que escribió sale de los datos."""
    if not texto or CHAT_RUIDO.search(texto) or CHAT_EXCUSA.search(texto):
        return False
    del_dato = _chat_cifras_de(datos)
    for n in CHAT_NUMERO.findall(texto):
        v = round(float(n.replace(",", "")), 2)
        if v >= 100 and not any(abs(v - d) < 0.01 for d in del_dato):
            return False
    return True


def _chat_rango(periodo: Optional[str], tz_min: int):
    """Rango [desde, hasta) en UTC naive para un periodo en hora local.
    tz_min es el getTimezoneOffset() del navegador (360 para México)."""
    ahora_local = datetime.utcnow() - timedelta(minutes=tz_min)
    inicio_hoy = ahora_local.replace(hour=0, minute=0, second=0, microsecond=0)
    manana = inicio_hoy + timedelta(days=1)

    if periodo == "ayer":
        desde, hasta = inicio_hoy - timedelta(days=1), inicio_hoy
    elif periodo == "semana":
        desde, hasta = inicio_hoy - timedelta(days=6), manana
    elif periodo == "mes":
        desde, hasta = inicio_hoy.replace(day=1), manana
    else:  # hoy
        desde, hasta = inicio_hoy, manana

    a_utc = lambda d: d + timedelta(minutes=tz_min)
    return a_utc(desde), a_utc(hasta)


def _chat_pesos(n) -> str:
    return f"${n:,.2f}"


def _chat_periodo_texto(periodo: Optional[str]) -> str:
    return {"hoy": "hoy", "ayer": "ayer", "semana": "los últimos 7 días",
            "mes": "este mes"}.get(periodo or "hoy", "hoy")


# ─── Consultas que el asistente puede ejecutar (todas de solo lectura) ──────
# Cada una devuelve {"datos": ..., "resumen": "..."}. El `resumen` es la
# respuesta ya redactada por código: si el modelo contesta cualquier cosa rara,
# se muestra ese texto. Así las cifras nunca dependen del modelo.

def _chat_buscar_producto(db, sesion, args, tz_min):
    nombre = (args.get("nombre") or "").strip()
    if not nombre:
        return {"datos": [], "resumen": "¿De qué producto quieres saber el precio?"}

    query = db.query(Producto).filter(or_(
        Producto.nombre.ilike(f"%{nombre}%"),
        Producto.marca.ilike(f"%{nombre}%"),
        Producto.categoria.ilike(f"%{nombre}%"),
    ))
    rows = aplicar_filtro_tienda(query, sesion).order_by(Producto.nombre).limit(5).all()
    if not rows:
        return {"datos": [], "resumen": f"No encontré ningún producto que coincida con «{nombre}»."}

    datos = [{
        "nombre": p.nombre,
        "marca": p.marca,
        "precio": calcular_precio_final(p),
        "precio_lista": p.precio_venta,
        "stock": p.stock,
        "unidad": p.unidad,
    } for p in rows]

    p = datos[0]
    existencia = f"quedan {p['stock']:g} {p['unidad'] or 'pz'}" if p["stock"] else "no hay existencia"
    resumen = f"{p['nombre']}: {_chat_pesos(p['precio'])} ({existencia})."
    if len(datos) > 1:
        resumen += " También encontré: " + ", ".join(
            f"{d['nombre']} {_chat_pesos(d['precio'])}" for d in datos[1:4]) + "."
    return {"datos": datos, "resumen": resumen}


def _chat_stock_sucursal(db, sesion, args, tz_min):
    nombre = (args.get("producto") or "").strip()
    pedida = (args.get("sucursal") or "").strip()
    if not nombre:
        return {"datos": [], "resumen": "¿De qué producto quieres ver las existencias?"}

    query = db.query(Producto).filter(or_(
        Producto.nombre.ilike(f"%{nombre}%"),
        Producto.marca.ilike(f"%{nombre}%"),
        Producto.categoria.ilike(f"%{nombre}%"),
    ))
    productos = aplicar_filtro_tienda(query, sesion).order_by(Producto.nombre).limit(3).all()
    if not productos:
        return {"datos": [], "resumen": f"No encontré ningún producto que coincida con «{nombre}»."}

    visibles = sucursales_visibles(db, sesion)
    ids = [p.id for p in productos]
    filas = db.query(StockSucursal).filter(StockSucursal.producto_id.in_(ids)).all()
    nombres = {p.id: p.nombre for p in productos}

    datos = []
    for f in filas:
        if visibles is not None and f.sucursal not in visibles:
            continue
        if pedida and pedida.lower() not in f.sucursal.lower():
            continue
        if f.cantidad:
            datos.append({"producto": nombres[f.producto_id],
                          "sucursal": f.sucursal, "cantidad": f.cantidad})
    datos.sort(key=lambda d: -d["cantidad"])

    # La búsqueda puede caer en un solo producto o en varios de una marca
    # («¿dónde hay Repashy?»); en ese caso se suman las piezas por sucursal.
    etiqueta = nombres[productos[0].id] if len(productos) == 1 else \
        f"{nombre} ({len(productos)} productos)"
    if not datos:
        donde = f" en {pedida}" if pedida else " en ninguna sucursal"
        return {"datos": [], "resumen": f"No hay existencia de {etiqueta}{donde}."}

    por_suc = {}
    for d in datos:
        por_suc[d["sucursal"]] = por_suc.get(d["sucursal"], 0) + d["cantidad"]
    lista = "; ".join(f"{s}: {c:g}" for s, c in
                      sorted(por_suc.items(), key=lambda x: -x[1])[:6])
    return {"datos": datos, "resumen": f"{etiqueta} — {lista}."}


def _chat_stock_bajo(db, sesion, args, tz_min):
    categoria = (args.get("categoria") or "").strip()
    query = db.query(Producto).filter(
        Producto.stock <= Producto.stock_minimo, Producto.stock_minimo > 0)
    if categoria:
        query = query.filter(or_(Producto.categoria.ilike(f"%{categoria}%"),
                                 Producto.marca.ilike(f"%{categoria}%")))
    query = aplicar_filtro_tienda(query, sesion)
    total = query.count()
    rows = query.order_by(Producto.stock, Producto.nombre).limit(10).all()

    if not rows:
        return {"datos": [], "resumen": "No hay productos por debajo del stock mínimo."}
    datos = [{"nombre": p.nombre, "stock": p.stock, "minimo": p.stock_minimo} for p in rows]
    lista = ", ".join(f"{d['nombre']} ({d['stock']:g})" for d in datos[:5])
    de = f" de {categoria}" if categoria else ""
    resumen = f"Hay {total} productos{de} en o por debajo del mínimo. Los más bajos: {lista}."
    return {"datos": datos, "total": total, "resumen": resumen}


def _chat_resumen_ventas(db, sesion, args, tz_min):
    periodo = args.get("periodo") or "hoy"
    desde, hasta = _chat_rango(periodo, tz_min)
    r = _calcular_periodo_dash(db, desde, hasta, sucursal_restriccion(sesion))
    txt = _chat_periodo_texto(periodo)
    if not r["num_ventas"]:
        return {"datos": r, "resumen": f"No hay ventas registradas {txt}."}
    resumen = (f"Ventas de {txt}: {_chat_pesos(r['total_vendido'])} en {r['num_ventas']} "
               f"tickets (promedio {_chat_pesos(r['ticket_promedio'])}). "
               f"Ganancia {_chat_pesos(r['ganancia'])}, margen {r['margen_pct']}%.")
    return {"datos": r, "resumen": resumen}


def _chat_resumen_gastos(db, sesion, args, tz_min):
    periodo = args.get("periodo") or "mes"
    desde, hasta = _chat_rango(periodo, tz_min)
    q = db.query(Gasto).filter(Gasto.fecha >= desde, Gasto.fecha < hasta)
    restriccion = sucursal_restriccion(sesion)
    if restriccion is not None:
        q = q.filter(Gasto.sucursal == restriccion)
    gastos = q.all()
    txt = _chat_periodo_texto(periodo)
    if not gastos:
        return {"datos": {}, "resumen": f"No hay gastos registrados {txt}."}

    por_cat = {}
    for g in gastos:
        por_cat[g.categoria] = por_cat.get(g.categoria, 0.0) + g.monto
    desglose = sorted(({"categoria": k, "total": round(v, 2)} for k, v in por_cat.items()),
                      key=lambda x: -x["total"])
    total = round(sum(g.monto for g in gastos), 2)
    lista = ", ".join(f"{d['categoria']} {_chat_pesos(d['total'])}" for d in desglose[:4])
    return {"datos": {"total": total, "num_gastos": len(gastos), "por_categoria": desglose},
            "resumen": f"Gastos de {txt}: {_chat_pesos(total)} en {len(gastos)} movimientos. {lista}."}


def _chat_deuda_clientes(db, sesion, args, tz_min):
    nombre = (args.get("cliente") or "").strip()
    query = clientes_visibles_query(db, sesion)
    if nombre:
        query = query.filter(Cliente.nombre.ilike(f"%{nombre}%"))

    deudores = []
    for c in query.all():
        saldo = _saldo_cliente(db, c.id)
        if saldo > 0:
            deudores.append({"cliente": c.nombre, "deuda": saldo,
                             "limite_credito": c.limite_credito})
    deudores.sort(key=lambda d: -d["deuda"])

    if not deudores:
        if nombre:
            return {"datos": [], "resumen": f"{nombre} no tiene saldo pendiente."}
        return {"datos": [], "resumen": "Ningún cliente tiene saldo pendiente."}
    total = round(sum(d["deuda"] for d in deudores), 2)
    lista = "; ".join(f"{d['cliente']} {_chat_pesos(d['deuda'])}" for d in deudores[:6])
    if nombre and len(deudores) == 1:
        return {"datos": deudores, "resumen": f"{deudores[0]['cliente']} debe {_chat_pesos(total)}."}
    return {"datos": deudores, "total_por_cobrar": total,
            "resumen": f"Por cobrar {_chat_pesos(total)} de {len(deudores)} clientes: {lista}."}


def _chat_top_productos(db, sesion, args, tz_min):
    periodo = args.get("periodo") or "mes"
    desde, hasta = _chat_rango(periodo, tz_min)
    q = db.query(Venta).filter(Venta.creado_en >= desde, Venta.creado_en < hasta)
    restriccion = sucursal_restriccion(sesion)
    if restriccion is not None:
        q = q.filter(Venta.sucursal == restriccion)

    acum = {}
    for v in q.all():
        try:
            detalle = json.loads(v.detalle_json)
        except (TypeError, ValueError):
            continue
        for it in detalle:
            nom = it.get("nombre") or "(sin nombre)"
            a = acum.setdefault(nom, {"nombre": nom, "unidades": 0.0, "importe": 0.0})
            a["unidades"] += it.get("cantidad", 0) or 0
            a["importe"] += it.get("importe", 0) or 0

    top = sorted(acum.values(), key=lambda d: -d["importe"])[:10]
    for d in top:
        d["importe"] = round(d["importe"], 2)
    txt = _chat_periodo_texto(periodo)
    if not top:
        return {"datos": [], "resumen": f"No hay ventas registradas {txt}."}
    lista = ", ".join(f"{d['nombre']} ({d['unidades']:g} pz, {_chat_pesos(d['importe'])})"
                      for d in top[:5])
    return {"datos": top, "resumen": f"Lo más vendido {txt}: {lista}."}


# nombre -> (función, descripción, parámetros, solo_gerente)
CHAT_HERRAMIENTAS = {
    "buscar_producto": (
        _chat_buscar_producto,
        "Precio y existencia total de un producto del catálogo. Úsala cuando "
        "pregunten cuánto cuesta algo, a cuánto se vende, o si hay existencia.",
        {"type": "object",
         "properties": {"nombre": {"type": "string",
                                   "description": "Nombre, marca o parte del nombre del producto"}},
         "required": ["nombre"]},
        False,
    ),
    "stock_por_sucursal": (
        _chat_stock_sucursal,
        "Existencias de un producto desglosadas por sucursal. Úsala cuando la "
        "pregunta mencione una sucursal o pregunte en dónde hay.",
        {"type": "object",
         "properties": {"producto": {"type": "string", "description": "Nombre del producto"},
                        "sucursal": {"type": "string",
                                     "description": "Sucursal concreta. Omitir para ver todas."}},
         "required": ["producto"]},
        False,
    ),
    "productos_stock_bajo": (
        _chat_stock_bajo,
        "Productos en o por debajo de su stock mínimo. Úsala para qué se está "
        "acabando o qué hay que resurtir.",
        {"type": "object",
         "properties": {"categoria": {"type": "string",
                                      "description": "Filtrar por categoría o marca. Opcional."}}},
        False,
    ),
    "resumen_ventas": (
        _chat_resumen_ventas,
        "Total vendido, número de tickets, ganancia y margen de un periodo.",
        {"type": "object",
         "properties": {"periodo": {"type": "string", "enum": ["hoy", "ayer", "semana", "mes"]}},
         "required": ["periodo"]},
        True,
    ),
    "resumen_gastos": (
        _chat_resumen_gastos,
        "Gastos ya registrados, agrupados por categoría. No sirve para dar de "
        "alta un gasto nuevo.",
        {"type": "object",
         "properties": {"periodo": {"type": "string", "enum": ["hoy", "semana", "mes"]}},
         "required": ["periodo"]},
        True,
    ),
    "deuda_clientes": (
        _chat_deuda_clientes,
        "Saldo pendiente de los clientes a crédito. Úsala para deudas y cobranza.",
        {"type": "object",
         "properties": {"cliente": {"type": "string",
                                    "description": "Nombre del cliente. Omitir para ver a todos."}}},
        True,
    ),
    "top_productos": (
        _chat_top_productos,
        "Productos más vendidos de un periodo, por dinero e unidades.",
        {"type": "object",
         "properties": {"periodo": {"type": "string", "enum": ["hoy", "semana", "mes"]}},
         "required": ["periodo"]},
        True,
    ),
}


def _chat_esquema(sesion: Sesion):
    """Herramientas que le tocan a esta sesión. Un operador no ve ventas,
    gastos ni deudas: el mismo criterio que requerir_gerente en el resto de la
    API, aplicado antes de que el modelo sepa siquiera que existen."""
    return [
        {"type": "function",
         "function": {"name": nombre, "description": desc, "parameters": params}}
        for nombre, (_fn, desc, params, solo_gerente) in CHAT_HERRAMIENTAS.items()
        if not solo_gerente or sesion.rol == "gerente"
    ]


def _chat_ollama(mensajes, herramientas=None):
    cuerpo = {"model": CHAT_MODELO, "messages": mensajes, "stream": False,
              "keep_alive": CHAT_KEEP_ALIVE, "options": {"temperature": 0}}
    if herramientas:
        cuerpo["tools"] = herramientas
    req = urllib.request.Request(
        CHAT_OLLAMA_URL,
        data=json.dumps(cuerpo, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=CHAT_TIMEOUT) as r:
            return json.loads(r.read())
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise HTTPException(status_code=503, detail=f"El asistente no está disponible ({e})")


def _chat_ayuda(sesion: Sesion) -> str:
    puedo = ["consultar precios y existencias", "ver el stock por sucursal",
             "decirte qué se está acabando"]
    if sesion.rol == "gerente":
        puedo += ["darte el resumen de ventas y gastos", "revisar quién debe"]
    return "Puedo " + ", ".join(puedo[:-1]) + " y " + puedo[-1] + ". ¿Qué necesitas?"


@app.post("/api/chat")
def chat(data: dict = Body(...), sesion: Sesion = Depends(requerir_sesion),
         db: Session = Depends(get_db)):
    mensaje = (data.get("mensaje") or "").strip()
    tz_min = data.get("tz_offset_min")
    tz_min = tz_min if isinstance(tz_min, int) else 360
    if not mensaje:
        raise HTTPException(status_code=400, detail="Falta el mensaje")
    if len(mensaje) > 500:
        mensaje = mensaje[:500]

    # Charla suelta: se responde sin modelo (ver CHAT_CORTESIA)
    if CHAT_CORTESIA.match(mensaje) and len(mensaje.split()) <= 6:
        return {"respuesta": _chat_ayuda(sesion), "herramienta": None, "datos": None}

    if sesion.rol != "gerente" and CHAT_TEMA_GERENTE.search(mensaje):
        return {"respuesta": "Las ventas, los gastos y las deudas de clientes solo "
                             "las puede consultar un gerente. " + _chat_ayuda(sesion),
                "herramienta": None, "datos": None}

    herramientas = _chat_esquema(sesion)
    mensajes = [{"role": "system", "content": CHAT_SISTEMA},
                {"role": "user", "content": mensaje}]
    primera = _chat_ollama(mensajes, herramientas)
    llamadas = (primera.get("message") or {}).get("tool_calls") or []

    if not llamadas:
        texto = (primera.get("message") or {}).get("content") or ""
        limpio = texto.strip()
        if not limpio or CHAT_RUIDO.search(limpio):
            limpio = ("No estoy seguro de qué necesitas. " + _chat_ayuda(sesion))
        return {"respuesta": limpio, "herramienta": None, "datos": None}

    fn = llamadas[0]["function"]
    nombre = fn.get("name")
    args = fn.get("arguments") or {}
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            args = {}

    entrada = CHAT_HERRAMIENTAS.get(nombre)
    if not entrada or (entrada[3] and sesion.rol != "gerente"):
        # El modelo pidió algo que no existe o que no le toca a esta sesión
        return {"respuesta": _chat_ayuda(sesion), "herramienta": None, "datos": None}

    resultado = entrada[0](db, sesion, args, tz_min)
    respuesta = resultado["resumen"]

    # Segunda pasada opcional: que el modelo lo diga de forma más natural. Solo
    # se usa si pasa la verificación; si no, queda el texto calculado (ver
    # CHAT_REDACTAR). El modelo elige la consulta; las cifras las pone el código.
    if CHAT_REDACTAR:
        mensajes.append({"role": "assistant", "content": "",
                         "tool_calls": [{"function": {"name": nombre, "arguments": args}}]})
        mensajes.append({"role": "tool", "tool_name": nombre,
                         "content": json.dumps(resultado["datos"], ensure_ascii=False, default=str)})
        try:
            segunda = _chat_ollama(mensajes, herramientas)
            texto = ((segunda.get("message") or {}).get("content") or "").strip()
        except HTTPException:
            texto = ""
        if _chat_redaccion_confiable(texto, resultado["datos"]):
            respuesta = texto

    return {"respuesta": respuesta, "resumen_verificado": resultado["resumen"],
            "herramienta": nombre, "argumentos": args, "datos": resultado["datos"]}


@app.get("/chat", response_class=FileResponse)
def chat_page():
    return FileResponse("static/chat.html")
