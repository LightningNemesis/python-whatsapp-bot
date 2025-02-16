import sqlite3
from typing import Optional
import os
from datetime import datetime


class BookingMapper:
    def __init__(self, db_path: str):
        """Initialize the booking mapper with a database path."""
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database with required tables."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create table for scheduled events
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS scheduled_events (
                event_uri TEXT PRIMARY KEY,
                whatsapp_id TEXT NOT NULL,
                event_type_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        conn.commit()
        conn.close()

    def add_scheduled_event(
        self,
        event_uri: str,
        whatsapp_id: str,
        event_type_id: str,
        status: str = "scheduled",
    ):
        """Record a scheduled event."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT OR REPLACE INTO scheduled_events (event_uri, whatsapp_id, event_type_id, status) VALUES (?, ?, ?, ?)",
            (event_uri, whatsapp_id, event_type_id, status),
        )

        conn.commit()
        conn.close()

    def get_whatsapp_id_for_event(self, event_uri: str) -> Optional[str]:
        """Get the WhatsApp ID associated with a scheduled event."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT whatsapp_id FROM scheduled_events WHERE event_uri = ?", (event_uri,)
        )

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None

    def get_event_details(self, event_uri: str) -> Optional[dict]:
        """Get all details for a scheduled event."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM scheduled_events WHERE event_uri = ?", (event_uri,)
        )

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                "event_uri": result[0],
                "whatsapp_id": result[1],
                "event_type_id": result[2],
                "status": result[3],
                "created_at": result[4],
            }
        return None

    def update_event_status(self, event_uri: str, status: str):
        """Update the status of a scheduled event."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE scheduled_events SET status = ? WHERE event_uri = ?",
            (status, event_uri),
        )

        conn.commit()
        conn.close()

    def get_whatsapp_id_for_event_type(self, event_type_id: str) -> Optional[str]:
        """Get the most recent WhatsApp ID associated with an event type."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT whatsapp_id 
            FROM scheduled_events 
            WHERE event_type_id = ? 
            ORDER BY created_at DESC 
            LIMIT 1
            """,
            (event_type_id,),
        )

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None
