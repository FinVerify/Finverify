"""Minimal offline stand-in for the subset of pytest used by this repo's tests.

This sandbox has no network access to install real pytest (see
requirements.txt). This shim implements only what the test files actually
use: pytest.raises, pytest.approx, pytest.mark.parametrize, and the
tmp_path/monkeypatch fixtures. It is dev tooling, not shipped/used at
runtime, and is not a replacement for running the real pytest in CI.
"""
from __future__ import annotations

import contextlib
import inspect
import os
import re
import shutil
import sys
import tempfile
import traceback
import types


class _Approx:
    def __init__(self, value, rel=1e-6, abs=1e-12):
        self.value = value
        self.rel = rel
        self.abs = abs

    def __eq__(self, other):
        try:
            return abs(other - self.value) <= max(self.abs, self.rel * abs(self.value))
        except TypeError:
            return NotImplemented

    def __repr__(self):
        return "approx(%r)" % (self.value,)


def approx(value, rel=1e-6, abs=1e-12):
    return _Approx(value, rel=rel, abs=abs)


class raises:
    def __init__(self, exc_type, match=None):
        self.exc_type = exc_type
        self.match = match
        self.value = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            raise AssertionError("expected %r to be raised, nothing was raised" % (self.exc_type,))
        if not issubclass(exc_type, self.exc_type):
            return False
        if self.match and not re.search(self.match, str(exc_val)):
            raise AssertionError("exception message %r did not match %r" % (str(exc_val), self.match))
        self.value = exc_val
        return True


class _Mark:
    @staticmethod
    def parametrize(argnames, argvalues):
        names = [n.strip() for n in argnames.split(",")]

        def decorator(fn):
            fn.__parametrize__ = (names, argvalues)
            return fn
        return decorator

    @staticmethod
    def skip(reason=""):
        def decorator(fn):
            fn.__skip__ = reason
            return fn
        return decorator


class _Fail(Exception):
    pass


def fail(msg=""):
    raise _Fail(msg)


def install() -> None:
    if "pytest" in sys.modules:
        return
    module = types.ModuleType("pytest")
    module.raises = raises
    module.approx = approx
    module.mark = _Mark()
    module.fail = fail
    module.fixture = lambda *a, **k: (a[0] if a and callable(a[0]) else (lambda f: f))
    sys.modules["pytest"] = module


def _make_tmp_path():
    d = tempfile.mkdtemp(prefix="finverify_test_")
    import pathlib
    return pathlib.Path(d)


class _MonkeyPatch:
    def __init__(self):
        self._undo = []

    def setattr(self, target, name, value):
        if isinstance(target, str):
            mod_name, attr = target.rsplit(".", 1)
            obj = sys.modules[mod_name]
            name = attr
        else:
            obj = target
        old = getattr(obj, name)
        self._undo.append((obj, name, old))
        setattr(obj, name, value)

    def setenv(self, name, value):
        old = os.environ.get(name)
        self._undo.append((os.environ, name, old))
        os.environ[name] = value

    def undo(self):
        for obj, name, old in reversed(self._undo):
            if obj is os.environ:
                if old is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = old
            else:
                setattr(obj, name, old)
        self._undo.clear()


def run_module(path: str) -> bool:
    """Collect and run test_* functions in a module file. Returns True if all passed."""
    install()
    import importlib.util
    spec = importlib.util.spec_from_file_location("_target_test_module_" + os.path.basename(path), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    total = 0
    failed = 0
    tmp_dirs = []
    for name in dir(mod):
        if not name.startswith("test_"):
            continue
        fn = getattr(mod, name)
        if not inspect.isfunction(fn):
            continue
        if getattr(fn, "__skip__", None) is not None:
            continue
        param = getattr(fn, "__parametrize__", None)
        cases = [()]
        names = []
        if param:
            names, values = param
            cases = values
        for case in cases:
            kwargs = {}
            if names:
                case_tuple = case if isinstance(case, tuple) else (case,)
                kwargs.update(dict(zip(names, case_tuple)))
            sig = inspect.signature(fn)
            mp = None
            for pname in sig.parameters:
                if pname in kwargs:
                    continue
                if pname == "tmp_path":
                    p = _make_tmp_path()
                    tmp_dirs.append(p)
                    kwargs[pname] = p
                elif pname == "monkeypatch":
                    mp = _MonkeyPatch()
                    kwargs[pname] = mp
            total += 1
            label = name + (("[" + ",".join(map(str, case if isinstance(case, tuple) else (case,))) + "]") if names else "")
            try:
                fn(**kwargs)
                print("PASS", label)
            except Exception:
                failed += 1
                print("FAIL", label)
                traceback.print_exc()
            finally:
                if mp is not None:
                    mp.undo()
    for p in tmp_dirs:
        shutil.rmtree(p, ignore_errors=True)
    print("--- %s: %d run, %d failed ---" % (path, total, failed))
    return failed == 0


if __name__ == "__main__":
    ok = True
    for path in sys.argv[1:]:
        ok = run_module(path) and ok
    sys.exit(0 if ok else 1)
