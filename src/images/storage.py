"""
Tenant-isolated image storage manager.
Ensures image files are written into distinct folders partitioned by org_id.
"""
from __future__ import annotations

import base64
import os
import uuid
from pathlib import Path
from src.config import get_settings


class TenantImageStorage:
    def __init__(self):
        self.settings = get_settings()
        self.base_dir = Path(self.settings.image_storage_dir)

    def save_image_b64(self, org_id: str, record_id: str, b64_str: str) -> str:
        """
        Stores image inside storage/images/{org_id}/{record_id}_{uuid}.jpg
        Returns relative internal storage path.
        """
        tenant_dir = self.base_dir / org_id
        tenant_dir.mkdir(parents=True, exist_ok=True)

        if b64_str.startswith("data:image"):
            b64_str = b64_str.split(",", 1)[1]

        try:
            data = base64.b64decode(b64_str)
        except Exception:
            # Fallback if raw text or placeholder
            data = b64_str.encode("utf-8")

        filename = f"{record_id}_{uuid.uuid4().hex[:8]}.jpg"
        target_path = tenant_dir / filename
        with open(target_path, "wb") as f:
            f.write(data)

        # Return standardized relative path
        return f"storage/images/{org_id}/{filename}"
