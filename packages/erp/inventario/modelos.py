import os
from sqlmodel import SQLModel, Field, create_engine, Session
from sqlalchemy.engine import URL
from typing import Optional
from datetime import datetime
from contextlib import contextmanager


def get_engine():
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)

        return create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=1,
            pool_timeout=30,
            pool_recycle=1800
        )

    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME")
    db_host = os.getenv("DB_HOST")
    db_port = int(os.getenv("DB_PORT", "5432"))
    db_sslmode = os.getenv("DB_SSLMODE", "require")

    db_url = URL.create(
        "postgresql+psycopg2",
        username=db_user,
        password=db_pass,
        host=db_host,
        port=db_port,
        database=db_name,
        query={"sslmode": db_sslmode}
    )

    return create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=1,
        pool_timeout=30,
        pool_recycle=1800
    )


engine = get_engine()


class Inventario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    descripcion: Optional[str] = None
    precio_venta: float
    cantidad: int = Field(default=0)
    actualizado_en: datetime = Field(default_factory=datetime.utcnow)


class Cliente(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    apellido: str
    email: Optional[str] = None


class Venta(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    inventario_id: int = Field(foreign_key="inventario.id")
    cliente_id: int = Field(foreign_key="cliente.id")
    cantidad: int
    total: float
    fecha: datetime = Field(default_factory=datetime.utcnow)


class Compra(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    inventario_id: int = Field(foreign_key="inventario.id")
    cantidad: int
    costo_unitario: float
    fecha: datetime = Field(default_factory=datetime.utcnow)


def modificar_stock_db(session: Session, inventario_id: int, cantidad_cambio: int):
    item = session.get(Inventario, inventario_id)

    if not item:
        return {
            "status": "error",
            "mensaje": "Item no encontrado",
            "id": inventario_id
        }

    nuevo_stock = item.cantidad + cantidad_cambio

    if nuevo_stock < 0:
        return {
            "status": "error",
            "mensaje": "Stock insuficiente",
            "stock_actual": item.cantidad,
            "id": item.id
        }

    item.cantidad = nuevo_stock
    item.actualizado_en = datetime.utcnow()

    session.add(item)

    return {
        "status": "ok",
        "mensaje": "Stock ajustado",
        "nuevo_stock": item.cantidad,
        "id": item.id
    }


@contextmanager
def get_session():
    session = Session(engine)

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    SQLModel.metadata.create_all(engine)