"""
Printing service for LineCook.

This module handles all printing operations with configurable print commands,
system detection, and comprehensive error handling.
"""

import logging
import subprocess
import platform
import tempfile
import os
from typing import Tuple, Dict, Any, Union
from pathlib import Path
from datetime import datetime

from PIL import Image, ImageDraw

from config import settings, TEMP_DIR
from dataclasses import dataclass


logger = logging.getLogger(__name__)


class PrintingError(Exception):
    """Custom exception for printing errors."""
    pass


@dataclass
class PrintResult:
    """Result of a print operation with cleaner interface."""
    success: bool
    message: str
    command_used: str = ""


class PrintService:
    """
    Service for handling printing operations.
    
    This service provides cross-platform printing capabilities with
    configurable commands and comprehensive error handling.
    """
    
    def __init__(self):
        """Initialize the print service."""
        self.temp_dir = TEMP_DIR
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        logger.info("Initialized print service")
    
    def print_label(self, image_path: Union[str, Path]) -> PrintResult:
        """
        Print a label file using configurable system print utilities.
        
        Args:
            image_path: Path to the image file to print
            
        Returns:
            PrintResult with success status and message
            
        Raises:
            PrintingError: If printing is disabled or fails critically
        """
        if not settings.print_enabled:
            raise PrintingError("Printing is disabled in configuration")
        
        image_path = str(image_path)
        
        if not os.path.exists(image_path):
            raise PrintingError(f"Print file does not exist: {image_path}")
        
        try:
            cmd = self._get_print_command()
            full_cmd = cmd + [image_path]
            
            if settings.print_debug:
                logger.debug(f"🖨️  Executing print command: {' '.join(full_cmd)}")
            
            # Execute the print command with timeout
            result = subprocess.run(
                full_cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=settings.api_timeout
            )
            
            success_msg = f"Print job submitted successfully"
            if settings.print_debug and result.stdout:
                success_msg += f"\\nOutput: {result.stdout.strip()}"
            
            logger.info(f"Print job submitted for: {image_path}")
            return PrintResult(
                success=True,
                message=success_msg,
                command_used=' '.join(cmd)
            )
            
        except subprocess.TimeoutExpired:
            error_msg = f"Print command timed out after {settings.api_timeout} seconds"
            logger.error(f"🖨️  {error_msg}")
            return PrintResult(success=False, message=error_msg, command_used=' '.join(cmd))
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Print command failed with exit code {e.returncode}"
            if e.stderr:
                error_msg += f": {e.stderr.strip()}"
            logger.error(f"🖨️  {error_msg}")
            return PrintResult(success=False, message=error_msg, command_used=' '.join(cmd))
            
        except FileNotFoundError:
            error_msg = f"Print command not found: {cmd[0] if cmd else 'unknown'}"
            logger.error(f"🖨️  {error_msg}")
            return PrintResult(success=False, message=error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error during printing: {str(e)}"
            logger.error(f"🖨️  {error_msg}")
            return PrintResult(success=False, message=error_msg)

    def print_label_file(self, image_path: Union[str, Path]) -> Tuple[bool, str]:
        """
        Print a label file using configurable system print utilities.
        
        Args:
            image_path: Path to the image file to print
            
        Returns:
            Tuple of (success: bool, message: str)
            
        Raises:
            PrintingError: If printing is disabled or fails critically
        """
        if not settings.print_enabled:
            raise PrintingError("Printing is disabled in configuration")
        
        image_path = str(image_path)  # Ensure string path
        
        if not os.path.exists(image_path):
            raise PrintingError(f"Print file does not exist: {image_path}")
        
        try:
            # Determine print command based on configuration
            cmd = self._get_print_command()
            
            # Build full command with file path
            full_cmd = cmd + [image_path]
            
            if settings.print_debug:
                logger.debug(f"🖨️  Executing print command: {' '.join(full_cmd)}")
                logger.debug(f"🖨️  File exists: {os.path.exists(image_path)}")
                logger.debug(f"🖨️  File size: {os.path.getsize(image_path)} bytes")
            
            # Execute the print command with timeout
            result = subprocess.run(
                full_cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=settings.api_timeout  # Use configurable timeout
            )
            
            success_msg = f"Print job submitted successfully using: {' '.join(cmd)}"
            if settings.print_debug and result.stdout:
                success_msg += f"\\nOutput: {result.stdout.strip()}"
            
            logger.info(f"Print job submitted for: {image_path}")
            return True, success_msg
            
        except subprocess.TimeoutExpired:
            error_msg = f"Print command timed out after {settings.api_timeout} seconds"
            logger.error(f"🖨️  {error_msg}")
            return False, error_msg
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Print command failed with exit code {e.returncode}"
            if e.stderr:
                error_msg += f": {e.stderr.strip()}"
            logger.error(f"🖨️  {error_msg}")
            if settings.print_debug:
                logger.debug(f"🖨️  Command: {' '.join(full_cmd)}")
            return False, error_msg
            
        except FileNotFoundError:
            error_msg = f"Print command not found: {cmd[0] if cmd else 'unknown'}"
            logger.error(f"🖨️  {error_msg}")
            if settings.print_debug:
                logger.debug(f"🖨️  Full command: {' '.join(full_cmd) if 'full_cmd' in locals() else 'N/A'}")
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error during printing: {str(e)}"
            logger.error(f"🖨️  {error_msg}")
            if settings.print_debug:
                logger.exception("Print error details:")
            return False, error_msg
    
    def _get_print_command(self) -> list[str]:
        """
        Determine the appropriate print command based on configuration.
        
        Returns:
            List of command components
            
        Raises:
            PrintingError: If no suitable print command is found
        """
        if settings.print_command == "auto":
            # Auto-detect based on operating system
            system = platform.system()
            
            if system == "Darwin":  # macOS
                return ["lpr"]
            elif system == "Linux":
                return ["lp"]
            elif system == "Windows":
                raise PrintingError(
                    f"Auto print not supported on {system}. "
                    "Please configure PRINT_COMMAND explicitly."
                )
            else:
                raise PrintingError(f"Unsupported system for auto print: {system}")
        else:
            # Parse custom command
            cmd = settings.print_command.split()
            if not cmd:
                raise PrintingError("Empty print command configured")
            return cmd
    
    def check_print_setup(self) -> Dict[str, Any]:
        """
        Check and debug the current print setup.
        
        Returns:
            Dictionary with detailed information about print configuration and system state
        """
        info = {
            "print_enabled": settings.print_enabled,
            "print_command": settings.print_command,
            "print_debug": settings.print_debug,
            "system": platform.system(),
            "available_commands": {},
            "printers": [],
            "timeout": settings.api_timeout
        }
        
        # Check available print commands
        commands_to_check = ["lpr", "lp", "lpstat", "lpq"]
        for cmd in commands_to_check:
            try:
                result = subprocess.run(
                    [cmd, "--help"], 
                    capture_output=True, 
                    timeout=5,
                    text=True
                )
                info["available_commands"][cmd] = "available"
                logger.debug(f"Print command {cmd} is available")
            except FileNotFoundError:
                info["available_commands"][cmd] = "not found"
            except subprocess.TimeoutExpired:
                info["available_commands"][cmd] = "timeout"
            except Exception as e:
                info["available_commands"][cmd] = f"error: {str(e)}"
        
        # Try to get list of printers
        try:
            if platform.system() in ["Darwin", "Linux"]:  # macOS and Linux
                result = subprocess.run(
                    ["lpstat", "-p"], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                if result.returncode == 0:
                    info["printers"] = [
                        line.strip() for line in result.stdout.split('\\n') 
                        if line.strip()
                    ]
                    logger.debug(f"Found {len(info['printers'])} printer(s)")
        except Exception as e:
            info["printer_error"] = str(e)
            logger.warning(f"Could not retrieve printer list: {str(e)}")
        
        return info
    
    def create_test_image(self) -> str:
        """
        Create a test image for print testing.
        
        Returns:
            Path to the created test image
            
        Raises:
            PrintingError: If test image creation fails
        """
        try:
            # Create a 4x6 inch test image at 300 DPI
            width, height = 1200, 1800
            image = Image.new('RGB', (width, height), 'white')
            draw = ImageDraw.Draw(image)
            
            # Draw test content
            draw.rectangle([50, 50, width-50, height-50], outline='black', width=5)
            
            # Add text content (PIL default font)
            y_offset = 100
            line_height = 80
            
            test_lines = [
                "LINECOOK PRINT TEST",
                f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"System: {platform.system()}",
                f"Print Command: {settings.print_command}",
                f"Print Enabled: {settings.print_enabled}",
                f"Print Debug: {settings.print_debug}"
            ]
            
            for line in test_lines:
                draw.text((100, y_offset), line, fill='black')
                y_offset += line_height
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(
                dir=self.temp_dir,
                suffix=".png",
                delete=False
            )
            image.save(temp_file.name, 'PNG')
            temp_file.close()
            
            logger.info(f"Created test image: {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Error creating test image: {str(e)}")
            raise PrintingError(f"Failed to create test image: {str(e)}")
    
    def test_print(self) -> Dict[str, Any]:
        """
        Perform a comprehensive print test.
        
        Returns:
            Dictionary with test results and system information
            
        Raises:
            PrintingError: If test fails critically
        """
        try:
            # Create test image
            test_image_path = self.create_test_image()
            
            # Attempt to print
            success, message = self.print_label_file(test_image_path)
            
            # Get system information
            setup_info = self.check_print_setup()
            
            result = {
                "test_attempted": True,
                "print_success": success,
                "print_message": message,
                "test_image_path": test_image_path,
                "setup_info": setup_info
            }
            
            # Clean up test file if print was successful
            if success:
                try:
                    os.unlink(test_image_path)
                    result["test_image_cleaned"] = True
                except Exception as e:
                    logger.warning(f"Could not clean up test image: {str(e)}")
                    result["test_image_cleaned"] = False
            
            return result
            
        except Exception as e:
            logger.error(f"Print test failed: {str(e)}")
            raise PrintingError(f"Print test failed: {str(e)}")


# Global print service instance
print_service = PrintService()

# Alias for backward compatibility
PrintingService = PrintService