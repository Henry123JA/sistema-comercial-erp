import json
from sqlmodel import select
from modelos import (
    Compra,
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

    # GET / o /compra o /compras
    if path in ["/", "/compra", "/compras"] and method == "GET":
        with get_session() as session:
            compras = session.exec(select(Compra)).all()
            res = []

            for compra in compras:
                item = session.get(Inventario, compra.inventario_id)

                data = compra.model_dump()
                data["fecha"] = data["fecha"].isoformat()

                if item:
                    data["producto"] = item.nombre

                res.append(data)

            return response({
                "status": "ok",
                "data": res
            }, 200)

    # POST / o /compra o /compras
    elif path in ["/", "/compra", "/compras"] and method == "POST":
        inventario_id = args.get("inventario_id")
        cantidad = args.get("cantidad")
        costo_unitario = args.get("costo_unitario")

        if inventario_id is None or cantidad is None or costo_unitario is None:
            return response({
                "status": "error",
                "mensaje": "Faltan datos"
            }, 400)

        inventario_id = int(inventario_id)
        cantidad = int(cantidad)
        costo_unitario = float(costo_unitario)

        with get_session() as session:
            item = session.get(Inventario, inventario_id)

            if not item:
                return response({
                    "status": "error",
                    "mensaje": "Producto no encontrado"
                }, 404)

            nueva_compra = Compra(
                inventario_id=inventario_id,
                cantidad=cantidad,
                costo_unitario=costo_unitario
            )

            session.add(nueva_compra)

            resultado_stock = modificar_stock_db(
                session,
                inventario_id,
                cantidad
            )

            if resultado_stock["status"] == "error":
                return response(resultado_stock, 400)

            session.flush()
            session.refresh(nueva_compra)

            res = nueva_compra.model_dump()
            res["fecha"] = res["fecha"].isoformat()

            return response({
                "status": "ok",
                "mensaje": "Compra registrada",
                "compra": res,
                "stock": resultado_stock
            }, 201)

    return response({
        "status": "error",
        "mensaje": "Ruta o método no válido",
        "path_recibido": path,
        "method_recibido": method
    }, 404)