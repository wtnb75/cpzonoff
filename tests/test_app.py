import json
import yaml
import unittest
import tempfile
import os
from unittest.mock import patch
from cpzonoff import app


class TestApp(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_index(self):
        cpzres = [{
            "ID": "id123",
            "Name": "name123",
            "Image": "image123",
            "Created": 1670135389,
            "Service": "hello",
        }]
        cpz = {
            "version": "3",
            "services": {
                "hello": {
                    "image": "new_image_123",
                },
                "world": {
                    "image": "world123",
                }
            }
        }
        with patch("cpzonoff.app.do_compose") as docmp, patch("cpzonoff.app.load_compose") as load:
            load.return_value = cpz
            docmp.return_value = json.dumps(cpzres)
            res = app.app.test_client().get("/")
            self.assertEqual(200, res.status_code)
            self.assertIn("2022-12-04", res.text)
            self.assertIn("name123", res.text)
            self.assertIn("image123", res.text)
            self.assertNotIn("new_image_123", res.text)
            self.assertIn("world", res.text)
            load.assert_called_once_with(['docker-compose.yml'])
            docmp.assert_called_once_with('ps', '--format=json', '-a')

    def _any_compose(self, cmd, ctn, *options):
        with patch("cpzonoff.app.do_compose") as docmp:
            docmp.return_value = ""
            res = app.app.test_client().get(f"/{cmd}/{ctn}")
            self.assertEqual(302, res.status_code)
            self.assertEqual("/", res.location)
            docmp.assert_called_once_with(cmd, *options)

    def test_up(self):
        self._any_compose("up", "abc", "-d", "abc")

    def test_stop(self):
        self._any_compose("stop", "abc", "abc")

    def test_restart(self):
        self._any_compose("restart", "abc", "abc")

    def test_rm(self):
        self._any_compose("rm", "abc", "abc", "-f")

    def test_pause(self):
        self._any_compose("pause", "abc", "abc")

    def test_unpause(self):
        self._any_compose("unpause", "abc", "abc")

    def test_kill(self):
        self._any_compose("kill", "abc", "abc")

    def test_pull(self):
        self._any_compose("pull", "abc", "abc")

    def test_push(self):
        self._any_compose("push", "abc", "abc")

    def test_load_compose(self):
        cpz1 = {
            "version": "3",
            "services": {
                "hello": {
                    "image": "new_image_123",
                },
                "world": {
                    "image": "world123",
                }
            }
        }
        cpz2 = {
            "version": "3.1",
            "services": {
                "hello2": {
                    "image": "new_image_123",
                },
                "world": {
                    "image": "world123_2",
                }
            }
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "docker-compose.yml"), "w") as cpzf1:
                yaml.dump(cpz1, stream=cpzf1)
            with open(os.path.join(tmpdir, "docker-compose-2.yml"), "w") as cpzf2:
                yaml.dump(cpz2, stream=cpzf2)
            app.app.config["working_dir"] = tmpdir
            res = app.load_compose(
                ["docker-compose.yml", "docker-compose-2.yml"])
            self.assertEqual("3.1", res["version"])
            self.assertEqual(
                "new_image_123", res["services"]["hello2"]["image"])
            self.assertEqual("world123_2", res["services"]["world"]["image"])

    def test_compose(self):
        with patch("subprocess.run") as run:
            run.return_value.stdout = "hello"
            res = app.do_compose("hello", "world")
            run.assert_called_once_with(
                ["docker", "compose", "hello", "world"], capture_output=True, encoding="utf-8")
            self.assertEqual("hello", res)
