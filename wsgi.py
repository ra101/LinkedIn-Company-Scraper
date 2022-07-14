try:
    from app import create_app
except:
    from .app import create_app

application = create_app()
