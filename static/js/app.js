/**
 * LineCook Web Interface JavaScript
 * Handles file upload, processing, preview, and download functionality
 */

class LineCookApp {
    constructor() {
        this.selectedFile = null;
        this.processedImageData = null;
        this.initializeElements();
        this.setupEventListeners();
    }

    initializeElements() {
        // File upload elements
        this.uploadArea = document.getElementById('uploadArea');
        this.fileInput = document.getElementById('fileInput');
        this.fileInfo = document.getElementById('fileInfo');
        this.fileName = document.getElementById('fileName');
        this.fileSize = document.getElementById('fileSize');
        this.removeFileBtn = document.getElementById('removeFile');

        // Action elements
        this.actionButtons = document.getElementById('actionButtons');
        this.convertBtn = document.getElementById('convertBtn');
        this.printBtn = document.getElementById('printBtn');

        // Message and results elements
        this.messageArea = document.getElementById('messageArea');
        this.message = document.getElementById('message');
        this.resultsSection = document.getElementById('resultsSection');
        this.processedImage = document.getElementById('processedImage');
        this.labelDimensions = document.getElementById('labelDimensions');
        this.labelConfidence = document.getElementById('labelConfidence');
        this.downloadBtn = document.getElementById('downloadBtn');
        this.printStatus = document.getElementById('printStatus');
        this.printMessage = document.getElementById('printMessage');
    }

    setupEventListeners() {
        // File upload events
        this.uploadArea.addEventListener('click', () => this.fileInput.click());
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e.target.files[0]));
        this.removeFileBtn.addEventListener('click', () => this.clearFile());

        // Drag and drop events
        this.uploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.uploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.uploadArea.addEventListener('drop', (e) => this.handleDrop(e));

        // Action button events
        this.convertBtn.addEventListener('click', () => this.processFile(false));
        this.printBtn.addEventListener('click', () => this.processFile(true));

        // Download button event
        this.downloadBtn.addEventListener('click', () => this.downloadProcessedImage());
    }

    handleDragOver(e) {
        e.preventDefault();
        this.uploadArea.classList.add('dragover');
    }

    handleDragLeave(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('dragover');
    }

    handleDrop(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.handleFileSelect(files[0]);
        }
    }

    handleFileSelect(file) {
        if (!file) return;

        // Validate file type
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf'];
        if (!allowedTypes.includes(file.type)) {
            this.showMessage('Please select a valid image file (JPG, JPEG, PNG) or PDF.', 'error');
            return;
        }

        // Validate file size (max 50MB)
        const maxSize = 50 * 1024 * 1024; // 50MB
        if (file.size > maxSize) {
            this.showMessage('File is too large. Please select a file smaller than 50MB.', 'error');
            return;
        }

        this.selectedFile = file;
        this.displayFileInfo(file);
        this.hideMessage();
        this.hideResults();
    }

    displayFileInfo(file) {
        this.fileName.textContent = file.name;
        this.fileSize.textContent = this.formatFileSize(file.size);
        this.fileInfo.style.display = 'flex';
        this.actionButtons.style.display = 'flex';
    }

    clearFile() {
        this.selectedFile = null;
        this.fileInput.value = '';
        this.fileInfo.style.display = 'none';
        this.actionButtons.style.display = 'none';
        this.hideMessage();
        this.hideResults();
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async processFile(shouldPrint = false) {
        if (!this.selectedFile) {
            this.showMessage('Please select a file first.', 'error');
            return;
        }

        const button = shouldPrint ? this.printBtn : this.convertBtn;
        const buttonText = button.querySelector('.btn-text');
        const spinner = button.querySelector('.spinner');

        // Show loading state
        button.disabled = true;
        buttonText.style.display = 'none';
        spinner.style.display = 'inline';
        this.hideMessage();
        this.hideResults();

        try {
            const formData = new FormData();
            formData.append('file', this.selectedFile);
            formData.append('print_label', shouldPrint.toString());

            const response = await fetch('/create_labels', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.displayResults(result, shouldPrint);
                this.showMessage(
                    shouldPrint && result.print_attempted 
                        ? `Label processed successfully. Print ${result.print_success ? 'succeeded' : 'failed'}.`
                        : 'Label processed successfully!', 
                    'success'
                );
            } else {
                // Handle different error cases
                if (response.status === 404) {
                    this.showMessage('No shipping labels were detected in the uploaded file. Please try a different image with a clearly visible shipping label.', 'error');
                } else {
                    this.showMessage(result.detail || result.message || 'Processing failed. Please try again.', 'error');
                }
            }
        } catch (error) {
            console.error('Processing error:', error);
            this.showMessage('Network error occurred. Please check your connection and try again.', 'error');
        } finally {
            // Reset button state
            button.disabled = false;
            buttonText.style.display = 'inline';
            spinner.style.display = 'none';
        }
    }

    displayResults(result, wasPrintRequest) {
        // Store image data for download
        this.processedImageData = result.image_data;

        // Display processed image
        this.processedImage.src = `data:image/png;base64,${result.image_data}`;

        // Display label information
        const dimensions = result.label_dimensions;
        this.labelDimensions.textContent = `${dimensions.width} × ${dimensions.height}px`;
        
        if (result.confidence !== null && result.confidence !== undefined) {
            this.labelConfidence.textContent = `Confidence: ${(result.confidence * 100).toFixed(1)}%`;
        } else {
            this.labelConfidence.textContent = '';
        }

        // Handle print status if this was a print request
        if (wasPrintRequest && result.print_attempted) {
            this.printStatus.style.display = 'block';
            this.printStatus.className = `print-status ${result.print_success ? 'success' : 'error'}`;
            this.printMessage.textContent = result.print_message || 'Print status unknown';
        } else {
            this.printStatus.style.display = 'none';
        }

        // Show results section
        this.resultsSection.style.display = 'block';
    }

    downloadProcessedImage() {
        if (!this.processedImageData) {
            this.showMessage('No processed image available to download.', 'error');
            return;
        }

        try {
            // Convert base64 to blob
            const byteCharacters = atob(this.processedImageData);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], { type: 'image/png' });

            // Create download link
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            
            // Generate filename based on original file
            const originalName = this.selectedFile ? this.selectedFile.name : 'processed_label';
            const baseName = originalName.split('.')[0];
            link.download = `${baseName}_label.png`;

            // Trigger download
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            // Clean up
            URL.revokeObjectURL(url);

            this.showMessage('Label downloaded successfully!', 'success');
        } catch (error) {
            console.error('Download error:', error);
            this.showMessage('Failed to download image. Please try again.', 'error');
        }
    }

    showMessage(text, type = 'info') {
        this.message.textContent = text;
        this.message.className = `message ${type}`;
        this.messageArea.style.display = 'block';

        // Auto-hide success messages after 5 seconds
        if (type === 'success') {
            setTimeout(() => {
                this.hideMessage();
            }, 5000);
        }
    }

    hideMessage() {
        this.messageArea.style.display = 'none';
    }

    hideResults() {
        this.resultsSection.style.display = 'none';
        this.processedImageData = null;
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new LineCookApp();
});

// Handle global errors
window.addEventListener('error', (e) => {
    console.error('Global error:', e.error);
});

// Handle unhandled promise rejections
window.addEventListener('unhandledrejection', (e) => {
    console.error('Unhandled promise rejection:', e.reason);
});