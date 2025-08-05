import tempfile
import subprocess
import platform
import base64
import logging
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from PIL import Image
from io import BytesIO
import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from inference_sdk import InferenceHTTPClient, InferenceConfiguration
from pdf2image import convert_from_path


# --- CONFIG ---
class Settings(BaseSettings):
    """Application settings with environment variable support"""
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'  # Ignore extra environment variables
    )
    
    # Required fields
    roboflow_api_key: str = Field(
        description="Roboflow API key for inference"
    )
    model_id: str = Field(
        default="shipping-label-k3hzg/4",
        description="Roboflow model ID for label detection"
    )
    confidence_thresh: float = Field(
        default=0.04,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for predictions"
    )
    
    # Print configuration
    print_command: str = Field(
        default="auto",
        description="Print command to use. 'auto' for system default, or custom command like 'lpr -P printer_name'"
    )
    print_enabled: bool = Field(
        default=True,
        description="Enable/disable printing functionality"
    )
    print_debug: bool = Field(
        default=False,
        description="Enable debug output for print operations"
    )
    
    # Logging configuration
    log_level: str = Field(
        default="INFO",
        description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    @property
    def endpoint(self) -> str:
        """Build the inference endpoint URL"""
        return f"https://infer.roboflow.com/{self.model_id}?api_key={self.roboflow_api_key}"


# Initialize settings - this will validate environment variables at startup
settings = Settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="LineCook Label Detection API", version="1.0.0")

# Resize config (4x6 in at 300DPI)
TARGET_SIZE = (1200, 1800)
TMP_DIR = Path("tmp")
TMP_DIR.mkdir(exist_ok=True, parents=True)


def infer_image(image_path):
    custom_configuration = InferenceConfiguration(
        confidence_threshold=settings.confidence_thresh
    )
    client = InferenceHTTPClient(
        api_url=f"https://serverless.roboflow.com/", api_key=settings.roboflow_api_key
    )
    image = Image.open(image_path)
    with client.use_configuration(custom_configuration):
        results = client.infer(image, model_id=settings.model_id)
    return results


def infer_image_pil(image):
    custom_configuration = InferenceConfiguration(
        confidence_threshold=settings.confidence_thresh
    )
    client = InferenceHTTPClient(
        api_url=f"https://serverless.roboflow.com/", api_key=settings.roboflow_api_key
    )
    with client.use_configuration(custom_configuration):
        results = client.infer(image, model_id=settings.model_id)
    return results


def crop_and_save_prediction(image, pred, output_path):
    # Extract prediction box (center-based coords)
    x = pred["x"]
    y = pred["y"]
    w = pred["width"]
    h = pred["height"]
    left = int(x - w / 2)
    top = int(y - h / 2)
    right = int(x + w / 2)
    bottom = int(y + h / 2)

    cropped = image.crop((left, top, right, bottom))

    # Rotate to portrait if needed
    if cropped.width > cropped.height:
        cropped = cropped.rotate(90, expand=True)

    cropped.save(output_path)
    return cropped


def pick_best_prediction(predictions):
    TARGET_RATIOS = [4 / 6, 6 / 4]

    def aspect_ratio_score(pred):
        w, h = pred["width"], pred["height"]
        ratio = w / h
        return min(abs(ratio - target) for target in TARGET_RATIOS)

    return min(predictions, key=aspect_ratio_score)


