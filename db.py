"""
Database utilities for the Telegram AI assistant bot.

This module centralises creation of the SQLAlchemy engine and session
factory, exposes a convenience context manager `get_db` for acquiring
sessions, and implements simple audit logging for admin actions.

Any module that needs to access the database should import `get_db` from
this module.  Use the context manager pattern to ensure sessions are
closed properly:

```
from .db import get_db

with get_db() as db:
    # perform DB operations
```

Note that the database schema is created automatically on import.  If you
add new models you should run the bot once to create the tables, or
invoke `Base.metadata.create_all()` manually.
"""

from contextlib import contextmanager
from typing import Iterator, Optional, Dict, Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL
from models import Base, ActionLog, User
from models_enums import UserAction

# Create the SQLAlchemy engine.  Future=True enables 2.0 style usage.
engine = create_engine(DATABASE_URL, echo=False, future=True)

# Session factory bound to the engine.  We disable autoflush to reduce
# incidental writes during command processing.  Autocommit is false so
# that we control transactions explicitly.
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Create all tables on module import.  This ensures that the database
# schema is ready before any requests are handled.  If the database file
# does not exist it will be created.  For production systems you may
# wish to manage migrations with Alembic instead.
Base.metadata.create_all(bind=engine)


@contextmanager
def get_db() -> Iterator[SessionLocal]:
    """Provide a transactional scope around a series of operations.

    Yields a SQLAlchemy session and ensures it is closed when
    the context exits.  Any unhandled exceptions will cause the
    transaction to roll back.

    Returns
    -------
    Iterator[Session]
        A SQLAlchemy session object.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def log_action(db: SessionLocal, user_id: Optional[int], action: UserAction,
               meta: Optional[Dict[str, Any]] = None) -> None:
    """Record a user or admin action in the audit log.

    Parameters
    ----------
    db : Session
        A SQLAlchemy session.
    user_id : int or None
        The ID of the acting user.  If unknown, None may be provided.
    action : UserAction
        An enum describing what happened.
    meta : dict, optional
        Additional metadata to store alongside the action.  This can
        include arbitrary JSON serialisable data.
    """
    # Guard against missing meta
    if meta is None:
        meta = {}
    log_entry = ActionLog(user_id=user_id, action=action, meta=meta)
    db.add(log_entry)
    # Commit handled by context manager
