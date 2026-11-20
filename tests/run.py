"""零依赖测试运行器：不需要 pytest。

用法：python tests/run.py
容器里的 test_* 函数会被自动发现；带 tmp_path 参数的会拿到一个临时目录。
"""
import inspect
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_core  # noqa: E402


def main():
    tests = [(n, f) for n, f in inspect.getmembers(test_core, inspect.isfunction)
             if n.startswith("test_")]
    passed = failed = 0
    for name, fn in tests:
        params = inspect.signature(fn).parameters
        try:
            if "tmp_path" in params:
                with tempfile.TemporaryDirectory() as d:
                    fn(Path(d))
            else:
                fn()
            print("PASS", name)
            passed += 1
        except Exception:
            print("FAIL", name)
            traceback.print_exc()
            failed += 1
    print("\n%d passed, %d failed, %d total" % (passed, failed, passed + failed))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
