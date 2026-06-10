import json
from sqlmodel import select
from modelos import (
    Venta,
    Cliente,
    Inventario,
    get_session,
    modificar_stock_db,
    init_db
)

_db_initialized = False


def ensure_db():
    global _db_initialized
    if not _db_initialized:
        init_db()
        _db_initialized = True


def response(body, status_code=200):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(body)
    }


def get_method_and_path(event):
    http = event.get("http", {})

    method = (http.get("method") or "GET").upper()
    path = http.get("path") or "/"

    path = path.rstrip("/") or "/"

    return method, path


def get_body_params(event):
    return {k: v for k, v in event.items() if k != "http"}


def main(event, context):
    #ensure_db()

    method, path = get_method_and_path(event)
    args = get_body_params(event)

    # GET / o /venta o /ventas
    if path in ["/", "/venta", "/ventas"] and method == "GET":
        with get_session() as session:
            ventas = session.exec(select(Venta)).all()
            res = []

            for venta in ventas:
                cliente = session.get(Cliente, venta.cliente_id)
                producto = session.get(Inventario, venta.inventario_id)

                data = venta.model_dump()
                data["fecha"] = data["fecha"].isoformat()

                if cliente:
                    data["cliente"] = f"{cliente.nombre} {cliente.apellido}"

                if producto:
                    data["producto"] = producto.nombre

                res.append(data)

            return response({
                "status": "ok",
                "data": res
            }, 200)

    # POST / o /venta o /ventas
    elif path in ["/", "/venta", "/ventas"] and method == "POST":
        inventario_id = args.get("inventario_id")
        cliente_id = args.get("cliente_id")
        cantidad = args.get("cantidad")

        if inventario_id is None or cliente_id is None or cantidad is None:
            return response({
                "status": "error",
                "mensaje": "Faltan datos"
            }, 400)

        inventario_id = int(inventario_id)
        cliente_id = int(cliente_id)
        cantidad = int(cantidad)

        with get_session() as session:
            producto = session.get(Inventario, inventario_id)

            if not producto:
                return response({
                    "status": "error",
                    "mensaje": "Producto no encontrado"
                }, 404)

            cliente = session.get(Cliente, cliente_id)

            if not cliente:
                return response({
                    "status": "error",
                    "mensaje": "Cliente no encontrado"
                }, 404)

            resultado_stock = modificar_stock_db(
                session,
                inventario_id,
                -cantidad
            )

            if resultado_stock["status"] == "error":
                return response(resultado_stock, 400)

            total = float(producto.precio_venta) * cantidad

            nueva_venta = Venta(
                inventario_id=inventario_id,
                cliente_id=cliente_id,
                cantidad=cantidad,
                total=total
            )

            session.add(nueva_venta)
            session.flush()
            session.refresh(nueva_venta)

            res = nueva_venta.model_dump()
            res["fecha"] = res["fecha"].isoformat()

            return response({
                "status": "ok",
                "mensaje": "Venta registrada",
                "venta": res,
                "stock": resultado_stock
            }, 201)

    return response({
        "status": "error",
        "mensaje": "Ruta o método no válido",
        "path_recibido": path,
        "method_recibido": method
    }, 404)