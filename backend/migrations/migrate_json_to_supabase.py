#!/usr/bin/env python3
"""
One-time migration: JSON file storage -> Supabase PostgreSQL + Storage.

Reads data/projects.json and uploads everything to Supabase:
- Project rows -> projects table
- Improvement markers -> improvement_markers table
- Disk images -> Supabase Storage bucket (project-images)
- Base64 generated images -> decoded and uploaded to Storage
- Image records -> project_images table

Features:
- Batch processing with configurable batch size
- Checkpoint file for resuming interrupted migrations
- --dry-run mode (preview only)
- --verify mode (compare JSON vs Supabase)
- Idempotent: skips already-migrated projects

Usage:
  python migrate_json_to_supabase.py --dry-run       # Preview only
  python migrate_json_to_supabase.py                  # Execute migration
  python migrate_json_to_supabase.py --verify         # Compare JSON vs Supabase
  python migrate_json_to_supabase.py --batch-size 25  # Custom batch size

Environment:
  SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.
"""

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

# Add parent dir to path so we can import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase_client import get_supabase_client, is_supabase_configured

BATCH_SIZE = 50
CHECKPOINT_FILE = Path("data/migration_checkpoint.json")
JSON_DATA_FILE = Path("data/projects.json")
IMAGES_DIR = Path("data/images")
STORAGE_BUCKET = "project-images"


