import datetime
import subprocess
import json
import yaml
import os
from typing import Union
import shlex
from logging import getLogger
from flask import Flask, render_template, redirect, url_for, request
from flask_misaka import Misaka
from wsgiref.handlers import format_date_time

_log = getLogger(__name__)
app = Flask(__name__)
Misaka(app, tables=True)


def str2datetime(s: str) -> Union[datetime.datetime, datetime.date]:
    """convert string to datetime"""
    if s == 'now':
        return datetime.datetime.now()
    if s == 'today':
        return datetime.date.today()
    try:
        ts = float(s)
        return datetime.datetime.fromtimestamp(ts)
    except ValueError:
        pass
    try:
        return datetime.datetime.fromisoformat(s)
    except ValueError:
        pass
    raise ValueError(f"invalid timestamp: {s}")


@app.template_filter()
def strftime(value: str, format: str = 'iso8601') -> str:
    dt = str2datetime(value)
    if format in ('iso8601', 'rfc3339'):
        return dt.isoformat()
    if format == 'http':
        return format_date_time(dt.timestamp())
    return dt.strftime(format)


def do_compose(*args) -> str:
    """execute compose command

    returns:
        stdout output
    """
    cmd = ["docker", "compose"]
    cmd.extend(args)
    _log.debug("exec command: %s", cmd)
    res = subprocess.run(cmd, capture_output=True, encoding='utf-8')
    _log.debug("result: %s", res)
    return res.stdout


def load_compose(fnames=["docker-compose.yml"]) -> dict:
    """load docker-compose.yml"""
    res = {}
    for f in fnames:
        fname = os.path.join(app.config.get("working_dir", os.getcwd()), f)
        try:
            with open(fname) as ifp:
                d = yaml.safe_load(ifp)
                for k, v in d.items():
                    if k in res:
                        if isinstance(res[k], dict):
                            res[k].update(v)  # add
                        elif isinstance(res[k], list):
                            res[k].extend(v)  # add
                        else:
                            res[k] = v        # override
                    else:
                        res[k] = v
        except Exception:
            _log.exception("load file: %s", fname)
    return res


def get_container_data() -> list[dict]:
    """merge container-data and compose-file"""
    data = json.loads(do_compose("ps", "--format=json", "-a"))
    filedata = load_compose(app.config.get(
        "compose_files", ["docker-compose.yml"]))
    def_buttons = ["up", "compose", "build", "pull"]
    buttons = {
        "running": ["stop", "compose", "logs", "pause", "kill",
                    "pull", "build", "restart", "top", "exec"],
        "exited": ["up", "compose", "logs", "rm", "pull", "build", "run"],
        "paused": ["unpause", "kill", "stop"],
        "disabled": ["up", "compose", "pull", "build"],
    }
    svset = {d.get("Service") for d in data}
    dset = set(filedata.get("services", {}).keys())
    for d in data:
        d["buttons"] = buttons.get(d.get("State"), def_buttons)
        if d.get("Service") in filedata.get("services", {}):
            d["compose"] = filedata.get("services", {}).get(d.get("Service"))
    for k in dset - svset:
        data.append({
            "Service": k, "State": "disabled",
            "compose": filedata.get("services", {}).get(k),
            "buttons": def_buttons,
        })
    return data


@app.route('/')
def index() -> str:
    """index page"""
    data = get_container_data()
    return render_template(
        'index.j2', data=data,
        index_url=url_for('index'))


@app.route("/up/<string:service>")
def do_up(service):
    """execute docker compose up"""
    do_compose("up", "-d", service)
    return redirect(url_for('index'))


@app.route("/stop/<string:service>")
def do_stop(service):
    do_compose("stop", service)
    return redirect(url_for('index'))


@app.route("/rm/<string:service>")
def do_rm(service):
    do_compose("rm", service, "-f")
    return redirect(url_for('index'))


@app.route("/logs/<string:service>")
def do_logs(service):
    res = do_compose("logs", service, "--no-color")
    return render_template(
        'logs.j2', data=res.splitlines(),
        index_url=url_for('index'))


@app.route("/top/<string:service>")
def do_top(service):
    res = do_compose("top", service)
    return render_template(
        'logs.j2', data=res.splitlines(),
        index_url=url_for('index'))


@app.route("/pause/<string:service>")
def do_pause(service):
    do_compose("pause", service)
    return redirect(url_for('index'))


@app.route("/unpause/<string:service>")
def do_unpause(service):
    do_compose("unpause", service)
    return redirect(url_for('index'))


@app.route("/restart/<string:service>")
def do_restart(service):
    do_compose("restart", service)
    return redirect(url_for('index'))


@app.route("/kill/<string:service>")
def do_kill(service):
    do_compose("kill", service)
    return redirect(url_for('index'))


@app.route("/pull/<string:service>")
def do_pull(service):
    do_compose("pull", service)
    return redirect(url_for('index'))


@app.route("/push/<string:service>")
def do_push(service):
    do_compose("push", service)
    return redirect(url_for('index'))


@app.route("/build/<string:service>")
def do_build(service):
    do_compose("build", service)
    return redirect(url_for('index'))


@app.route("/compose/<string:service>")
def do_view_compose(service):
    filedata = load_compose(app.config.get(
        "compose_files", ["docker-compose.yml"]))
    data = filedata.get("services", {}).get(service)
    return render_template(
        'compose.j2', data=data,
        index_url=url_for('index'))


@app.route("/convert/<string:service>")
def do_convert(service):
    res = do_compose("convert", service)
    return render_template(
        'logs.j2', data=res.splitlines(),
        index_url=url_for('index'))


@app.route("/exec/<string:service>", methods=["GET", "POST"])
def do_exec(service):
    data = get_container_data()
    cmd = request.form.get("cmd")
    if cmd is not None:
        res = do_compose("exec", service, *shlex.split(cmd))
    else:
        res = ""
    return render_template(
        'exec.j2', output=res.splitlines(),
        container=data, service=service, command=cmd,
        index_url=url_for('index'))


@app.route("/run/<string:service>", methods=["GET", "POST"])
def do_run(service):
    data = get_container_data()
    cmd = request.form.get("cmd")
    if cmd is not None:
        res = do_compose("run", service, *shlex.split(cmd))
    else:
        res = ""
    return render_template(
        'exec.j2', output=res.splitlines(), container=data,
        service=service, command=cmd,
        index_url=url_for('index'))
