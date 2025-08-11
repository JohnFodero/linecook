"""
Computer vision inference service for LineCook.

This module handles all interactions with the Roboflow inference API,
providing a clean interface for label detection functionality.
"""

import logging
from typing import Dict, Any, Union, List
from pathlib import Path

from PIL import Image
from inference_sdk import InferenceHTTPClient, InferenceConfiguration

from config import settings, TARGET_RATIOS


logger = logging.getLogger(__name__)


class InferenceService:
    """
    Service for handling computer vision inference operations.
    
    This service encapsulates all interactions with the Roboflow API,
    providing secure API key handling and consistent error management.
    """
    
    def __init__(self, api_key: str, model_id: str, confidence_threshold: float = 0.04):
        """
        Initialize the inference service.
        
        Args:
            api_key: Roboflow API key for authentication
            model_id: Model identifier for inference
            confidence_threshold: Minimum confidence for predictions
        """
        self.api_key = api_key
        self.model_id = model_id
        self.confidence_threshold = confidence_threshold
        
        # Configure inference settings
        self.config = InferenceConfiguration(
            confidence_threshold=confidence_threshold
        )
        
        # Initialize client with secure API key handling
        self.client = InferenceHTTPClient(
            api_url="https://serverless.roboflow.com/",
            api_key=api_key
        )
        
        logger.info(f"Initialized inference service with model {model_id}")
    
    def infer_image(self, image_input: Union[str, Path, Image.Image]) -> Dict[str, Any]:
        """
        Run inference on an image to detect shipping labels.
        
        This method consolidates the previous infer_image() and infer_image_pil()
        functions, accepting either file paths or PIL Image objects.
        
        Args:
            image_input: Either a file path (str/Path) or PIL Image object
            
        Returns:
            Dictionary containing inference results with predictions
            
        Raises:
            ValueError: If image_input type is not supported
            Exception: If inference fails
        """
        try:
            # Handle different input types
            if isinstance(image_input, (str, Path)):
                # Load image from file path
                image = Image.open(image_input)
                logger.debug(f"Loaded image from path: {image_input}")
            elif isinstance(image_input, Image.Image):
                # Use PIL Image directly
                image = image_input
                logger.debug("Using provided PIL Image object")
            else:
                raise ValueError(f"Unsupported image input type: {type(image_input)}")
            
            # Run inference with configured settings
            with self.client.use_configuration(self.config):
                results = self.client.infer(image, model_id=self.model_id)
            
            prediction_count = len(results.get("predictions", []))
            logger.info(f"Inference completed: {prediction_count} predictions found")
            
            return results
            
        except Exception as e:
            logger.error(f"Inference failed: {str(e)}")
            raise
    
    def pick_best_prediction(self, predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Select the best shipping label prediction based on aspect ratio.
        
        Shipping labels typically have a 4:6 or 6:4 aspect ratio. This method
        scores predictions based on how close they are to these target ratios.
        
        Args:
            predictions: List of prediction dictionaries from inference
            
        Returns:
            The prediction with the best aspect ratio score
            
        Raises:
            ValueError: If predictions list is empty
        """
        if not predictions:
            raise ValueError("No predictions provided")
        
        def aspect_ratio_score(pred: Dict[str, Any]) -> float:
            """Calculate aspect ratio score for a prediction."""
            width, height = pred["width"], pred["height"]
            if height == 0:
                return float('inf')  # Avoid division by zero
            
            ratio = width / height
            # Find minimum distance to target ratios
            return min(abs(ratio - target) for target in TARGET_RATIOS)
        
        best_prediction = min(predictions, key=aspect_ratio_score)
        best_score = aspect_ratio_score(best_prediction)
        
        logger.info(f"Selected best prediction with aspect ratio score: {best_score:.3f}")
        logger.debug(f"Best prediction dimensions: {best_prediction['width']}x{best_prediction['height']}")
        
        return best_prediction
    
    def detect_labels(self, image_input: Union[str, Path, Image.Image]) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Detect shipping labels in an image and return the best prediction.
        
        This is a high-level method that combines inference and prediction selection.
        
        Args:
            image_input: Either a file path (str/Path) or PIL Image object
            
        Returns:
            Tuple of (all_predictions, best_prediction)
            
        Raises:
            ValueError: If no labels are detected
        """
        results = self.infer_image(image_input)
        predictions = results.get("predictions", [])
        
        if not predictions:
            raise ValueError("No shipping labels detected in image")
        
        best_prediction = self.pick_best_prediction(predictions)
        
        return predictions, best_prediction


# Global inference service instance
inference_service = InferenceService(
    api_key=settings.roboflow_api_key,
    model_id=settings.model_id,
    confidence_threshold=settings.confidence_thresh
)