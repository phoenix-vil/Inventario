from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProductoBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    categoria: str = Field(..., min_length=1, max_length=100)
    marca: Optional[str] = Field(None, max_length=100)
    codigo_barras: Optional[str] = Field(None, max_length=64)
    clave: Optional[str] = Field(None, max_length=64)
    precio_venta: float = Field(..., gt=0)
    precio_costo: float = Field(default=0.0, ge=0)
    precio_1: Optional[float] = Field(None, ge=0)  # niveles de mayoreo; nulo = no aplica
    precio_2: Optional[float] = Field(None, ge=0)
    precio_3: Optional[float] = Field(None, ge=0)
    stock: float = Field(default=0)
    stock_minimo: float = Field(default=5, ge=0)
    unidad: str = Field(default="pieza", max_length=50)
    vendido_por_peso: bool = Field(default=False)
    descuento_pct: float = Field(default=0.0, ge=0, le=100)
    descuento_desde: Optional[datetime] = None
    descuento_hasta: Optional[datetime] = None
    imagen_url: Optional[str] = None
    tienda: Optional[str] = Field(None, max_length=50)


class ProductoCreate(ProductoBase):
    pass


class ProductoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=200)
    categoria: Optional[str] = Field(None, min_length=1, max_length=100)
    marca: Optional[str] = Field(None, max_length=100)
    codigo_barras: Optional[str] = Field(None, max_length=64)
    clave: Optional[str] = Field(None, max_length=64)
    precio_venta: Optional[float] = Field(None, gt=0)
    precio_costo: Optional[float] = Field(None, ge=0)
    stock: Optional[float] = Field(None)
    stock_minimo: Optional[float] = Field(None, ge=0)
    unidad: Optional[str] = Field(None, max_length=50)
    vendido_por_peso: Optional[bool] = None
    descuento_pct: Optional[float] = Field(None, ge=0, le=100)
    descuento_desde: Optional[datetime] = None
    descuento_hasta: Optional[datetime] = None
    imagen_url: Optional[str] = None
    tienda: Optional[str] = Field(None, max_length=50)


class DescuentoCategoria(BaseModel):
    """Aplica un descuento a todos los productos de una categoría."""
    categoria: str
    descuento_pct: float = Field(..., ge=0, le=100)
    descuento_hasta: Optional[datetime] = None


class AsignarStockSucursal(BaseModel):
    producto_id: int
    sucursal: str
    cantidad: float = Field(..., ge=0)


class AjusteStock(BaseModel):
    cantidad: float


class ItemVenta(BaseModel):
    producto_id: Optional[int] = None
    nombre: Optional[str] = None
    cantidad: float
    precio_unitario: float
    precio_original: Optional[float] = None


class AutorizarDescuento(BaseModel):
    usuario: str
    password: str
    descuento_pct: float = Field(..., ge=0, le=100)


class RegistrarVenta(BaseModel):
    items: list[ItemVenta]
    descuento_extra_pct: float = Field(default=0.0, ge=0, le=100)
    autorizado_por: Optional[str] = None
    pago_con: Optional[float] = Field(None, ge=0)
    metodo_pago: str = Field(default="efectivo")
    tpv_referencia: Optional[str] = None
    tpv_autorizacion: Optional[str] = None
    tpv_terminal: Optional[str] = None
    transferencia_referencia: Optional[str] = None
    cliente_id: Optional[int] = None
    # El pedido completo (El Zar del LED) se registra como venta a crédito
    # por el total acordado; el anticipo que se cobra hoy se registra aparte
    # como un PagoCredito ligado a esta venta (ver /api/clientes/{id}/pagos).
    es_anticipo: bool = False


class ItemCotizacion(BaseModel):
    producto_id: Optional[int] = None
    nombre: Optional[str] = None
    cantidad: float
    precio_unitario: float


class RegistrarCotizacion(BaseModel):
    items: list[ItemCotizacion]
    descuento_extra_pct: float = Field(default=0.0, ge=0, le=100)
    cliente_nombre: Optional[str] = None
    cliente_telefono: Optional[str] = None
    nota: Optional[str] = None


class Login(BaseModel):
    usuario: str
    password: str
    sucursal: Optional[str] = None


class LogoutReq(BaseModel):
    token: str


class CrearUsuario(BaseModel):
    usuario: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=4, max_length=100)
    rol: str = Field(default="cajero")


class AccesoEnterprise(BaseModel):
    usuario: str = Field(..., min_length=1, max_length=50)
    permitir: bool


class CambiarPassword(BaseModel):
    usuario: str
    password_nuevo: str = Field(..., min_length=4, max_length=100)


class CrearSucursal(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=50)
    tiendas: Optional[list[str]] = None  # a qué tienda(s) pertenece esta sucursal física
    usuarios_permitidos: Optional[list[str]] = None  # vacío = cualquiera puede entrar


class EditarSucursal(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=50)
    tiendas: Optional[list[str]] = None
    usuarios_permitidos: Optional[list[str]] = None


class CrearTienda(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=50)


class ClasificarProductosMasivo(BaseModel):
    producto_ids: list[int] = Field(..., min_length=1)
    tienda: Optional[str] = None  # None = quitar clasificación (queda visible en todas)


class ProductoOut(ProductoBase):
    id: int
    creado_en: datetime
    actualizado_en: datetime

    class Config:
        from_attributes = True


class TrasladoStock(BaseModel):
    producto_id: int
    sucursal_origen: str
    sucursal_destino: str
    cantidad: float = Field(..., gt=0)


class CrearVentaPendiente(BaseModel):
    carrito: list
    descuento_extra_pct: float = 0.0
    autorizado_por: Optional[str] = None
    nota: Optional[str] = None
    hoy_inicio: Optional[str] = None


class CrearGasto(BaseModel):
    concepto: str = Field(..., min_length=1, max_length=200)
    categoria: str = Field(..., min_length=1, max_length=100)
    monto: float = Field(..., gt=0)
    metodo_pago: str = Field(default="efectivo")
    fecha: Optional[datetime] = None
    nota: Optional[str] = Field(None, max_length=500)


class CrearCliente(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    telefono: Optional[str] = Field(None, max_length=30)
    nota: Optional[str] = Field(None, max_length=500)
    limite_credito: Optional[float] = Field(None, ge=0)
    nivel_precio: Optional[int] = Field(None, ge=1, le=3)  # mayoreo: 1, 2 o 3
    # Cliente dado de alta solo para un anticipo (El Zar del LED): a
    # diferencia de un cliente de crédito normal, se borra solo en cuanto ya
    # no debe nada -no tiene sentido dejarlo en la cartera para siempre-.
    temporal: bool = False


class CrearPagoCredito(BaseModel):
    monto: float = Field(..., gt=0)
    metodo_pago: str = Field(default="efectivo")
    nota: Optional[str] = Field(None, max_length=500)
    tpv_referencia: Optional[str] = None
    tpv_autorizacion: Optional[str] = None
    tpv_terminal: Optional[str] = None
    transferencia_referencia: Optional[str] = None
    venta_id: Optional[int] = None


class LiquidarCuenta(BaseModel):
    usuario: str
    password: str
    nota: Optional[str] = Field(None, max_length=500)


class RegistrarCorteCaja(BaseModel):
    contado: float = Field(..., ge=0)          # efectivo contado en el cajón
    retirado: float = Field(default=0.0, ge=0)  # lo que se saca al cerrar
    nota: Optional[str] = Field(None, max_length=500)
