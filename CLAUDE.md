# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LineCook is a shipping label detection and extraction tool that uses computer vision to identify and crop shipping labels from images and PDFs. It leverages the Roboflow inference API with a custom-trained model to detect labels and automatically crops them to standardized dimensions.

## Development Environment

This project uses `uv` for Python dependency management. Always use `uv run python` instead of direct python calls to ensure the correct environment with all dependencies.

### Key Dependencies
- `inference>=0.51.3` - Roboflow inference SDK for computer vision
- `pdf2image>=1.17.0` - PDF to image conversion
- `PIL` (Pillow) - Image processing
- `supervision>=0.26.1` - Computer vision utilities

## Common Commands

```bash
# Run the application on test inputs
uv run python main.py

# Install/update dependencies
uv sync

# Run Python REPL with project dependencies
uv run python
```

## Configuration

The application requires a `.env` file with:
```
ROBOFLOW_API_KEY=your_api_key_here
```

## Architecture

### Core Components

**main.py** - Single-file application with these key functions:

- `infer_image(image_path)` - Runs inference on image files
- `infer_image_pil(image)` - Runs inference on PIL Image objects
- `crop_and_save_prediction(image, pred, output_path)` - Crops detected labels and saves them
- `pick_best_prediction(predictions)` - Selects the best label based on aspect ratio (4:6 or 6:4)
- `run_app(image_path)` - Main processing function that handles both images and PDFs

### Processing Flow

1. Input files are read from `test_inputs/` directory
2. For PDFs: Each page is converted to an image at 300 DPI
3. Images are sent to Roboflow model `shipping-label-k3hzg/4` for inference
4. Multiple predictions are filtered by aspect ratio to find the best shipping label
5. Labels are cropped, rotated to portrait orientation if needed
6. Output images are saved to `test_outputs/` directory

### Model Configuration

- **Model ID**: `shipping-label-k3hzg/4`
- **Confidence Threshold**: 0.04 (very low to catch faint labels)
- **Target Label Ratios**: 4:6 or 6:4 (standard shipping label dimensions)

## File Structure

- `main.py` - Main application logic
- `test_inputs/` - Input images and PDFs for processing
- `test_outputs/` - Processed/cropped label images
- `pyproject.toml` - Project dependencies and metadata
- `uv.lock` - Dependency lock file
- `.env` - Environment variables (not committed)

## Development Notes

The application processes all supported files (`*.pdf`, `*.jpg`, `*.jpeg`) in the `test_inputs/` directory when run. Output images are automatically named based on the input filename with page numbers for PDFs.