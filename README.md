# LineCook - Shipping Label Detection API

This is designed to solve a super narrow problem - when using a label printer you have to download, crop, save all before printing. This makes the benefits of having a label printer setup marginal at best. This tool automates the label detection, crop, rotation, and printing all into one API. 

## Installation & Setup

### Prerequisites

- [uv](https://github.com/astral-sh/uv) package manager
- Roboflow API key

### Environment Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd linecook
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Configure environment variables**:
   Create a `.env` file in the project root:
   ```env
   ROBOFLOW_API_KEY=your_api_key_here
   ```

  __Note__: see `.env.example` for more configuration options
## API Usage

### Starting the Server

```bash
# Using Justfile (recommended)
just serve
```

The API will be available at `http://localhost:8000` with interactive documentation at `http://localhost:8000/docs`.

### Available Endpoints

#### 1. Process Labels - `POST /create_labels`

Detects and extracts shipping labels from uploaded files.

**Parameters:**
- `file` (required): Uploaded file (PDF, JPG, JPEG, or PNG)
- `print_label` (optional): Boolean flag to print the label after processing (default: false)

**Example Request:**
```bash
curl -X POST "http://localhost:8000/create_labels" \
  -F "file=@shipping_document.pdf" \
  -F "print_label=false"
```

**Example Response (Success):**
```json
{
  "success": true,
  "message": "Label successfully detected and processed",
  "label_dimensions": {
    "width": 1200,
    "height": 1800
  },
  "image_data": "iVBORw0KGgoAAAANSUhEUgAA...",
  "confidence": 0.85,
  "print_attempted": false
}
```

**Example Response (No Label Found):**
```json
{
  "success": false,
  "message": "No labels detected in image"
}
```

### Response Format Details

**Successful Label Detection:**
- `success`: Boolean indicating operation success
- `message`: Human-readable status message
- `label_dimensions`: Object with width/height of cropped label
- `image_data`: Base64-encoded PNG image of the cropped label
- `confidence`: Detection confidence score (0.0 - 1.0)
- `print_attempted`: Boolean (only present if print_label=true)
- `print_success`: Boolean (only present if printing was attempted)
- `print_error`: String error message (only present if printing failed)

**Error Responses:**
- `400`: Unsupported file type
- `404`: No labels detected in the uploaded file
- `500`: Processing error (with error details)

## Configuration

### Model Configuration

The application uses the following configuration:

- **Model ID**: `shipping-label-k3hzg/4` (Roboflow custom model)
- **Confidence Threshold**: 0.04 (yes this is low, but this + aspect ratio filtering seems to have the highest success rate)
- **Target Label Ratios**: 4:6 or 6:4 (standard shipping label dimensions)
- **Output Size**: 1200x1800 pixels (4x6 inches at 300 DPI)

### Supported File Types

- **Images**: JPG, JPEG, PNG
- **Documents**: PDF (all pages processed, first detected label returned)
