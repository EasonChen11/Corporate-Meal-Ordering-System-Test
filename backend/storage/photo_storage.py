"""菜單照片儲存層。

- 不信任 client 提供的 content-type；用 PIL 實際解碼來判型別。
- 一律重新編碼成 JPEG (strip EXIF / SVG 等 payload smuggling 風險)。
- 寫入採 .tmp + os.replace 原子操作，避免 Caddy 看到半寫入檔案。
- Repository 不碰檔案；service 層用 set_photo_path() 把相對路徑寫回 DB。
"""
from __future__ import annotations

import io
import os
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from backend.core.errors import CodedHTTPException

_ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
_DEFAULT_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_DEFAULT_MAX_EDGE = 1600
# 解壓縮炸彈防線：拒絕宣稱像素 > 25M 的圖（5MB PNG 可宣稱 50000x50000 = 25 億像素 → 記憶體 DoS）
_MAX_PIXELS = 25_000_000


class PhotoStorage:
    def __init__(
        self,
        root: Path,
        *,
        max_bytes: int = _DEFAULT_MAX_BYTES,
        max_edge_px: int = _DEFAULT_MAX_EDGE,
    ) -> None:
        self.root = root
        self.max_bytes = max_bytes
        self.max_edge_px = max_edge_px

    def store_menu_photo(self, *, vendor_id: int, item_id: int, data: bytes) -> str:
        """驗證 → 重新編碼 → 原子寫入；回傳 DB 用的相對路徑。"""
        if len(data) > self.max_bytes:
            raise CodedHTTPException(status_code=413, code="image_too_large", detail="image exceeds size limit")

        try:
            with Image.open(io.BytesIO(data)) as img:
                if img.format not in _ALLOWED_FORMATS:
                    raise CodedHTTPException(
                        status_code=415,
                        code="invalid_image_type",
                        detail=f"unsupported image format: {img.format}",
                    )
                # 在 load() 之前先檢查像素數，避免解壓縮炸彈耗盡記憶體
                width, height = img.size
                if width * height > _MAX_PIXELS:
                    raise CodedHTTPException(
                        status_code=413,
                        code="image_too_large",
                        detail=f"image dimensions exceed limit ({width}x{height})",
                    )
                img.load()
                # 轉 RGB 才能存成 JPEG (PNG 可能是 RGBA / palette mode)
                rgb = img.convert("RGB")
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
            # PIL 可能拋多種型別：未識別格式、解壓縮炸彈、檔案截斷等。
            # 一律當成「壞圖」回 415，不洩漏內部 stack trace。
            raise CodedHTTPException(
                status_code=415, code="invalid_image_type", detail="not a recognised image"
            ) from exc

        # 等比例縮到最長邊 = max_edge_px
        if max(rgb.size) > self.max_edge_px:
            ratio = self.max_edge_px / max(rgb.size)
            new_size = (int(rgb.size[0] * ratio), int(rgb.size[1] * ratio))
            rgb = rgb.resize(new_size)

        rel_path = self._relative_path(vendor_id, item_id)
        final_path = self.root / rel_path
        final_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = final_path.with_suffix(final_path.suffix + ".tmp")

        # 先寫 tmp 再 rename — 避免 Caddy 服務到半寫檔案。
        rgb.save(tmp_path, format="JPEG", quality=85, optimize=True)
        os.replace(tmp_path, final_path)
        return rel_path

    def delete_menu_photo(self, *, vendor_id: int, item_id: int) -> None:
        """Best-effort 刪除；檔案不存在不算錯 (idempotent)。"""
        try:
            (self.root / self._relative_path(vendor_id, item_id)).unlink()
        except FileNotFoundError:
            return

    @staticmethod
    def _relative_path(vendor_id: int, item_id: int) -> str:
        return f"vendors/{vendor_id}/menu/{item_id}.jpg"
