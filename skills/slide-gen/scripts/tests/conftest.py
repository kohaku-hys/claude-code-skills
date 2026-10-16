"""pytest から流すための包み（2026-10-16 追加）。

ここの test_*.py は、どれも「py <ファイル> で流し、exit 0＝合格」の単体の試験スクリプト。import した時点で試験が走り、
最後に sys.exit するので、pytest の普通の集め方（import して test_ 関数を探す）では import の所で止まってしまう。
そこで pytest には中身を import させず、1ファイル＝1件として子プロセスで流し、exit 0 なら合格にする。試験の中身は変えない。

使い方:  py -m pytest slide-gen/scripts/tests -q
失敗したファイルは、そのスクリプトの出力の最後の60行を見せる（全部見たい時は、そのファイルを py で直接流す）。
"""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TIMEOUT_SEC = 1800   # test_deck_doctor.py は試験集があると数分かかる


def pytest_pycollect_makemodule(module_path, parent):
    # この tests の直下の test_*.py だけを、子プロセスで流す包みに替える（ほかの場所の試験には手を出さない）
    if os.path.dirname(os.path.abspath(str(module_path))) == HERE:
        return ScriptFile.from_parent(parent, path=module_path)
    return None


class ScriptFile(pytest.File):
    def collect(self):
        yield ScriptItem.from_parent(self, name=os.path.basename(str(self.path)))


class ScriptFailed(Exception):
    pass


class ScriptItem(pytest.Item):
    def runtest(self):
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        r = subprocess.run([sys.executable, str(self.path)], cwd=HERE, env=env, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT_SEC)
        out = (r.stdout or "") + (r.stderr or "")
        self.add_report_section("call", "script output", out)
        if r.returncode != 0:
            tail = "\n".join(out.splitlines()[-60:])
            raise ScriptFailed("exit %d\n%s" % (r.returncode, tail))
        # 試すものが無くて全体を飛ばした（作者の修正が入った ppt-master のサーバが無い等）時は skipped と数える
        for line in out.splitlines():
            if line.startswith("[SKIP-ALL]"):
                pytest.skip(line)

    def repr_failure(self, excinfo):
        if isinstance(excinfo.value, ScriptFailed):
            return "%s が失敗した: %s" % (self.name, excinfo.value)
        return super().repr_failure(excinfo)

    def reportinfo(self):
        return self.path, 0, self.name
