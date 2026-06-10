#import json
from os import getenv
from sqlmodel import select
from modelos import Cliente, get_session, init_db
#from modelos import Cliente
#from sqlalchemy import create_engine, text

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


def get_method_and_path(event):
    http = event.get("http", {})

    method = (http.get("method") or event.get("__ow_method") or "GET").upper()
    path = http.get("path") or event.get("__ow_path") or "/"

    path = path.rstrip("/") or "/"

    return method, path


def get_cliente_id_from_path(path):
    """
    Acepta:
    /1
    /cliente/1
    /clientes/1
    """
    parts = [p for p in path.split("/") if p]

    if len(parts) == 1 and parts[0].isdigit():
        return int(parts[0])

    if len(parts) == 2 and parts[0] in ["cliente", "clientes"] and parts[1].isdigit():
        return int(parts[1])

    return None


def get_body_params(event):
    """
    En DigitalOcean con web: true, el body JSON llega como campos directos.
    Quitamos 'http' porque eso es metadata de la petición.
    """
    return {k: v for k, v in event.items() if k != "http"}


def main(event, context):
    ensure_db()

    method, path = get_method_and_path(event)
    args = get_body_params(event)

    # GET / o /cliente o /clientes
    if path in ["/", "/cliente", "/clientes"] and method == "GET":
        with get_session() as session:
            clientes = session.exec(select(Cliente)).all()
            data = [c.model_dump() for c in clientes]

            return response({
                "status": "ok",
                "data": data
            }, 200)

    # POST / o /cliente o /clientes
    elif path in ["/", "/cliente", "/clientes"] and method == "POST":
        nombre = args.get("nombre")
        apellido = args.get("apellido")
        email = args.get("email")

        if not nombre or not apellido:
            return response({
                "status": "error",
                "mensaje": "Nombre y apellido requeridos"
            }, 400)

        with get_session() as session:
            nuevo_cliente = Cliente(
                nombre=nombre,
                apellido=apellido,
                email=email
            )

            session.add(nuevo_cliente)
            session.flush()
            session.refresh(nuevo_cliente)

            return response({
                "status": "ok",
                "mensaje": "Cliente creado",
                "data": nuevo_cliente.model_dump()
            }, 201)

    # PUT /1 o /cliente/1 o /clientes/1
    elif method == "PUT":
        cliente_id = get_cliente_id_from_path(path)

        if cliente_id is None:
            return response({
                "status": "error",
                "mensaje": "ID inválido"
            }, 400)

        with get_session() as session:
            cliente = session.get(Cliente, cliente_id)

            if not cliente:
                return response({
                    "status": "error",
                    "mensaje": "Cliente no encontrado"
                }, 404)

            cliente.nombre = args.get("nombre", cliente.nombre)
            cliente.apellido = args.get("apellido", cliente.apellido)
            cliente.email = args.get("email", cliente.email)

            session.add(cliente)
            session.flush()
            session.refresh(cliente)

            return response({
                "status": "ok",
                "mensaje": "Cliente actualizado",
                "data": cliente.model_dump()
            }, 200)

    # DELETE /1 o /cliente/1 o /clientes/1
    elif method == "DELETE":
        cliente_id = get_cliente_id_from_path(path)

        if cliente_id is None:
            return response({
                "status": "error",
                "mensaje": "ID inválido"
            }, 400)

        with get_session() as session:
            cliente = session.get(Cliente, cliente_id)

            if not cliente:
                return response({
                    "status": "error",
                    "mensaje": "Cliente no encontrado"
                }, 404)

            session.delete(cliente)

            return response({
                "status": "ok",
                "mensaje": "Cliente eliminado"
            }, 200)

    return response({
        "status": "error",
        "mensaje": "Ruta o método no válido",
        "path_recibido": path,
        "method_recibido": method
    }, 404)
    
    