def print_label_file(image_path: str) -> tuple[bool, str]:
    """
    Print label using configurable system print utilities
    
    Returns:
        tuple: (success: bool, message: str)
    """
    if not settings.print_enabled:
        return False, "Printing is disabled in configuration"

    try:
        # Determine print command
        if settings.print_command == "auto":
            system = platform.system()
            if system == "Darwin":  # macOS
                cmd = ["lpr"]
            elif system == "Linux":
                cmd = ["lp"]
            elif system == "Windows":
                # For Windows, we could use print command but it's more complex
                return False, f"Auto print not supported on {system}. Please configure PRINT_COMMAND explicitly."
            else:
                return False, f"Unsupported system: {system}"
        else:
            # Parse custom command
            cmd = settings.print_command.split()
            if not cmd:
                return False, "Empty print command configured"

        # Add the file path
        full_cmd = cmd + [str(image_path)]

        if settings.print_debug:
            logger.debug(f"🖨️  Executing print command: {' '.join(full_cmd)}")
            logger.debug(f"🖨️  File exists: {os.path.exists(image_path)}")
            logger.debug(f"🖨️  File size: {os.path.getsize(image_path) if os.path.exists(image_path) else 'N/A'} bytes")

        # Execute the print command
        result = subprocess.run(
            full_cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )

        success_msg = f"Print job submitted successfully using: {' '.join(cmd)}"
        if settings.print_debug and result.stdout:
            success_msg += f"\nOutput: {result.stdout.strip()}"

        return True, success_msg

    except subprocess.TimeoutExpired:
        error_msg = "Print command timed out after 30 seconds"
        if settings.print_debug:
            logger.debug(f"🖨️  {error_msg}")
        return False, error_msg

    except subprocess.CalledProcessError as e:
        error_msg = f"Print command failed with exit code {e.returncode}"
        if e.stderr:
            error_msg += f": {e.stderr.strip()}"
        if settings.print_debug:
            logger.debug(f"🖨️  {error_msg}")
            logger.debug(f"🖨️  Command: {' '.join(full_cmd)}")
        return False, error_msg

    except FileNotFoundError as e:
        error_msg = f"Print command not found: {cmd[0] if cmd else 'unknown'}"
        if settings.print_debug:
            logger.debug(f"🖨️  {error_msg}")
            logger.debug(f"🖨️  Full command: {' '.join(full_cmd) if 'full_cmd' in locals() else 'N/A'}")
        return False, error_msg

    except Exception as e:
        error_msg = f"Unexpected error during printing: {str(e)}"
        if settings.print_debug:
            logger.debug(f"🖨️  {error_msg}")
        return False, error_msg


