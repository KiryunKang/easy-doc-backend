#!/usr/bin/env python
"""팀원 corpus 를 우리 백엔드 12필드 스키마로 변환.

팀원(origin/main)은 corpus 를 다른 스키마(title/benefit/apply/signals/priority(int) ...)로
관리한다. 우리 rag.py 는 12필드 스키마(name/amount/how_to_apply/keywords(공백)/priority(str) ...)를
읽으므로, 팀원 데이터를 받을 때마다 이 스크립트로 변환한다.

사용 예:
  git show origin/main:data/corpus.json | python scripts/convert_team_corpus.py - data/corpus.json
  python scripts/convert_team_corpus.py team_corpus.json data/corpus.json

phone/visit/related_doc_types 는 팀원 데이터에 있으면 그대로 가져오고, 없으면 빈값으로 둔다.
(현재 팀원 corpus 엔 phone/visit 가 없어 빈값 → 채워서 푸시하면 자동 반영됨)
"""
import json
import sys


def priority(n):
    """팀원 priority(int 1~5) → 우리 priority(str). 이미 str 이면 그대로."""
    if isinstance(n, str):
        return n
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "medium"
    return "high" if n <= 2 else ("medium" if n == 3 else "low")


def keywords(p):
    """keywords + signals 를 공백 구분 문자열로 합침(중복 제거).

    keywords 가 list(팀원 원본)든 공백 문자열(우리 변환본)이든 모두 처리 →
    같은 입력을 두 번 변환해도 결과가 같다(idempotent)."""
    kws = p.get("keywords") or []
    if isinstance(kws, str):
        kws = kws.split()
    sigs = p.get("signals") or []
    seen, out = set(), []
    for w in list(kws) + list(sigs):
        w = str(w).strip()
        if w and w not in seen:
            seen.add(w)
            out.append(w)
    return " ".join(out)


def convert(p):
    return {
        "id": str(p.get("id", "")),
        "name": p.get("title") or p.get("name", ""),
        "category": p.get("category", ""),
        "eligibility": p.get("eligibility", ""),
        "keywords": keywords(p),
        "related_doc_types": p.get("related_doc_types") or [],
        "amount": p.get("benefit") or p.get("amount", ""),
        "how_to_apply": p.get("apply") or p.get("how_to_apply", ""),
        "phone": p.get("phone", ""),
        "visit": p.get("visit", ""),
        "source": p.get("source", ""),
        "priority": priority(p.get("priority")),
    }


def main():
    src_path = sys.argv[1] if len(sys.argv) > 1 else "-"
    dst_path = sys.argv[2] if len(sys.argv) > 2 else "data/corpus.json"

    if src_path == "-":
        raw = sys.stdin.buffer.read().decode("utf-8")  # 파이프 인코딩 깨짐 방지
    else:
        raw = open(src_path, encoding="utf-8").read()
    out = [convert(p) for p in json.loads(raw)]

    with open(dst_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    ph = sum(1 for p in out if p["phone"].strip())
    vi = sum(1 for p in out if p["visit"].strip())
    print(f"변환 {len(out)}건 → {dst_path}  (phone {ph}/{len(out)}, visit {vi}/{len(out)})")


if __name__ == "__main__":
    main()
