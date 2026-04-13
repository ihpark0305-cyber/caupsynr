-- ══════════════════════════════════════════════════════════════
-- TSL Portal — Supabase Migration v2
-- 신기능 B/C/D 대응 컬럼 추가
-- Supabase Dashboard → SQL Editor 에서 실행
-- ══════════════════════════════════════════════════════════════

-- portal_files: 컬럼 스키마 + 행 수
ALTER TABLE portal_files ADD COLUMN IF NOT EXISTS column_schema TEXT DEFAULT '[]';
ALTER TABLE portal_files ADD COLUMN IF NOT EXISTS row_count INTEGER DEFAULT 0;

-- measurements: 업로드 파일 출처 추적
ALTER TABLE measurements ADD COLUMN IF NOT EXISTS source_file_id TEXT;

-- 인덱스 (파일별 측정 조회 최적화)
CREATE INDEX IF NOT EXISTS idx_m_source_file ON measurements(source_file_id);
