-- Draft migration for vendor self-service backend.
-- DB team to review, adapt to their conventions, and merge into the canonical
-- migrations directory. Until then, application repositories run on in-memory
-- stubs — no production data depends on this file existing in the DB.

-- 商家 (vendors) 表預設只有 (id, name, contact_email, status, *_at)。
-- vendor self-service 需要這些額外欄位 — DB 組請確認後納入或單獨 migrate。
ALTER TABLE vendors
  ADD COLUMN IF NOT EXISTS address          TEXT,
  ADD COLUMN IF NOT EXISTS business_hours   TEXT,
  ADD COLUMN IF NOT EXISTS contact_phone    TEXT,
  ADD COLUMN IF NOT EXISTS owner_user_id    BIGINT REFERENCES users(id);

CREATE TABLE IF NOT EXISTS menu_categories (
  id          BIGSERIAL PRIMARY KEY,
  vendor_id   BIGINT NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  sort_order  INT NOT NULL DEFAULT 0,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (vendor_id, name)
);
CREATE INDEX ON menu_categories (vendor_id, sort_order);

CREATE TABLE IF NOT EXISTS menu_items (
  id           BIGSERIAL PRIMARY KEY,
  vendor_id    BIGINT NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
  category_id  BIGINT REFERENCES menu_categories(id) ON DELETE SET NULL,
  name         TEXT NOT NULL,
  description  TEXT,
  price_cents  INT NOT NULL CHECK (price_cents >= 0),
  available    BOOLEAN NOT NULL DEFAULT true,
  daily_quota  INT CHECK (daily_quota IS NULL OR daily_quota >= 0),  -- 每日最大供應份數，NULL = 不限
  photo_path   TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON menu_items (vendor_id, category_id);
CREATE INDEX ON menu_items (vendor_id) WHERE available;

-- 多廠區關聯：committee 模組寫入，vendor backend 唯讀。
CREATE TABLE IF NOT EXISTS facilities (
  id    BIGSERIAL PRIMARY KEY,
  code  TEXT NOT NULL UNIQUE,    -- 廠區代號，例: 'F12A'
  name  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vendor_facilities (
  vendor_id    BIGINT NOT NULL REFERENCES vendors(id)    ON DELETE CASCADE,
  facility_id  BIGINT NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
  PRIMARY KEY (vendor_id, facility_id)
);
CREATE INDEX ON vendor_facilities (facility_id);
