from sqlmodel import select
from modelos import Inventario, get_session, modificar_stock_db, init_db

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
        "body": body
    }


def serialize_inventario(item):
    data = item.model_dump()

    if data.get("actualizado_en"):
        data["actualizado_en"] = data["actualizado_en"].isoformat()

    return data


def get_method_and_path(event):
    http = event.get("http", {})

    method = (http.get("method") or "GET").upper()
    path = http.get("path") or "/"

    path = path.rstrip("/") or "/"

    return method, path


def get_id_from_path(path):
    """
    Acepta:
    /1
    /inventario/1
    """
    parts = [p for p in path.split("/") if p]

    if len(parts) == 1 and parts[0].isdigit():
        return int(parts[0])

    if len(parts) == 2 and parts[0] == "inventario" and parts[1].isdigit():
        return int(parts[1])

    return None


def main(event, context):
    ensure_db()

    method, path = get_method_and_path(event)

    # En DigitalOcean, el JSON del body llega como claves directas en event.
    args = {k: v for k, v in event.items() if k != "http"}

    # GET /inventario o URL directa de la función
    if path in ["/", "/inventario"] and method == "GET":
        with get_session() as session:
            items = session.exec(select(Inventario)).all()
            data = [serialize_inventario(i) for i in items]

            return response({
                "status": "ok",
                "data": data
            }, 200)

    # POST /inventario o URL directa de la función
    elif path in ["/", "/inventario"] and method == "POST":
        nombre = args.get("nombre")
        precio = args.get("precio_venta")
        cantidad = args.get("cantidad", 0)

        if not nombre or precio is None:
            return response({
                "status": "error",
                "mensaje": "Faltan datos"
            }, 400)

        with get_session() as session:
            nuevo_item = Inventario(
                nombre=nombre,
                descripcion=args.get("descripcion"),
                precio_venta=float(precio),
                cantidad=int(cantidad)
            )

            session.add(nuevo_item)
            session.flush()
            session.refresh(nuevo_item)

            return response({
                "status": "ok",
                "mensaje": "Creado",
                "data": serialize_inventario(nuevo_item)
            }, 201)

    # PUT /1 o /inventario/1
    elif method == "PUT":
        inv_id = get_id_from_path(path)

        if inv_id is None:
            return response({
                "status": "error",
                "mensaje": "ID inválido"
            }, 400)

        cambio = args.get("cambio")

        if cambio is None:
            return response({
                "status": "error",
                "mensaje": "Cambio requerido"
            }, 400)

        with get_session() as session:
            resultado = modificar_stock_db(session, inv_id, int(cambio))

            if resultado["status"] == "ok":
                return response(resultado, 200)

            if resultado["mensaje"] == "Stock insuficiente":
                return response(resultado, 400)

            return response(resultado, 404)

    return response({
        "status": "error",
        "mensaje": "Ruta o método no válido",
        "path_recibido": path,
        "method_recibido": method
    }, 404)