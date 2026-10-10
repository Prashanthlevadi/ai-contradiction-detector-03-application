"""SQLite Audit & History Storage Module.

Implements persistent audit logs and comparison history according to PDF 04 Step 9.
"""

from typing import List, Dict, Any, Optional
import os
import sqlite3
import json
from datetime import datetime


class HistoryDB:
    """Manages SQLite storage for past comparison sessions."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "history.sqlite")
        self.db_path = db_path
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    source_a_label TEXT,
                    source_b_label TEXT,
                    contradictions_count INTEGER,
                    compatibles_count INTEGER,
                    insufficient_count INTEGER,
                    claims_analyzed INTEGER,
                    summary_json TEXT
                )
            """)
            conn.commit()

    def record_run(
        self,
        source_a_label: str,
        source_b_label: str,
        metrics: Dict[str, Any],
        results: List[Any]
    ) -> int:
        """Records an execution session in SQLite."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        serialized_results = [
            r.model_dump() if hasattr(r, "model_dump") else str(r)
            for r in results
        ]
        summary_payload = json.dumps({
            "metrics": metrics,
            "results": serialized_results
        })

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_runs (
                    timestamp, source_a_label, source_b_label,
                    contradictions_count, compatibles_count,
                    insufficient_count, claims_analyzed, summary_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                source_a_label,
                source_b_label,
                metrics.get("contradictions", 0),
                metrics.get("compatible", 0),
                metrics.get("insufficient", 0),
                metrics.get("claims_analyzed", 0),
                summary_payload
            ))
            conn.commit()
            return cursor.lastrowid

    def list_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Lists recent audit runs."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, timestamp, source_a_label, source_b_label,
                       contradictions_count, compatibles_count,
                       insufficient_count, claims_analyzed
                FROM audit_runs
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
