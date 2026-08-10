-- Mind Mate 후속조사(f/u) 응답 로그 테이블
-- Supabase SQL Editor에서 실행하세요.
--
-- 설문 문항 스키마가 유동적이므로, 앱스 스크립트가 넘긴 응답 전체는
-- data(JSONB)에 그대로 저장하고, 흔한 식별 필드만 별도 컬럼으로 둡니다.
CREATE TABLE IF NOT EXISTS mindmate_followup (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id     UUID,
    user_name      TEXT,
    followup_round TEXT,          -- 회차/wave (있을 경우)
    submitted_at   TEXT,          -- 응답 제출 시각(앱스 스크립트 원본 문자열)
    source         TEXT DEFAULT 'apps_script',
    data           JSONB DEFAULT '{}',   -- 설문 응답 전체(문항→답변)
    received_at    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mindmate_project  ON mindmate_followup(project_id);
CREATE INDEX IF NOT EXISTS idx_mindmate_user     ON mindmate_followup(user_name);
CREATE INDEX IF NOT EXISTS idx_mindmate_received ON mindmate_followup(received_at DESC);
