"""
Image Matching System for LEGO Minifigure Identification
Uses computer vision to match uploaded images against database
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import sqlite3
import logging
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class MatchResult:
    """Result of image matching"""
    minifigure_id: int
    item_number: str
    name: str
    theme: str
    confidence: float
    match_type: str  # 'exact', 'similar', 'partial'
    image_path: str
    year_released: Optional[int] = None

class ImageMatcher:
    """Matches uploaded images against minifigure database"""
    
    def __init__(self, db_path: str = "data/minifigure_database.db"):
        self.db_path = db_path
        self.images_dir = Path("data/minifigure_images")
        
        # Initialize feature detectors
        self.sift = cv2.SIFT_create()
        self.orb = cv2.ORB_create()
        
        # Feature matching parameters
        self.match_threshold = 0.7
        self.min_matches = 10
        
    def extract_features(self, image_path: str) -> Dict[str, np.ndarray]:
        """Extract features from an image for matching"""
        try:
            image = cv2.imread(str(image_path))
            if image is None:
                return {}
                
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Extract SIFT features
            sift_keypoints, sift_descriptors = self.sift.detectAndCompute(gray, None)
            
            # Extract ORB features
            orb_keypoints, orb_descriptors = self.orb.detectAndCompute(gray, None)
            
            # Extract color histogram
            hist = self._extract_color_histogram(image)
            
            return {
                'sift_keypoints': sift_keypoints,
                'sift_descriptors': sift_descriptors,
                'orb_keypoints': orb_keypoints,
                'orb_descriptors': orb_descriptors,
                'color_histogram': hist
            }
            
        except Exception as e:
            logger.error(f"Error extracting features from {image_path}: {e}")
            return {}
    
    def _extract_color_histogram(self, image: np.ndarray) -> np.ndarray:
        """Extract color histogram features"""
        # Convert to HSV for better color analysis
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Calculate histogram for each channel
        hist_h = cv2.calcHist([hsv], [0], None, [50], [0, 180])
        hist_s = cv2.calcHist([hsv], [1], None, [60], [0, 256])
        hist_v = cv2.calcHist([hsv], [2], None, [60], [0, 256])
        
        # Normalize and concatenate
        hist_h = cv2.normalize(hist_h, hist_h).flatten()
        hist_s = cv2.normalize(hist_s, hist_s).flatten()
        hist_v = cv2.normalize(hist_v, hist_v).flatten()
        
        return np.concatenate([hist_h, hist_s, hist_v])
    
    def match_features(self, query_features: Dict[str, np.ndarray], 
                      database_features: Dict[str, np.ndarray]) -> float:
        """Calculate similarity score between two feature sets"""
        try:
            scores = []
            
            # SIFT matching
            if (query_features.get('sift_descriptors') is not None and 
                database_features.get('sift_descriptors') is not None):
                sift_score = self._match_sift_features(
                    query_features['sift_descriptors'],
                    database_features['sift_descriptors']
                )
                scores.append(sift_score * 0.4)  # Weight SIFT more heavily
            
            # ORB matching
            if (query_features.get('orb_descriptors') is not None and 
                database_features.get('orb_descriptors') is not None):
                orb_score = self._match_orb_features(
                    query_features['orb_descriptors'],
                    database_features['orb_descriptors']
                )
                scores.append(orb_score * 0.3)
            
            # Color histogram matching
            if (query_features.get('color_histogram') is not None and 
                database_features.get('color_histogram') is not None):
                color_score = self._match_color_histograms(
                    query_features['color_histogram'],
                    database_features['color_histogram']
                )
                scores.append(color_score * 0.3)
            
            return sum(scores) if scores else 0.0
            
        except Exception as e:
            logger.error(f"Error matching features: {e}")
            return 0.0
    
    def _match_sift_features(self, desc1: np.ndarray, desc2: np.ndarray) -> float:
        """Match SIFT features using FLANN matcher"""
        try:
            # FLANN parameters
            FLANN_INDEX_KDTREE = 1
            index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
            search_params = dict(checks=50)
            flann = cv2.FlannBasedMatcher(index_params, search_params)
            
            matches = flann.knnMatch(desc1, desc2, k=2)
            
            # Apply Lowe's ratio test
            good_matches = []
            for match_pair in matches:
                if len(match_pair) == 2:
                    m, n = match_pair
                    if m.distance < 0.7 * n.distance:
                        good_matches.append(m)
            
            # Calculate match ratio
            if len(matches) > 0:
                return len(good_matches) / len(matches)
            return 0.0
            
        except Exception as e:
            logger.error(f"Error in SIFT matching: {e}")
            return 0.0
    
    def _match_orb_features(self, desc1: np.ndarray, desc2: np.ndarray) -> float:
        """Match ORB features using brute force matcher"""
        try:
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(desc1, desc2)
            matches = sorted(matches, key=lambda x: x.distance)
            
            # Calculate match ratio
            if len(matches) > 0:
                good_matches = [m for m in matches if m.distance < 50]
                return len(good_matches) / len(matches)
            return 0.0
            
        except Exception as e:
            logger.error(f"Error in ORB matching: {e}")
            return 0.0
    
    def _match_color_histograms(self, hist1: np.ndarray, hist2: np.ndarray) -> float:
        """Match color histograms using correlation"""
        try:
            correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
            return max(0.0, correlation)
        except Exception as e:
            logger.error(f"Error in color histogram matching: {e}")
            return 0.0
    
    def find_matches(self, query_image_path: str, limit: int = 10) -> List[MatchResult]:
        """Find matches for a query image in the database"""
        try:
            # Extract features from query image
            query_features = self.extract_features(query_image_path)
            if not query_features:
                return []
            
            # Get all minifigures from database
            minifigures = self._get_all_minifigures()
            
            matches = []
            for minifig in minifigures:
                if not minifig['image_path'] or not Path(minifig['image_path']).exists():
                    continue
                
                # Extract features from database image
                db_features = self.extract_features(minifig['image_path'])
                if not db_features:
                    continue
                
                # Calculate similarity
                similarity = self.match_features(query_features, db_features)
                
                if similarity > 0.3:  # Minimum threshold
                    match_result = MatchResult(
                        minifigure_id=minifig['id'],
                        item_number=minifig['item_number'],
                        name=minifig['name'],
                        theme=minifig['theme'],
                        confidence=similarity,
                        match_type=self._determine_match_type(similarity),
                        image_path=minifig['image_path'],
                        year_released=minifig['year_released']
                    )
                    matches.append(match_result)
            
            # Sort by confidence and return top matches
            matches.sort(key=lambda x: x.confidence, reverse=True)
            return matches[:limit]
            
        except Exception as e:
            logger.error(f"Error finding matches: {e}")
            return []
    
    def _determine_match_type(self, confidence: float) -> str:
        """Determine match type based on confidence score"""
        if confidence >= 0.8:
            return 'exact'
        elif confidence >= 0.6:
            return 'similar'
        else:
            return 'partial'
    
    def _get_all_minifigures(self) -> List[Dict[str, Any]]:
        """Get all minifigures from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, item_number, name, theme, year_released, image_path
            FROM minifigures
            WHERE image_path IS NOT NULL
        """)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'item_number': row[1],
                'name': row[2],
                'theme': row[3],
                'year_released': row[4],
                'image_path': row[5]
            })
        
        conn.close()
        return results
    
    def get_minifigure_by_id(self, minifigure_id: int) -> Optional[Dict[str, Any]]:
        """Get minifigure details by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT item_number, name, theme, year_released, image_path, description
            FROM minifigures
            WHERE id = ?
        """, (minifigure_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'item_number': row[0],
                'name': row[1],
                'theme': row[2],
                'year_released': row[3],
                'image_path': row[4],
                'description': row[5]
            }
        return None

# CLI interface for testing
def main():
    """Test the image matcher"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LEGO Image Matcher")
    parser.add_argument("image", help="Path to image to match")
    parser.add_argument("--limit", type=int, default=5, help="Number of matches to return")
    
    args = parser.parse_args()
    
    matcher = ImageMatcher()
    matches = matcher.find_matches(args.image, args.limit)
    
    print(f"Found {len(matches)} matches:")
    for i, match in enumerate(matches, 1):
        print(f"{i}. {match.name} ({match.item_number}) - {match.theme}")
        print(f"   Confidence: {match.confidence:.3f} ({match.match_type})")
        print(f"   Year: {match.year_released}")
        print()

if __name__ == "__main__":
    main()