class MigrationRunner:
    def __init__(self, dry_run: bool = False, batch_size: int = BATCH_SIZE):
        self.dry_run = dry_run
        self.batch_size = batch_size
        self.stats = {
            "total": 0,
            "migrated": 0,
            "skipped": 0,
            "errors": 0,
            "images_uploaded": 0,
            "base64_extracted": 0,
        }
        self.errors: list = []
        self.checkpoint = self._load_checkpoint()

        if not dry_run:
            if not is_supabase_configured():
                print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
                sys.exit(1)
            self.supabase = get_supabase_client()
        else:
            self.supabase = None

    def _load_checkpoint(self) -> set:
        if CHECKPOINT_FILE.exists():
            return set(json.loads(CHECKPOINT_FILE.read_text()))
        return set()

    def _save_checkpoint(self):
        CHECKPOINT_FILE.parent.mkdir(exist_ok=True)
        CHECKPOINT_FILE.write_text(json.dumps(list(self.checkpoint), indent=2))

    # =========================================================================
    # MAIN ENTRY POINTS
    # =========================================================================

    def run(self):
        """Execute the migration."""
        if not JSON_DATA_FILE.exists():
            print(f"ERROR: {JSON_DATA_FILE} not found")
            sys.exit(1)

        projects = json.loads(JSON_DATA_FILE.read_text())
        self.stats["total"] = len(projects)

        print(f"\n{'='*60}")
        print(f"{'DRY RUN - ' if self.dry_run else ''}JSON -> Supabase Migration")
        print(f"{'='*60}")
        print(f"Total projects: {self.stats['total']}")
        print(f"Already migrated (checkpoint): {len(self.checkpoint)}")
        print(f"Batch size: {self.batch_size}")
        print()

        batch = []
        for project_id, project_data in projects.items():
            if project_id in self.checkpoint:
                self.stats["skipped"] += 1
                continue

            batch.append((project_id, project_data))

            if len(batch) >= self.batch_size:
                self._process_batch(batch)
                batch = []

        if batch:
            self._process_batch(batch)

        self._print_summary()

    def verify(self):
        """Compare JSON data against Supabase data."""
        if not JSON_DATA_FILE.exists():
            print(f"ERROR: {JSON_DATA_FILE} not found")
            sys.exit(1)

        projects = json.loads(JSON_DATA_FILE.read_text())
        supabase = get_supabase_client()

        print(f"\n{'='*60}")
        print(f"Verification: JSON vs Supabase")
        print(f"{'='*60}")
        print(f"Total projects in JSON: {len(projects)}")

        mismatches = 0
        missing = 0
        verified = 0

        for project_id, project_data in projects.items():
            result = (
                supabase.table("projects")
                .select("id, status, user_id, space_type")
                .eq("id", project_id)
                .maybe_single()
                .execute()
            )

            if not result.data:
                print(f"  MISSING in Supabase: {project_id}")
                missing += 1
                continue

            row = result.data
            json_status = project_data.get("status", "NEW")
            json_user = project_data.get("user_id", "")

            issues = []
            if row["status"] != json_status:
                issues.append(f"status: JSON={json_status} DB={row['status']}")
            if str(row.get("user_id", "")) != str(json_user):
                issues.append(f"user_id: JSON={json_user} DB={row.get('user_id')}")

            if issues:
                print(f"  MISMATCH {project_id}: {'; '.join(issues)}")
                mismatches += 1
            else:
                verified += 1

        # Check images
        images_result = supabase.table("project_images").select("id", count="exact").execute()
        image_count = images_result.count or 0

        print(f"\nResults:")
        print(f"  Verified OK: {verified}")
        print(f"  Missing:     {missing}")
        print(f"  Mismatches:  {mismatches}")
        print(f"  Images in DB: {image_count}")
        print(f"  Total:       {len(projects)}")

        if missing == 0 and mismatches == 0:
            print("\nVERIFICATION PASSED")
        else:
            print("\nVERIFICATION FAILED")

    # =========================================================================
    # BATCH PROCESSING
    # =========================================================================

    def _process_batch(self, batch: list):
        print(f"\nProcessing batch of {len(batch)} projects...")

        for project_id, project_data in batch:
            try:
                self._migrate_project(project_id, project_data)
                self.checkpoint.add(project_id)
                self.stats["migrated"] += 1
                print(f"  OK {project_id[:12]}... ({project_data.get('status', 'NEW')})")
            except Exception as e:
                self.stats["errors"] += 1
                error_msg = f"{project_id}: {str(e)}"
                self.errors.append(error_msg)
                print(f"  ERROR {project_id[:12]}...: {e}")

        if not self.dry_run:
            self._save_checkpoint()

    # =========================================================================
    # SINGLE PROJECT MIGRATION
    # =========================================================================

    def _migrate_project(self, project_id: str, project_data: dict):
        """Migrate a single project: DB row + images to storage."""
        user_id = project_data.get("user_id")
        
        # Skip legacy projects without user_id (pre-auth data)
        if not user_id:
            raise ValueError("Skipping legacy project without user_id (pre-auth data)")
        
        status = project_data.get("status", "NEW")
        created_at = project_data.get("created_at")
        context = project_data.get("context", {})

        # 1. Build project row
        row = {
            "id": project_id,
            "user_id": user_id,
            "status": status,
            "space_type": context.get("space_type"),
            "improvement_mode": context.get("improvement_mode"),
            "is_base_image_empty_room": context.get("is_base_image_empty_room"),
            "inspiration_images_skipped": context.get("inspiration_images_skipped", False),
            "color_analysis_skipped": context.get("color_analysis_skipped", False),
            "style_analysis_skipped": context.get("style_analysis_skipped", False),
            # String arrays
            "marker_recommendations": context.get("marker_recommendations") or [],
            "inspiration_recommendations": context.get("inspiration_recommendations") or [],
            "product_recommendations": context.get("product_recommendations") or [],
            "selected_product_recommendations": context.get("selected_product_recommendations") or [],
            "preferred_stores": context.get("preferred_stores") or [],
            # JSONB
            "color_analysis": context.get("color_analysis"),
            "style_analysis": context.get("style_analysis"),
            "color_scheme": context.get("color_scheme"),
            "design_style": context.get("design_style"),
            "pre_searched_categories": context.get("pre_searched_categories") or {},
            "product_search_results": context.get("product_search_results") or [],
            "selected_products": context.get("selected_products") or [],
            "favorite_products": context.get("favorite_products") or [],
            "selected_trending_products": context.get("selected_trending_products") or [],
            # Text metadata
            "generation_prompt": context.get("generation_prompt"),
            "generation_model_used": context.get("generation_model_used"),
            "inspiration_generation_prompt": context.get("inspiration_generation_prompt"),
            "inspiration_model_used": context.get("inspiration_model_used"),
        }

        # Add created_at if available
        if created_at:
            row["created_at"] = created_at

        if not self.dry_run:
            self.supabase.table("projects").upsert(row).execute()

        # 2. Migrate markers
        self._migrate_markers(project_id, user_id, context)

        # 3. Upload images
        self._migrate_images(project_id, user_id, context)

    def _migrate_markers(self, project_id: str, user_id: str, context: dict):
        """Migrate improvement markers to the markers table."""
        markers = context.get("improvement_markers", [])
        if not markers:
            return

        for i, marker in enumerate(markers):
            position = marker.get("position", {})
            marker_row = {
                "project_id": project_id,
                "user_id": user_id,
                "marker_id": marker.get("id", str(i)),
                "position_x": position.get("x", 0.5),
                "position_y": position.get("y", 0.5),
                "description": marker.get("description", ""),
                "color": marker.get("color", "red"),
                "sort_order": i,
            }

            if not self.dry_run:
                self.supabase.table("improvement_markers").upsert(
                    marker_row, on_conflict="project_id,marker_id"
                ).execute()

    def _migrate_images(self, project_id: str, user_id: str, context: dict):
        """Upload disk images to Supabase Storage and record in project_images."""
        # Base image
        base_path = context.get("base_image")
        if base_path:
            self._upload_file(project_id, user_id, base_path, "base")

        # Labelled image
        labelled_path = context.get("labelled_base_image")
        if labelled_path:
            self._upload_file(project_id, user_id, labelled_path, "labelled")

        # Inspiration images
        for i, img_path in enumerate(context.get("inspiration_images") or []):
            self._upload_file(project_id, user_id, img_path, "inspiration", sort_order=i)

        # Generated images (base64 -> decode -> upload to Storage)
        for field, img_type in [
            ("generated_image_base64", "generated"),
            ("inspiration_generated_image_base64", "inspiration_generated"),
        ]:
            b64_data = context.get(field)
            if b64_data and len(b64_data) > 100:  # Skip empty/placeholder values
                self._upload_base64(project_id, user_id, b64_data, img_type)

    def _upload_file(
        self, project_id: str, user_id: str, local_path: str,
        image_type: str, sort_order: int = 0
    ):
        """Upload a local file to Supabase Storage."""
        # Resolve relative paths
        path = Path(local_path)
        if not path.is_absolute():
            if local_path.startswith("data/"):
                path = Path(local_path)
            else:
                path = Path("data") / path

        if not path.exists():
            return  # Skip missing files silently

        filename = path.name
        storage_path = f"{project_id}/{image_type}/{filename}"

        if self.dry_run:
            self.stats["images_uploaded"] += 1
            return

        try:
            with open(path, "rb") as f:
                file_bytes = f.read()

            # Determine mime type
            suffix = path.suffix.lower()
            mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".heic": "image/heic"}
            mime_type = mime_map.get(suffix, "image/jpeg")

            self.supabase.storage.from_(STORAGE_BUCKET).upload(
                storage_path, file_bytes, {"content-type": mime_type}
            )

            public_url = self.supabase.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)

            self.supabase.table("project_images").insert({
                "project_id": project_id,
                "user_id": user_id,
                "image_type": image_type,
                "storage_path": storage_path,
                "public_url": public_url,
                "original_filename": filename,
                "mime_type": mime_type,
                "file_size_bytes": len(file_bytes),
                "sort_order": sort_order,
            }).execute()

            self.stats["images_uploaded"] += 1

        except Exception as e:
            # Don't fail the whole project for a single image
            print(f"    WARN: Failed to upload {storage_path}: {e}")

    def _upload_base64(
        self, project_id: str, user_id: str, b64_data: str, image_type: str
    ):
        """Decode base64 image and upload to Storage."""
        if self.dry_run:
            self.stats["base64_extracted"] += 1
            return

        try:
            image_bytes = base64.b64decode(b64_data)
            filename = f"{image_type}_{project_id[:8]}.png"
            storage_path = f"{project_id}/{image_type}/{filename}"

            self.supabase.storage.from_(STORAGE_BUCKET).upload(
                storage_path, image_bytes, {"content-type": "image/png"}
            )

            public_url = self.supabase.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)

            self.supabase.table("project_images").insert({
                "project_id": project_id,
                "user_id": user_id,
                "image_type": image_type,
                "storage_path": storage_path,
                "public_url": public_url,
                "original_filename": filename,
                "mime_type": "image/png",
                "file_size_bytes": len(image_bytes),
                "sort_order": 0,
            }).execute()

            self.stats["base64_extracted"] += 1
            self.stats["images_uploaded"] += 1

        except Exception as e:
            print(f"    WARN: Failed to upload base64 {image_type} for {project_id[:12]}: {e}")

    # =========================================================================
    # REPORTING
    # =========================================================================

    def _print_summary(self):
        print(f"\n{'='*60}")
        print(f"Migration Summary {'(DRY RUN)' if self.dry_run else ''}")
        print(f"{'='*60}")
        print(f"  Total projects:      {self.stats['total']}")
        print(f"  Migrated:            {self.stats['migrated']}")
        print(f"  Skipped (checkpoint):{self.stats['skipped']}")
        print(f"  Errors:              {self.stats['errors']}")
        print(f"  Images uploaded:     {self.stats['images_uploaded']}")
        print(f"  Base64 extracted:    {self.stats['base64_extracted']}")

        if self.errors:
            print(f"\nErrors:")
            for err in self.errors[:20]:
                print(f"  - {err}")
            if len(self.errors) > 20:
                print(f"  ... and {len(self.errors) - 20} more")

        if not self.dry_run and self.stats["migrated"] > 0:
            print(f"\nCheckpoint saved to {CHECKPOINT_FILE}")
            print(f"JSON backup remains at {JSON_DATA_FILE}")

        print()


def main():
    parser = argparse.ArgumentParser(description="Migrate JSON data to Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no writes")
    parser.add_argument("--verify", action="store_true", help="Compare JSON vs Supabase")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help=f"Batch size (default: {BATCH_SIZE})")
    args = parser.parse_args()

    if args.verify:
        runner = MigrationRunner(dry_run=True)
        runner.verify()
    else:
        runner = MigrationRunner(dry_run=args.dry_run, batch_size=args.batch_size)
        runner.run()


if __name__ == "__main__":
    main()
