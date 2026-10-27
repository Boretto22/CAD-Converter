"""Single-replica SQLite job catalogue; every read checks ownership and expiry."""
import hashlib
import hmac
from pathlib import Path
import re
import secrets
import shutil
import sqlite3
import time

ID = re.compile(r'^[a-f0-9]{32}$')


class Store:
    def __init__(self, settings):
        self.settings = settings
        self.root = settings.data_dir.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.database = self.root / 'jobs.sqlite3'
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, owner TEXT NOT NULL, kind TEXT NOT NULL, status TEXT NOT NULL, created REAL NOT NULL, expires REAL NOT NULL, error TEXT)')
            db.execute("UPDATE jobs SET status='failed',error='Service restarted; resubmit the operation' WHERE status IN ('queued','running')")

    def connect(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def directory(self, identifier):
        if not ID.fullmatch(identifier):
            raise ValueError('Invalid job identifier')
        target = self.root / identifier
        if target.is_symlink() or target.resolve().parent != self.root:
            raise ValueError('Invalid job directory')
        return target

    def create(self, owner, kind):
        if shutil.disk_usage(self.root).free < (128*1024**2 if self.settings.profile == 'free' else 1024**3):
            raise ValueError('Storage reserve reached; retry after retained jobs expire')
        now = time.time()
        identifier = secrets.token_hex(16)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            user = db.execute('SELECT count(*) FROM jobs WHERE owner=? AND expires>?', (owner, now)).fetchone()[0]
            total = db.execute('SELECT count(*) FROM jobs WHERE expires>?', (now,)).fetchone()[0]
            queued = db.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','running') AND expires>?", (now,)).fetchone()[0]
            if user >= self.settings.max_user_jobs or total >= self.settings.max_total_jobs or queued >= self.settings.max_queue:
                raise ValueError('Job limit reached; wait for active jobs or retention expiry')
            db.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?,?)', (identifier, owner, kind, 'queued', now, now+self.settings.retention_seconds, None))
        self.directory(identifier).mkdir(exist_ok=False)
        return identifier

    def get(self, identifier, owner):
        self.directory(identifier)
        with self.connect() as db:
            row = db.execute('SELECT * FROM jobs WHERE id=? AND owner=?', (identifier, owner)).fetchone()
        if not row or row['expires'] <= time.time():
            raise ValueError('Job unavailable or expired')
        return dict(row)

    def update(self, identifier, status, error=None):
        with self.connect() as db:
            db.execute('UPDATE jobs SET status=?,error=? WHERE id=?', (status, error, identifier))

    def link(self, identifier, name, owner):
        row = self.get(identifier, owner)
        if row['status'] != 'complete':
            raise ValueError('Job has no downloadable result yet')
        expiry = min(int(time.time())+self.settings.link_seconds, int(row['expires']))
        signature = self.signature(identifier, name, expiry)
        return f'{self.settings.base_url}/download/{identifier}/{name}?expires={expiry}&signature={signature}'

    def signature(self, identifier, name, expiry):
        return hmac.new(self.settings.signing_key.encode(), f'{identifier}\0{name}\0{expiry}'.encode(), hashlib.sha256).hexdigest()

    def authorize_download(self, identifier, name, expiry, signature):
        self.directory(identifier)
        if not isinstance(expiry, int) or expiry <= time.time() or expiry > time.time()+self.settings.link_seconds+2:
            raise ValueError('Download link expired')
        if not hmac.compare_digest(self.signature(identifier, name, expiry), signature):
            raise ValueError('Invalid download link')
        with self.connect() as db:
            row = db.execute('SELECT * FROM jobs WHERE id=?', (identifier,)).fetchone()
        if not row or row['status'] != 'complete' or row['expires'] <= time.time():
            raise ValueError('Result unavailable')
        return row

    def prune(self):
        with self.connect() as db:
            rows = db.execute('SELECT id FROM jobs WHERE expires<=?', (time.time(),)).fetchall()
            for row in rows:
                folder = self.directory(row['id'])
                if folder.exists():
                    shutil.rmtree(folder)
                db.execute('DELETE FROM jobs WHERE id=?', (row['id'],))
        return len(rows)
