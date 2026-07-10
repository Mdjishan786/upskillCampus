#!/usr/bin/env python3
"""
📦 Advanced File Organizer Automator
Author: Professional Engineering Refactor
Description: Safely categorizes files into clean subdirectories using strict Pathlib APIs,
             duplicate checking, execution previews (dry-run), and operational isolation.
"""

import json
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional

# ---------- Configuration & System Constants ----------
DEFAULT_CONFIG_NAME = "config.json"
DEFAULT_LOG_NAME = "file_organizer.log"

DEFAULT_CATEGORIES: Dict[str, List[str]] = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".svg", ".webp", ".ico", ".heic", ".raw"],
    "Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".xls", ".pptx", ".ppt", ".odt", ".ods", ".rtf", ".md", ".csv"],
    "Videos": [".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm", ".3gp", ".m4v", ".mpeg"],
    "Audio": [".mp3", ".wav", ".aac", ".flac", ".ogg", ".wma", ".m4a", ".aiff"],
    "Archives": [".zip", ".tar", ".gz", ".rar", ".7z", ".bz2", ".xz", ".tgz"],
    "Scripts": [".py", ".js", ".html", ".css", ".sh", ".bat", ".ps1", ".rb", ".java", ".cpp", ".c", ".php"],
    "Design": [".psd", ".ai", ".eps", ".sketch", ".xd", ".fig"],
    "Executables": [".exe", ".msi", ".dmg", ".app", ".deb", ".rpm"],
    "Other": []
}

logger = logging.getLogger("FileOrganizer")


# ---------- Logging & I/O Infrastructure ----------
def configure_logging(log_filepath: Path) -> None:
    """Sets up a robust, dual-handler logging architecture (File + Console)."""
    logger.setLevel(logging.INFO)
    
    # Reset existing handlers if any to prevent duplicate logging
    if logger.hasHandlers():
        logger.handlers.clear()

    log_format = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # File Handler
    file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    # Console Stream Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(console_handler)


# ---------- Configuration Subsystem ----------
class ConfigurationManager:
    """Handles thread-safe storage, fetching, and fallback orchestration of mapping schemas."""
    
    def __init__(self, config_path: Path):
        self.config_path = config_path

    def load_extensions_mapping(self) -> Dict[str, List[str]]:
        """Loads categories mapping from JSON or falls back gracefully to defaults."""
        if self.config_path.is_file():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as stream:
                    return json.load(stream)
            except (json.JSONDecodeError, IOError) as err:
                logger.warning(f"⚠️ Failed decoding custom config '{self.config_path}'. Fallback to defaults. Error: {err}")
                return DEFAULT_CATEGORIES
        
        # Seed default configuration if completely missing
        try:
            with open(self.config_path, 'w', encoding='utf-8') as stream:
                json.dump(DEFAULT_CATEGORIES, stream, indent=4, ensure_ascii=False)
            logger.info(f"📝 Seeded clean config definition profile at: '{self.config_path}'")
        except IOError as err:
            logger.error(f"❌ Critical failure trying to write configuration framework: {err}")
            
        return DEFAULT_CATEGORIES


