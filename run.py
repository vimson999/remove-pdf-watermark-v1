import os
from app import create_app

config_name = os.getenv('FLASK_CONFIG') or 'default'
app = create_app(config_name)

if __name__ == '__main__':
    # Determine port, default to 5001 to avoid conflicts
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port)