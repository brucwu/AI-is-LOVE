import json
import sqlite3
import types
from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
from typing import get_args, get_origin, get_type_hints, Union

from backend.character.runtime import CharacterRuntime


def encode(value):
    if is_dataclass(value):
        return {f.name: encode(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [encode(v) for v in value]
    return value


def decode(kind, value):
    origin, args = get_origin(kind), get_args(kind)
    if origin in (Union, types.UnionType):
        if value is None and type(None) in args:
            return None
        return decode(next(t for t in args if t is not type(None)), value)
    if origin is list:
        return [decode(args[0], v) for v in value]
    if kind is datetime:
        return datetime.fromisoformat(value)
    if isinstance(kind, type) and issubclass(kind, Enum):
        return kind(value)
    if is_dataclass(kind):
        hints = get_type_hints(kind)
        return kind(**{k: decode(hints[k], v) for k, v in value.items()})
    if type(value) is not kind:
        if kind is float and type(value) is int:
            return float(value)
        raise ValueError('Invalid snapshot field type')
    return value


class ConflictError(RuntimeError):
    """Another request saved this character first; reload before retrying."""


class RuntimeStore:
    """SQLite for local restart tests; PostgreSQL for Render deployment.

    Save requires the revision returned by load. Revision zero creates only;
    existing snapshots are never silently overwritten. No default cloud path.
    """
    def __init__(self, url):
        if url.startswith('sqlite:///'):
            self.connection = sqlite3.connect(url[len('sqlite:///'):])
            self.placeholder = '?'
        elif url.startswith(('postgresql://', 'postgres://')):
            import psycopg
            self.connection = psycopg.connect(url)
            self.placeholder = '%s'
        else:
            raise ValueError('Use sqlite:/// locally or a PostgreSQL DATABASE_URL')
        with self.connection:
            self.connection.execute('CREATE TABLE IF NOT EXISTS character_snapshots '
                                    '(character_id TEXT PRIMARY KEY, revision INTEGER NOT NULL, payload TEXT NOT NULL)')

    def close(self):
        self.connection.close()

    def load(self, character_id):
        with self.connection:
            row = self.connection.execute(
                f'SELECT revision, payload FROM character_snapshots WHERE character_id={self.placeholder}',
                (character_id,)).fetchone()
        if row is None:
            return None, 0
        document = json.loads(row[1])
        if document['schema_version'] != 1:
            raise ValueError('Unsupported snapshot schema version')
        runtime = decode(CharacterRuntime, document['runtime'])
        if runtime.profile.id != character_id:
            raise ValueError('Snapshot identity mismatch')
        return runtime, row[0]

    def save(self, runtime, expected_revision):
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError('Invalid expected revision')
        payload = json.dumps({'schema_version': 1, 'runtime': encode(runtime)}, ensure_ascii=False)
        p = self.placeholder
        with self.connection:
            if expected_revision == 0:
                cursor = self.connection.execute(
                    f'INSERT INTO character_snapshots (character_id, revision, payload) VALUES ({p}, 1, {p}) '
                    'ON CONFLICT (character_id) DO NOTHING', (runtime.profile.id, payload))
            else:
                cursor = self.connection.execute(
                    f'UPDATE character_snapshots SET revision=revision+1, payload={p} '
                    f'WHERE character_id={p} AND revision={p}',
                    (payload, runtime.profile.id, expected_revision))
            if cursor.rowcount != 1:
                raise ConflictError('Snapshot changed; reload before retrying')
        return expected_revision + 1
