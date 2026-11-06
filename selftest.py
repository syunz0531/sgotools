# -*- coding: utf-8 -*-
"""설치 후 실제 서버에 붙여 패키지가 동작하는지 확인한다.

하는 일
  1. sgotools 를 불러온다
  2. download_snapshot() 으로 NHTSA 서버에서 새로 내려받는다
  3. load_incidents() 로 읽어 단계별 건수를 찍는다
  4. 앞서 run_download.bat 으로 받아 둔 11-06 사본과 해시를 비교한다
     (해시가 다르면 그 사이에 NHTSA가 파일을 교체했다는 뜻이고,
      그것 자체가 이 패키지가 필요한 이유를 보여 주는 기록이 된다)
"""
import json
import sys
import warnings
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent                      # ...\av_crash_data
OLD_SNAPSHOT = PROJECT / "raw" / "snapshot_2026-11-06"
NEW_SNAPSHOT = PROJECT / "raw" / ("snapshot_selftest_" + datetime.now().strftime("%Y-%m-%d"))


def main():
    print("1) 패키지 불러오기")
    try:
        import sgotools as sgo
    except ImportError as exc:
        print("   실패:", exc)
        print("   먼저 이 폴더에서 'pip install -e .' 를 실행해야 한다.")
        return 1
    print("   OK  버전", sgo.__version__)

    print()
    print("2) 실제 서버에서 내려받기 ->", NEW_SNAPSHOT.name)
    snap = sgo.download_snapshot(NEW_SNAPSHOT)
    manifest = snap.manifest or {"files": []}
    ok = [f for f in manifest["files"] if f.get("status") == "ok"]
    for f in manifest["files"]:
        state = f.get("status")
        size = f.get("bytes", 0)
        print(f"   {state:6s} {f['name']:26s} {size:>10,d} bytes")
    print(f"   {len(ok)}/{len(manifest['files'])} 성공")
    if len(ok) < len(manifest["files"]):
        print("   일부 실패. 위 메시지를 확인할 것.")
        return 1

    print()
    print("3) 읽어서 단계별 건수 확인")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df = sgo.load_incidents(snap, regime="current", categories=["ADS"])
    prov = df.attrs["provenance"]
    for step in prov.steps:
        print(f"   {step.name:20s} {step.rows_before:7,d} -> {step.rows_after:7,d}")
    print()
    print("   [논문용 문장]")
    print("  ", prov.methods_sentence())

    print()
    print("4) 11-06 사본과 해시 비교")
    old_manifest = OLD_SNAPSHOT / "manifest.json"
    if not old_manifest.exists():
        print("   이전 사본이 없어 건너뜀:", OLD_SNAPSHOT)
        return 0
    old = {f["name"]: f.get("sha256") for f in
           json.loads(old_manifest.read_text(encoding="utf-8"))["files"]}
    changed = []
    for f in manifest["files"]:
        before, after = old.get(f["name"]), f.get("sha256")
        if before is None:
            continue
        mark = "같음" if before == after else "*** 바뀜 ***"
        if before != after:
            changed.append(f["name"])
        print(f"   {f['name']:26s} {mark}")
    print()
    if changed:
        print("   공개본이 바뀌었다:", ", ".join(changed))
        print("   두 사본을 모두 보관할 것. 논문의 근거 자료가 된다.")
    else:
        print("   모두 동일. 아직 같은 공개본이다.")

    print()
    print("=== 끝. 이 창을 닫아도 됩니다 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
