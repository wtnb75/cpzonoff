import click
import yaml
from .app import app
from .version import VERSION


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version=VERSION, prog_name="cpzonoff")
def cli(ctx):
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.option("--base-url")
@click.option("--verbose/--quiet")
@click.option("--debug/--no-debug", default=False)
@click.option("--config", type=click.File('r'))
@click.option("--host", default="localhost")
@click.option("--port", type=int, default=8080)
def server(base_url, config, verbose, host, port, debug):
    if config:
        conf = yaml.safe_load(config)
    else:
        conf = {}
    if "logging" in conf:
        from logging.config import dictConfig
        dictConfig(conf.get("logging"))
    else:
        from logging import basicConfig
        if verbose is None:
            level = "INFO"
        elif verbose:
            level = "DEBUG"
        else:
            level = "WARNING"
        basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")
    if base_url:
        app.config["APPLICATION_ROOT"] = base_url
        from werkzeug.middleware.dispatcher import DispatcherMiddleware

        def dummy(env, resp):
            resp('400 Not Found', [('Content-Type', 'text/plain')])
            return [b'not found']

        app.wsgi_app = DispatcherMiddleware(dummy, {base_url: app.wsgi_app})
    app.config.update(conf)
    app.debug = debug
    app.run(host=host, port=port)


if __name__ == "__main__":
    cli()
