from flask import Flask


def create_app() -> Flask:
    """Flask application factory.

    - Configures static and template folders
    - Registers blueprints
    """
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
    )

    # Register routes blueprint
    try:
        from .routes import register_blueprint  # local import to avoid circulars

        register_blueprint(app)
    except Exception as exc:  # pragma: no cover
        # Defer errors until runtime to not block minimal app creation
        app.logger.debug("Blueprint registration deferred/failed: %s", exc)

    return app