# ---------- Core Engine Components ----------
class DirectoryOrganizer:
    """Orchestrates high-safety sorting algorithms on unmanaged directories."""
    
    def __init__(self, target_dir: Path, mapping: Dict[str, List[str]], config_file: Path, log_file: Path):
        self.target_dir = target_dir.resolve()
        self.mapping = mapping
        
        # System Exclusion Guard: Block system elements from accidentally packing themselves
        self.system_exclusions: Set[Path] = {
            config_file.resolve(),
            log_file.resolve(),
            Path(__file__).resolve()
        }

    def _resolve_target_category(self, file_path: Path) -> str:
        """Determines the mapped group signature matching target string lower suffixes."""
        target_extension = file_path.suffix.lower()
        for category, extensions in self.mapping.items():
            if target_extension in extensions:
                return category
        return "Other"

    def _calculate_unique_destination(self, base_dir: Path, target_filename: str) -> Path:
        """Mitigates namespaces collision by generating sequentially incremented names."""
        candidate = base_dir / target_filename
        if not candidate.exists():
            return candidate

        stem = candidate.stem
        suffix = candidate.suffix
        counter = 1
        
        while True:
            allocated_name = f"{stem}_{counter}{suffix}"
            candidate = base_dir / allocated_name
            if not candidate.exists():
                return candidate
            counter += 1

    def process(self, dry_run: bool = False, verbose: bool = False) -> None:
        """Runs the validation logic and executes filesystem changes safely."""
        if not self.target_dir.is_dir():
            logger.error(f"❌ Operational Failure: Target '{self.target_dir}' is an unresolvable or missing directory routing.")
            return

        logger.info(f"📁 Source Target Vector  : {self.target_dir}")
        logger.info(f"🧪 Dry Run Flag Status   : {dry_run}")
        logger.info(f"📝 Verbose Logging Mode  : {verbose}")
        logger.info("═" * 65)

        # Pre-create folders if it's not a dry run
        if not dry_run:
            for category in self.mapping.keys():
                (self.target_dir / category).mkdir(parents=True, exist_ok=True)

        metrics = {"moved": 0, "skipped": 0, "errors": 0}

        for node in self.target_dir.iterdir():
            # Structural Guard: Ignore active subdirectories and system exclusions
            if node.is_dir():
                if verbose and node.name in self.mapping:
                    logger.info(f"⏭️ Skipping internal bucket directory: {node.name}/")
                continue
                
            if node.name.startswith('.') or node.resolve() in self.system_exclusions:
                if verbose:
                    logger.info(f"⏭️ Skipping core system/hidden entity: {node.name}")
                metrics["skipped"] += 1
                continue

            # Route calculation processing
            assigned_bucket = self._resolve_target_category(node)
            bucket_directory = self.target_dir / assigned_bucket
            final_destination = self._calculate_unique_destination(bucket_directory, node.name)

            if dry_run:
                logger.info(f"🔄 [DRY RUN] Expected route action: {node.name} ──> {assigned_bucket}/{final_destination.name}")
                metrics["moved"] += 1
            else:
                try:
                    # Native high-performance atomic shifting operations
                    node.replace(final_destination)
                    logger.info(f"✅ Transformed: {node.name} ──> {assigned_bucket}/{final_destination.name}")
                    metrics["moved"] += 1
                except Exception as ex:
                    logger.error(f"❌ Critical File Shift Failure: {node.name}. Root Reason: {ex}")
                    metrics["errors"] += 1

        # Execution Summary Output
        logger.info("═" * 65)
        logger.info("📊 EXECUTION ANALYTICS METRICS:")
        logger.info(f"   • Files Route System Operations : {metrics['moved']} Items")
        logger.info(f"   • Errors Encountered Count     : {metrics['errors']} Anomalies")
        logger.info(f"   • Skipped Entities Evaluated   : {metrics['skipped']} Elements")
        if dry_run:
            logger.info("   🔄 Evaluation Complete: No actual mutations have locked into disk storage.")
        logger.info("═" * 65)


# ---------- Command Line Interface Route Entry ----------
def main() -> None:
    """Configures explicit parsing structures and acts as runtime context launcher."""
    parser = argparse.ArgumentParser(
        description="📁 File Organizer Automator - Cleans up workspaces into structured directories safely.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Execution Configurations Framework Examples:
  python file_organizer.py C:\\Users\\Name\\Downloads
  python file_organizer.py ./TargetDir --dry-run
  python file_organizer.py /var/data -v --config /opt/rules.json
        """
    )
    parser.add_argument("directory", help="The absolute target directory route workspace to cleanly parse.")
    parser.add_argument("--dry-run", action="store_true", help="Generates evaluation simulations maps outputs without disk changes.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enables verbose debugging trace metrics updates.")
    parser.add_argument("--config", "-c", help="Locate standard programmatic rules configuration mappings overrides.")

    args = parser.parse_args()

    # System configuration paths resolution
    runtime_config_path = Path(args.config) if args.config else Path(__file__).parent / DEFAULT_CONFIG_NAME
    runtime_log_path = Path(__file__).parent / DEFAULT_LOG_NAME

    # Initialize execution systems
    configure_logging(runtime_log_path)
    config_engine = ConfigurationManager(runtime_config_path)
    extensions_mapping = config_engine.load_extensions_mapping()

    target_directory = Path(args.directory)
    
    engine = DirectoryOrganizer(
        target_dir=target_directory,
        mapping=extensions_mapping,
        config_file=runtime_config_path,
        log_file=runtime_log_path
    )
    
    engine.process(dry_run=args.dry_run, verbose=args.verbose)


if __name__ == "__main__":
    main()
