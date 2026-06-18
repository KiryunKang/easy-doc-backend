"""요청 입력/출력 로깅 + 개인정보·민감정보 마스킹.

OCR 텍스트나 분석 결과에는 이름·주민번호·전화·납부번호 등 PII 가 섞일 수 있으므로
로그에 남기기 전 `mask_pii()` 로 가린다. uvicorn 콘솔에 함께 출력된다.
"""
import logging
import re
import sys

# Windows 콘솔 기본 인코딩(cp949)에서 한글 로그가 깨지는 것을 방지
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001 (reconfigure 미지원 환경은 무시)
        pass

logger = logging.getLogger("easydoc")
if not logger.handlers:  # 중복 핸들러 방지(reload 시)
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s [easydoc] %(levelname)s: %(message)s"))
    logger.addHandler(_h)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def _mask_tail(s: str, keep: int = 4) -> str:
    """문자열의 숫자만 추려 뒤 keep 자리만 남기고 마스킹."""
    digits = re.sub(r"\D", "", s)
    if len(digits) <= keep:
        return s
    return "*" * (len(digits) - keep) + digits[-keep:]


# (정규식, 치환) — 위에서부터 순서대로 적용. 더 구체적인 패턴을 먼저.
_RULES = [
    # 주민등록번호: 901231-1234567 → 901231-*******
    (re.compile(r"\b(\d{6})-\d{7}\b"), lambda m: f"{m.group(1)}-*******"),
    # 휴대/일반 전화: 010-1234-5678 → 010-****-5678
    (re.compile(r"\b(\d{2,3})-(\d{3,4})-(\d{4})\b"), lambda m: f"{m.group(1)}-****-{m.group(3)}"),
    # 계좌/전자납부번호 등 4-4-2~4 숫자열: 1234-5678-9012 → ********9012
    (re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{2,4}\b"), lambda m: _mask_tail(m.group(0))),
]

# 이름: "김복순 귀하/님" → "김** 귀하"
_NAME = re.compile(r"([가-힣]{2,4})\s*(귀하|님)")

# 일반 호칭(이름 아님) — 마스킹 제외. "선생님·어머님·사장님" 등 오마스킹 방지.
_TITLE_WORDS = {
    "선생", "어머", "아버", "사장", "회장", "사모", "고객", "환자",
    "손님", "부장", "과장", "차장", "대리", "팀장", "원장", "교수", "박사",
}


def _mask_name(m: "re.Match") -> str:
    name = m.group(1)
    if name in _TITLE_WORDS:  # 일반 호칭이면 그대로 둠
        return m.group(0)
    return name[0] + "*" * (len(name) - 1) + " " + m.group(2)


def mask_pii(text: str) -> str:
    """로그용 PII 마스킹. 원본 데이터는 변경하지 않고 로그 문자열에만 적용."""
    if not text:
        return text
    out = text
    for pattern, repl in _RULES:
        out = pattern.sub(repl, out)
    out = _NAME.sub(_mask_name, out)
    return out
