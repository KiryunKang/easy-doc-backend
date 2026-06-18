import asyncio

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.logging_utils import logger, mask_pii
from app.schemas import AnalyzeTextRequest, ProcessResponse
from app.services import analysis, ocr, translation
from app.services.rag import get_engine

router = APIRouter(prefix="/api", tags=["document"])

_LOG_PREVIEW = 300  # 로그에 남길 텍스트 최대 길이(민감정보는 마스킹됨)


def _preview(text: str) -> str:
    # 마스킹 후 줄바꿈을 한 줄로 정리(로그 한 레코드 = 한 줄)
    masked = mask_pii(text[:_LOG_PREVIEW]).replace("\n", " ⏎ ")
    return masked + ("…" if len(text) > _LOG_PREVIEW else "")


async def _run_pipeline(text: str, source: str) -> ProcessResponse:
    # 입력 로깅 (마스킹)
    logger.info("[%s] 입력 텍스트(%d자): %s", source, len(text), _preview(text))

    # 분석 + 쉬운말 번역을 병렬로 실행
    analysis_result, easy_text = await asyncio.gather(
        analysis.analyze(text),
        translation.to_easy_korean(text),
    )
    matched = await get_engine().match(analysis_result)

    # 출력 로깅 (마스킹)
    logger.info(
        "[%s] 분석결과: doc_type=%s | sender=%s | amount=%s | deadline=%s",
        source,
        analysis_result.doc_type,
        mask_pii(analysis_result.sender),
        analysis_result.amount,
        analysis_result.deadline,
    )
    logger.info("[%s] 쉬운번역(%d자): %s", source, len(easy_text), _preview(easy_text))
    logger.info(
        "[%s] 매칭 정책 %d건: %s",
        source,
        len(matched),
        [f"{p.id}({p.score})" for p in matched],
    )

    return ProcessResponse(
        ocr_text=text,
        analysis=analysis_result,
        easy_translation=easy_text,
        matched_policies=matched,
    )


@router.post("/process", response_model=ProcessResponse)
async def process_document(file: UploadFile = File(...)):
    """사진 업로드 → OCR → (분석 ∥ 쉬운말 번역) → 혜택 정책 매칭."""
    logger.info(
        "[process] 이미지 수신: filename=%s content_type=%s",
        file.filename,
        file.content_type,
    )
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="이미지 파일만 업로드할 수 있습니다.")

    image_bytes = await file.read()
    logger.info("[process] 이미지 크기: %d bytes", len(image_bytes))
    if not image_bytes:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")

    try:
        ocr_text = await ocr.extract_text(
            image_bytes, file.content_type or "image/jpeg"
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("[process] OCR 처리 실패")
        raise HTTPException(status_code=502, detail=f"OCR 처리 실패: {e}")

    logger.info("[process] OCR 추출(%d자): %s", len(ocr_text), _preview(ocr_text))
    if not ocr_text.strip():
        raise HTTPException(status_code=422, detail="문서에서 글자를 찾지 못했습니다.")

    return await _run_pipeline(ocr_text, source="process")


@router.post("/analyze-text", response_model=ProcessResponse)
async def analyze_text(req: AnalyzeTextRequest):
    """OCR 없이 텍스트만으로 파이프라인 실행 (프론트엔드 개발/테스트용)."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text 가 비어 있습니다.")
    return await _run_pipeline(req.text, source="analyze-text")
