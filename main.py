"""
LineCook - Shipping Label Detection and Extraction Tool

This is the main entry point for the LineCook application, providing both
CLI and API interfaces for detecting and extracting shipping labels from
images and PDF files.

Usage:
    python main.py                    # CLI mode - process files in test_inputs/
    python main.py server             # Start FastAPI server
    uv run python main.py             # CLI mode with uv environment
    uv run python main.py server      # Server mode with uv environment
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from PIL import Image

from config import settings, logger, OUTPUT_DIR, ALLOWED_EXTENSIONS
from services.inference import inference_service
from services.image_processing import image_processor, ImageProcessingError
from api.endpoints import app


def process_file_cli(file_path: Path) -> bool:
    """
    Process a single file in CLI mode.
    
    Args:
        file_path: Path to the file to process
        
    Returns:
        True if processing succeeded, False otherwise
    """
    try:
        logger.info(f"Processing {file_path.name}...")
        
        # Read file content
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        # Process the file
        try:
            cropped_image, temp_path, best_pred = image_processor.process_uploaded_file(
                file_content, file_path.name
            )
        except ImageProcessingError as e:
            logger.error(f"Processing failed for {file_path.name}: {str(e)}")
            return False
        
        if cropped_image is None:
            logger.warning(f"❌ No labels detected in {file_path.name}")
            # Save original image to outputs for review if it's not a PDF
            if file_path.suffix.lower() != ".pdf":
                try:
                    original_image = Image.open(file_path).convert("RGB")
                    output_path = OUTPUT_DIR / f"no_label_{file_path.stem}.png"
                    original_image.save(output_path)
                    logger.info(f"Saved original image for review: {output_path}")
                except Exception as e:
                    logger.warning(f"Could not save original image: {str(e)}")
            return False
        
        # Determine output filename
        if file_path.suffix.lower() == ".pdf":
            # For PDFs, we processed pages and found a label on one of them
            output_filename = f"{file_path.stem}_page.png"
        else:
            output_filename = f"{file_path.stem}.png"
        
        output_path = OUTPUT_DIR / output_filename
        
        # Save the cropped label
        cropped_image.save(output_path)
        
        # Clean up temporary file
        if temp_path:
            try:
                import os
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Could not clean up temp file: {str(e)}")
        
        confidence = best_pred.get("confidence", 0) if best_pred else 0
        logger.info(f"✅ Saved label to {output_path} (confidence: {confidence:.3f})")
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing {file_path.name}: {str(e)}")
        return False


def run_cli_mode():
    """
    Run the application in CLI mode, processing all files in test_inputs/.
    
    This mode maintains backward compatibility with the original CLI interface.
    """
    logger.info("Starting LineCook CLI mode")
    
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
    
    # Find input files
    input_dir = Path("test_inputs")
    if not input_dir.exists():
        logger.error(f"Input directory {input_dir} does not exist")
        return
    
    # Process all supported files
    processed_files = 0
    successful_files = 0
    
    for file_path in input_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in ALLOWED_EXTENSIONS:
            processed_files += 1
            if process_file_cli(file_path):
                successful_files += 1
    
    if processed_files == 0:
        logger.warning(f"No supported files found in {input_dir}")
        logger.info(f"Supported extensions: {', '.join(ALLOWED_EXTENSIONS)}")
    else:
        logger.info(f"Processing complete: {successful_files}/{processed_files} files successful")


def run_server_mode():
    """
    Run the application in server mode using uvicorn.
    """
    try:
        import uvicorn
        logger.info("Starting LineCook API server")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except ImportError:
        logger.error("uvicorn is required for server mode. Install with: pip install uvicorn")
        sys.exit(1)


def main():
    """
    Main entry point for the LineCook application.
    
    Determines whether to run in CLI or server mode based on command line arguments.
    """
    try:
        # Check if API key is configured
        if not settings.roboflow_api_key:
            logger.error(
                "ROBOFLOW_API_KEY is not configured. "
                "Please set it in your .env file or environment variables."
            )
            sys.exit(1)
        
        # Determine mode based on command line arguments
        if len(sys.argv) > 1 and sys.argv[1] == "server":
            run_server_mode()
        else:
            run_cli_mode()
            
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        if settings.log_level.upper() == "DEBUG":
            logger.exception("Detailed error information:")
        sys.exit(1)


# Legacy function for backward compatibility
def run_app(image_path):
    """
    Legacy function for backward compatibility.
    
    Args:
        image_path: Path to image or PDF file to process
    """
    return process_file_cli(Path(image_path))


if __name__ == "__main__":
    main()