def check_print_setup() -> dict:
    """
    Check and debug the current print setup
    
    Returns:
        dict: Detailed information about print configuration and system state
    """
    info = {
        "print_enabled": settings.print_enabled,
        "print_command": settings.print_command,
        "print_debug": settings.print_debug,
        "system": platform.system(),
        "available_commands": {},
        "printers": []
    }
    
    # Check available print commands
    commands_to_check = ["lpr", "lp", "lpstat", "lpq"]
    for cmd in commands_to_check:
        try:
            result = subprocess.run([cmd, "--help"], capture_output=True, timeout=5)
            info["available_commands"][cmd] = "available"
        except FileNotFoundError:
            info["available_commands"][cmd] = "not found"
        except subprocess.TimeoutExpired:
            info["available_commands"][cmd] = "timeout"
        except Exception as e:
            info["available_commands"][cmd] = f"error: {str(e)}"
    
    # Try to get list of printers
    try:
        if platform.system() == "Darwin":  # macOS
            result = subprocess.run(["lpstat", "-p"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                info["printers"] = [line.strip() for line in result.stdout.split('\n') if line.strip()]
        elif platform.system() == "Linux":
            result = subprocess.run(["lpstat", "-p"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                info["printers"] = [line.strip() for line in result.stdout.split('\n') if line.strip()]
    except Exception as e:
        info["printer_error"] = str(e)
    
    return info


def process_file(file_content: bytes, filename: str) -> tuple[Optional[Image.Image], str, Optional[dict]]:
    """Process uploaded file and return cropped label image, message, and best prediction"""
    with tempfile.NamedTemporaryFile(dir=TMP_DIR, delete=True, suffix=Path(filename).suffix) as temp_input:
        temp_input.write(file_content)
        temp_input.flush()
        
        try:
            if filename.lower().endswith(".pdf"):
                pages = convert_from_path(temp_input.name, dpi=300)
                for i, page in enumerate(pages):
                    result = infer_image_pil(page)
                    if result["predictions"]:
                        best_pred = pick_best_prediction(result["predictions"])
                        with tempfile.NamedTemporaryFile(dir=TMP_DIR, delete=False, suffix=".png") as temp_output:
                            cropped = crop_and_save_prediction(page, best_pred, temp_output.name)
                            return cropped, temp_output.name, best_pred
                return None, "No labels detected in PDF", None
            else:
                image = Image.open(temp_input.name).convert("RGB")
                result = infer_image_pil(image)
                if not result["predictions"]:
                    return None, "No labels detected in image", None
                
                best_pred = pick_best_prediction(result["predictions"])
                with tempfile.NamedTemporaryFile(dir=TMP_DIR, delete=False, suffix=".png") as temp_output:
                    cropped = crop_and_save_prediction(image, best_pred, temp_output.name)
                    return cropped, temp_output.name, best_pred
        except Exception as e:
            logger.error(f"Error processing file {filename}: {str(e)}")
            return None, f"Processing error: {str(e)}", None


@app.post("/create_labels")
async def create_labels(
    file: UploadFile = File(...),
    print_label: bool = Form(default=False)
):
    """
    Process uploaded image/PDF file to detect and extract shipping labels.
    
    Args:
        file: Uploaded file (PDF, JPG, JPEG, or PNG)
        print_label: Optional flag to print the label if successful
    
    Returns:
        JSON response with success status, message, base64 image data, confidence score, and optionally print status
    """
    # Validate file type
    allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png"}
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Process the file
        cropped_image, result_path, best_pred = process_file(file_content, file.filename)
        if cropped_image is None:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": result_path}
            )
        
        # Convert image to base64
        buffer = BytesIO()
        cropped_image.save(buffer, format='PNG')
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        response_data = {
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
            print_success, print_message = print_label_file(result_path)
            response_data["print_attempted"] = True
            response_data["print_success"] = print_success
            response_data["print_message"] = print_message
            if not print_success:
                response_data["print_error"] = print_message
        
        # Clean up temp file
        try:
            os.unlink(result_path)
        except:
            pass
            
        return JSONResponse(content=response_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "api_configured": bool(settings.roboflow_api_key)}


@app.get("/print/status")
async def print_status():
    """Check print system status and configuration"""
    return check_print_setup()


@app.post("/print/test")
async def test_print():
    """Test printing with a simple test image"""
    try:
        # Create a simple test image
        from PIL import Image, ImageDraw
        from datetime import datetime
        
        # Create a 4x6 inch test image at 300 DPI
        width, height = 1200, 1800
        image = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(image)
        
        # Draw test content
        draw.rectangle([50, 50, width-50, height-50], outline='black', width=5)
        draw.text((100, 100), "LINECOOK PRINT TEST", fill='black')
        draw.text((100, 200), f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill='black')
        draw.text((100, 300), f"System: {platform.system()}", fill='black')
        draw.text((100, 400), f"Print Command: {settings.print_command}", fill='black')
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(dir=TMP_DIR, delete=False, suffix=".png") as tmp:
            image.save(tmp.name, 'PNG')
            tmp_path = tmp.name
        
        # Attempt to print
        success, message = print_label_file(tmp_path)
        
        # Get fresh settings to avoid caching issues
        fresh_settings = Settings()
        
        response = {
            "test_attempted": True,
            "print_success": success,
            "print_message": message,
            "test_image_path": tmp_path,
            "settings": {
                "print_enabled": fresh_settings.print_enabled,
                "print_command": fresh_settings.print_command,
                "print_debug": fresh_settings.print_debug,
                "system": platform.system()
            }
        }
        
        # Clean up temp file after successful print attempt
        try:
            os.unlink(tmp_path)
        except:
            pass
            
        return response
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test print error: {str(e)}")


# Legacy CLI functionality for backward compatibility
def run_app(image_path):
    logger.info(f"Running inference on {image_path}...")
    outdir = Path("test_outputs")
    outdir.mkdir(exist_ok=True)

    if str(image_path).lower().endswith(".pdf"):
        pages = convert_from_path(image_path, dpi=300)
        for i, page in enumerate(pages):
            result = infer_image_pil(page)
            if not result["predictions"]:
                logger.warning(f"❌ No labels detected on page {i}")
                page.save(outdir / f"badpage{image_path.stem}_{i}.png")
                continue
            out_path = outdir / Path(f"{image_path.stem}_page{i}.png")
            logger.info(f"Found {len(result['predictions'])} options")
            top = pick_best_prediction(result["predictions"])
            crop_and_save_prediction(page, top, out_path)
            logger.info(f"✅ Saved to {out_path}")
    else:
        result = infer_image(image_path)
        if not result["predictions"]:
            logger.warning(f"❌ No labels detected")
            return
        out_path = outdir / Path(f"{image_path.stem}.png")
        logger.info(f"Found {len(result['predictions'])} options")
        top = pick_best_prediction(result["predictions"])
        image = Image.open(image_path).convert("RGB")
        crop_and_save_prediction(image, top, out_path)
        logger.info(f"✅ Saved to {out_path}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        # Legacy CLI mode
        for filepath in Path("test_inputs/").glob("*"):
            if filepath.suffix.lower() in [".pdf", ".jpg", ".jpeg"]:
                run_app(filepath)
