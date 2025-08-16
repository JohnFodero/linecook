"""
Image processing service for LineCook.

This module handles all image manipulation operations including cropping,
rotation, resizing, and file format conversions.
"""

import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, Union, Optional, ContextManager
from contextlib import contextmanager
from io import BytesIO

from PIL import Image
from pdf2image import convert_from_path

from config import settings, TARGET_SIZE, DEFAULT_DPI, TEMP_DIR, ALLOWED_EXTENSIONS


logger = logging.getLogger(__name__)


class ImageProcessingError(Exception):
    """Custom exception for image processing errors."""
    pass


class ImageProcessor:
    """
    Service for handling image processing operations.
    
    This service provides methods for cropping detected labels, converting PDFs,
    and managing temporary files with proper resource cleanup.
    """
    
    def __init__(self, temp_dir: Path = TEMP_DIR):
        """
        Initialize the image processor.
        
        Args:
            temp_dir: Directory for temporary file storage
        """
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        logger.info(f"Initialized image processor with temp dir: {temp_dir}")
    
    @contextmanager
    def temporary_file(self, suffix: str = ".png", delete: bool = True) -> ContextManager[str]:
        """
        Context manager for temporary file handling with proper cleanup.
        
        Args:
            suffix: File extension for the temporary file
            delete: Whether to delete the file when context exits
            
        Yields:
            Path to the temporary file
            
        Example:
            with image_processor.temporary_file(".png") as temp_path:
                image.save(temp_path)
                # File is automatically cleaned up
        """
        temp_file = None
        try:
            temp_file = tempfile.NamedTemporaryFile(
                dir=self.temp_dir,
                suffix=suffix,
                delete=delete
            )
            yield temp_file.name
        except Exception as e:
            logger.error(f"Error in temporary file context: {str(e)}")
            raise ImageProcessingError(f"Temporary file error: {str(e)}")
        finally:
            if temp_file and not delete:
                try:
                    temp_file.close()
                except Exception as e:
                    logger.warning(f"Error closing temporary file: {str(e)}")
    
    def validate_file_content(self, file_content: bytes, filename: str) -> None:
        """
        Validate uploaded file content for security and format compliance.
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            
        Raises:
            ImageProcessingError: If file is invalid or unsafe
        """
        # Check file size
        if len(file_content) > settings.max_file_size:
            raise ImageProcessingError(
                f"File size {len(file_content)} bytes exceeds maximum allowed size "
                f"{settings.max_file_size} bytes"
            )
        
        # Check file extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise ImageProcessingError(
                f"File extension '{file_ext}' not allowed. "
                f"Supported extensions: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Basic content validation for image files
        if file_ext in {".jpg", ".jpeg", ".png"}:
            try:
                # Try to load as image to validate format
                image = Image.open(BytesIO(file_content))
                image.verify()  # Verify it's a valid image
                logger.debug(f"Validated image file: {filename} ({image.format}, {image.size})")
            except Exception as e:
                raise ImageProcessingError(f"Invalid image file: {str(e)}")
        
        # Basic content validation for PDF files
        elif file_ext == ".pdf":
            # Check for PDF magic number
            if not file_content.startswith(b'%PDF-'):
                raise ImageProcessingError("Invalid PDF file: missing PDF header")
            logger.debug(f"Validated PDF file: {filename}")
        
        logger.info(f"File validation passed for: {filename}")
    
    def crop_and_save_prediction(
        self, 
        image: Image.Image, 
        prediction: Dict[str, Any], 
        output_path: Union[str, Path]
    ) -> Image.Image:
        """
        Crop a detected label from an image and save it to disk.
        
        Args:
            image: Source PIL Image object
            prediction: Prediction dictionary with bounding box coordinates
            output_path: Path where cropped image should be saved
            
        Returns:
            Cropped PIL Image object
            
        Raises:
            ImageProcessingError: If cropping fails
        """
        try:
            # Extract prediction box (center-based coordinates)
            x = prediction["x"]
            y = prediction["y"]
            w = prediction["width"]
            h = prediction["height"]
            
            # Convert to corner coordinates
            left = int(x - w / 2)
            top = int(y - h / 2)
            right = int(x + w / 2)
            bottom = int(y + h / 2)
            
            # Validate coordinates are within image bounds
            left = max(0, left)
            top = max(0, top)
            right = min(image.width, right)
            bottom = min(image.height, bottom)
            
            # Crop the image
            cropped = image.crop((left, top, right, bottom))
            
            # Rotate to portrait orientation if needed (shipping labels are typically portrait)
            if cropped.width > cropped.height:
                cropped = cropped.rotate(90, expand=True)
                logger.debug("Rotated cropped image to portrait orientation")
            
            # Save the cropped image
            cropped.save(output_path)
            
            logger.info(f"Cropped label saved to: {output_path}")
            logger.debug(f"Cropped dimensions: {cropped.width}x{cropped.height}")
            
            return cropped
            
        except Exception as e:
            logger.error(f"Error cropping image: {str(e)}")
            raise ImageProcessingError(f"Failed to crop image: {str(e)}")
    
    def convert_pdf_to_images(self, pdf_path: Union[str, Path], dpi: int = DEFAULT_DPI) -> list[Image.Image]:
        """
        Convert PDF pages to PIL Image objects.
        
        Args:
            pdf_path: Path to the PDF file
            dpi: Resolution for conversion
            
        Returns:
            List of PIL Image objects, one per page
            
        Raises:
            ImageProcessingError: If PDF conversion fails
        """
        try:
            pages = convert_from_path(pdf_path, dpi=dpi)
            logger.info(f"Converted PDF to {len(pages)} image(s) at {dpi} DPI")
            return pages
            
        except Exception as e:
            logger.error(f"Error converting PDF: {str(e)}")
            raise ImageProcessingError(f"Failed to convert PDF: {str(e)}")
    
    def process_uploaded_file(
        self, 
        file_content: bytes, 
        filename: str
    ) -> tuple[Optional[Image.Image], str, Optional[Dict[str, Any]]]:
        """
        Process an uploaded file and extract the best shipping label.
        
        This is a simplified version that delegates to smaller, focused methods.
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            
        Returns:
            Tuple of (cropped_image, temp_file_path, best_prediction)
            Returns (None, error_message, None) if processing fails
        """
        try:
            self.validate_file_content(file_content, filename)
            
            with self.temporary_file(suffix=Path(filename).suffix) as temp_input_path:
                self._write_temp_file(temp_input_path, file_content)
                
                if self._is_pdf_file(filename):
                    return self._process_pdf_file(temp_input_path, filename)
                else:
                    return self._process_image_file(temp_input_path, filename)
                    
        except ImageProcessingError:
            raise
        except Exception as e:
            logger.error(f"Error processing uploaded file {filename}: {str(e)}")
            raise ImageProcessingError(f"File processing failed: {str(e)}")
    
    def _write_temp_file(self, temp_path: str, content: bytes) -> None:
        """Write content to temporary file."""
        with open(temp_path, 'wb') as f:
            f.write(content)
    
    def _is_pdf_file(self, filename: str) -> bool:
        """Check if filename is a PDF file."""
        return filename.lower().endswith(".pdf")
    
    def _process_pdf_file(
        self, 
        pdf_path: str, 
        filename: str
    ) -> tuple[Optional[Image.Image], str, Optional[Dict[str, Any]]]:
        """Process a PDF file and extract labels from pages."""
        from services.inference import inference_service
        
        try:
            pages = self.convert_pdf_to_images(pdf_path)
            
            for i, page in enumerate(pages):
                label_result = self._try_extract_label_from_image(page, f"page {i} of {filename}")
                if label_result[0] is not None:  # Found a label
                    return label_result
                    
            # No labels found in any page
            return None, "No shipping labels detected in PDF", None
            
        except Exception as e:
            logger.error(f"Error processing PDF file: {str(e)}")
            raise ImageProcessingError(f"PDF processing failed: {str(e)}")
    
    def _process_image_file(
        self, 
        image_path: str, 
        filename: str
    ) -> tuple[Optional[Image.Image], str, Optional[Dict[str, Any]]]:
        """Process an image file and extract labels."""
        try:
            # Load and convert image to RGB
            image = Image.open(image_path).convert("RGB")
            return self._try_extract_label_from_image(image, filename)
                
        except Exception as e:
            logger.error(f"Error processing image file: {str(e)}")
            raise ImageProcessingError(f"Image processing failed: {str(e)}")
    
    def _try_extract_label_from_image(
        self, 
        image: Image.Image, 
        image_description: str
    ) -> tuple[Optional[Image.Image], str, Optional[Dict[str, Any]]]:
        """
        Try to extract a label from a single image.
        
        This method handles the common logic for both PDF pages and standalone images.
        """
        from services.inference import inference_service
        
        try:
            # Run inference
            predictions, best_pred = inference_service.detect_labels(image)
            
            # Create temporary output file (not auto-deleted for return)
            with self.temporary_file(".png", delete=False) as temp_output_path:
                cropped = self.crop_and_save_prediction(image, best_pred, temp_output_path)
                
                logger.info(f"Successfully processed {image_description}")
                return cropped, temp_output_path, best_pred
                
        except ValueError as e:
            # No labels detected
            logger.debug(f"No labels detected in {image_description}: {str(e)}")
            return None, f"No shipping labels detected in {image_description}: {str(e)}", None


# Global image processor instance
image_processor = ImageProcessor()