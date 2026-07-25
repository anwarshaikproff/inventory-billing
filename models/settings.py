import os
import json
import shutil
from datetime import datetime
from database.db import query_db, execute_db

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'backups')

class Settings:
    @classmethod
    def get(cls, key, default=None):
        """Fetch setting value by key."""
        row = query_db("SELECT value FROM settings WHERE key = %s", (key,), one=True)
        if row:
            return row['value']
        return default

    @classmethod
    def set(cls, key, value):
        """Insert or update setting key-value pair."""
        exists = query_db("SELECT 1 FROM settings WHERE key = %s", (key,), one=True)
        if exists:
            execute_db("UPDATE settings SET value = %s WHERE key = %s", (str(value), key))
        else:
            execute_db("INSERT INTO settings (key, value) VALUES (%s, %s)", (key, str(value)))

    @classmethod
    def get_all(cls):
        """Fetch all settings as a key-value dictionary."""
        rows = query_db("SELECT * FROM settings")
        return {r['key']: r['value'] for r in rows}

    @classmethod
    def update_multiple(cls, settings_dict):
        """Update multiple configurations in one batch."""
        for key, value in settings_dict.items():
            cls.set(key, value)

    @classmethod
    def backup_database(cls):
        """
        Creates a JSON dump of all SQL tables in the backups folder.
        Saves backup record into database backups table.
        """
        os.makedirs(BACKUP_DIR, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"backup_{timestamp}.json"
        dest_path = os.path.join(BACKUP_DIR, backup_filename)
        
        tables_to_backup = [
            'users', 'login_history', 'settings', 'customers', 'suppliers',
            'products', 'offers', 'sales', 'sales_items', 'inventory_history',
            'backups', 'deletion_logs'
        ]
        
        backup_data = {}
        for t in tables_to_backup:
            rows = query_db(f"SELECT * FROM {t}")
            # Format datetime columns to string
            serializable_rows = []
            for r in rows:
                row_dict = {}
                for k, v in r.items():
                    if isinstance(v, datetime):
                        row_dict[k] = v.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        row_dict[k] = v
                serializable_rows.append(row_dict)
            backup_data[t] = serializable_rows
            
        try:
            with open(dest_path, 'w') as f:
                json.dump(backup_data, f, indent=2)
                
            execute_db(
                "INSERT INTO backups (filepath, created_at) VALUES (%s, %s)",
                (dest_path, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            return dest_path
        except Exception as e:
            raise IOError(f"Database backup failed: {str(e)}")

    @classmethod
    def get_backups(cls):
        """Fetch list of all backups."""
        return query_db("SELECT * FROM backups ORDER BY created_at DESC")

    @classmethod
    def restore_database(cls, backup_id):
        """Restores the database from a backup record."""
        row = query_db("SELECT filepath FROM backups WHERE id = %s", (backup_id,), one=True)
        if not row:
            raise ValueError(f"Backup with ID '{backup_id}' not found.")
            
        backup_filepath = row['filepath']
        if not os.path.exists(backup_filepath):
            raise FileNotFoundError(f"Backup file '{backup_filepath}' no longer exists on disk.")

        return cls.restore_from_file(backup_filepath)
            
    @classmethod
    def restore_from_file(cls, filepath):
        """Restore from a JSON database backup file directly."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Selected file '{filepath}' does not exist.")
        try:
            with open(filepath, 'r') as f:
                backup_data = json.load(f)
                
            tables_to_restore = [
                'users', 'login_history', 'settings', 'customers', 'suppliers',
                'products', 'offers', 'sales', 'sales_items', 'inventory_history',
                'backups', 'deletion_logs'
            ]
            
            # Wipe tables in reverse order of foreign keys
            for t in reversed(tables_to_restore):
                execute_db(f"DELETE FROM {t}")
                
            # Restore tables
            for t in tables_to_restore:
                rows = backup_data.get(t, [])
                if not rows:
                    continue
                # Construct insert queries dynamically
                columns = list(rows[0].keys())
                col_placeholders = ", ".join(["%s"] * len(columns))
                col_names = ", ".join(columns)
                query = f"INSERT INTO {t} ({col_names}) VALUES ({col_placeholders})"
                
                for r in rows:
                    vals = [r[col] for col in columns]
                    execute_db(query, tuple(vals))
                    
            return True
        except Exception as e:
            raise IOError(f"Restore from file failed: {str(e)}")
