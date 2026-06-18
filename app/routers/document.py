import asyncio

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas import AnalyzeTextRequest, ProcessResponse
from app.services import analysis, ocr, translation
from app.services.rag import get_engine

router = APIRouter(prefix="/api", tags=["document"])


async def _run_pipeline(text: str) -> ProcessResponse:
    # 분석 + 쉬운말 번역을 병렬로 실행
    analysis_result, easy_text = await asyncio.gather(
        analysis.analyze(text),
        translation.to_easy_korean(text),
    )
    matched = await get_engine().match(analysis_result)
    return ProcessResponse(
        ocr_text=text,
        analysis=analysis_result,
        easy_translation=easy_text,
        matched_policies=matched,
    )


@router.post("/process", response_model=ProcessResponse)
async def process_document(file: UploadFile = File(...)):
    """사진 업로드 → OCR → (분석 ∥ 쉬운말 번역) → 혜택 정책 매칭."""
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="이미지 파일만 업로드할 수 있습니다.")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")

    try:
        ocr_text = await ocr.extract_text(image_bytes)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"OCR 처리 실패: {e}")

    if not ocr_text.strip():
        raise HTTPException(status_code=422, detail="문서에서 글자를 찾지 못했습니다.")

    return await _run_pipeline(ocr_text)


@router.post("/analyze-text", response_model=ProcessResponse)
async def analyze_text(req: AnalyzeTextRequest):
    """OCR 없이 텍스트만으로 파이프라인 실행 (프론트엔드 개발/테스트용)."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text 가 비어 있습니다.")
    return await _run_pipeline(req.text)
