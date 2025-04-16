
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
from pathlib import Path
import secrets
import logging
import time
import sqlite3
from config_manager import load_config

logger = logging.getLogger(__name__)

def create_app() -> tuple[Flask, SocketIO]:
    app = Flask(__name__)
    app.config['SECRET_KEY'] = secrets.token_hex(16)

    # Try eventlet, fallback to threading if eventlet is unavailable
    async_mode = 'eventlet'
    try:
        import eventlet  # Check if eventlet is installed
        logger.info("Using eventlet for SocketIO async mode")
    except ImportError:
        logger.warning("eventlet not installed, falling back to threading async mode")
        async_mode = 'threading'

    socketio = SocketIO(app, async_mode=async_mode, cors_allowed_origins="*")

    CONFIG = load_config()

    def load_working_proxies():
        try:
            with sqlite3.connect(CONFIG["database"]["file"]) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM proxies")
                rows = cursor.fetchall()
                proxies = [
                    {
                        'ip_address': row[0],
                        'port': row[1],
                        'delay_ms': round(row[2], 2) if row[2] is not None else 0.0,
                        'country': row[3],
                        'updated_timestamp': row[4],
                        'updated_minutes_ago': f"{round((time.time() - row[4]) / 60, 1)} минут",
                        'anonymity': row[5],
                        'protocol': row[6]
                    }
                    for row in rows
                ]
                logger.info(f"Loaded {len(proxies)} proxies from database")
                return proxies
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            return []

    @app.route('/')
    def index():
        proxies_list = load_working_proxies()
        return render_template('index.html', proxies=proxies_list)

    @app.route('/api/proxies', methods=['GET'])
    def get_proxies():
        proxies_list = load_working_proxies()
        return jsonify(proxies_list)

    @app.route('/stat')
    def stat():
        return render_template('stat.html')

    return app, socketio