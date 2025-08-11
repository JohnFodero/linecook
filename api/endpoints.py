"""
FastAPI endpoints for LineCook label detection API.

This module defines all HTTP endpoints for the label detection service,
including file upload, processing, printing, and health checks.
"""

import base64
import logging
import os
from io import BytesIO
from typing import Dict, Any

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from services.image_processing import image_processor, ImageProcessingError
from services.printing import print_service, PrintingError


logger = logging.getLogger(__name__)


# Initialize FastAPI application
app = FastAPI(
    title="LineCook Label Detection API",
    version="1.0.0",
    description="API for detecting and extracting shipping labels from images and PDFs"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def web_interface():
    """
    Serve the main web interface for LineCook.
    
    Returns the HTML page that provides a user-friendly interface for
    uploading files, processing labels, and downloading results.
    """
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(
            status_code=500, 
            detail="Web interface not found. Please ensure static/index.html exists."
        )


@app.post("/create_labels")
async def create_labels(
    file: UploadFile = File(...),
    print_label: bool = Form(default=False)
) -> JSONResponse:
    """
    Process uploaded image/PDF file to detect and extract shipping labels.
    
    This endpoint accepts image files (JPG, JPEG, PNG) or PDF files,
    detects shipping labels using computer vision, crops the best label,
    and optionally prints it.
    
    Args:
        file: Uploaded file (PDF, JPG, JPEG, or PNG)
        print_label: Optional flag to print the label if successful
    
    Returns:
        JSON response with:
        - success: boolean indicating if label was found
        - message: descriptive message
        - label_dimensions: width/height of cropped label
        - image_data: base64 encoded PNG of cropped label
        - confidence: detection confidence score
        - print_attempted: boolean if printing was requested
        - print_success: boolean if printing succeeded
        - print_message: printing status message
    
    Raises:
        HTTPException: For validation errors (400) or processing errors (500)
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    try:
        # Read file content
        file_content = await file.read()
        logger.info(f"Processing uploaded file: {file.filename} ({len(file_content)} bytes)")
        
        # Process the file using the image processing service
        try:
            cropped_image, result_path, best_pred = image_processor.process_uploaded_file(
                file_content, file.filename
            )
        except ImageProcessingError as e:
            logger.warning(f"Image processing failed for {file.filename}: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        
        # Check if label was found
        if cropped_image is None:
            logger.info(f"No labels detected in {file.filename}")
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": result_path}
            )
        
        # Convert image to base64 for response
        buffer = BytesIO()
        cropped_image.save(buffer, format='PNG')
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Build response data
        response_data: Dict[str, Any] = {
            "success": True,
            "message": "Label successfully detected and processed",
            "label_dimensions": {
                "width": cropped_image.width,
                "height": cropped_image.height
            },
            "image_data": image_base64,
            "confidence": best_pred["confidence"] if best_pred else None
        }
        
        # Handle printing if requested
        if print_label:
            try:
                print_success, print_message = print_service.print_label_file(result_path)
                response_data.update({
                    "print_attempted": True,
                    "print_success": print_success,
                    "print_message": print_message
                })
                
                if not print_success:
                    response_data["print_error"] = print_message
                    logger.warning(f"Print failed for {file.filename}: {print_message}")
                else:
                    logger.info(f"Print succeeded for {file.filename}")
                    
            except PrintingError as e:
                logger.error(f"Print error for {file.filename}: {str(e)}")
                response_data.update({
                    "print_attempted": True,
                    "print_success": False,
                    "print_message": str(e),
                    "print_error": str(e)
                })
        
        # Clean up temporary file
        try:
            if result_path and os.path.exists(result_path):
                os.unlink(result_path)
                logger.debug(f"Cleaned up temporary file: {result_path}")
        except Exception as e:
            logger.warning(f"Could not clean up temporary file {result_path}: {str(e)}")
        
        logger.info(f"Successfully processed {file.filename}")
        return JSONResponse(content=response_data)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for service monitoring.
    
    Returns:
        Dictionary with service status and configuration information
    """
    return {
        "status": "healthy",
        "api_configured": bool(settings.roboflow_api_key),
        "print_enabled": settings.print_enabled,
        "model_id": settings.model_id,
        "confidence_threshold": settings.confidence_thresh
    }


@app.get("/print/status")
async def print_status() -> Dict[str, Any]:
    """
    Check print system status and configuration.
    
    Returns:
        Dictionary with detailed print system information including:
        - Print configuration settings
        - Available print commands
        - System information
        - Detected printers
    """
    try:
        return print_service.check_print_setup()
    except Exception as e:
        logger.error(f"Error checking print status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Print status check failed: {str(e)}")


@app.post("/print/test")
async def test_print() -> Dict[str, Any]:
    """
    Test printing functionality with a generated test image.
    
    Creates a test image with system information and attempts to print it
    using the configured print command. Useful for debugging print setup.
    
    Returns:
        Dictionary with test results including:
        - Test execution status
        - Print success/failure
        - System configuration
        - Error messages if applicable
        
    Raises:
        HTTPException: If test fails critically (500)
    """
    try:
        result = print_service.test_print()
        
        if result["print_success"]:
            logger.info("Print test completed successfully")
        else:
            logger.warning(f"Print test failed: {result.get('print_message', 'Unknown error')}")
        
        return result
        
    except PrintingError as e:
        logger.error(f"Print test failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in print test: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Test print error: {str(e)}")


# Error handlers for better error responses
@app.exception_handler(ImageProcessingError)
async def image_processing_error_handler(request, exc: ImageProcessingError):
    """Handle image processing errors with appropriate HTTP status codes."""
    logger.warning(f"Image processing error: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content={"error": "Image processing failed", "detail": str(exc)}
    )


@app.exception_handler(PrintingError)
async def printing_error_handler(request, exc: PrintingError):
    """Handle printing errors with appropriate HTTP status codes."""
    logger.warning(f"Printing error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Printing failed", "detail": str(exc)}
    )