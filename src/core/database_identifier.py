"""
Database-Driven LEGO Identifier
Combines computer vision matching with AI analysis for maximum accuracy
"""

import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

from src.models.schemas import IdentificationResult, LegoItem, ItemType, ItemCondition
from src.core.image_matcher import ImageMatcher, MatchResult
from src.core.lego_identifier import LegoIdentifier
from src.core.database_builder import MinifigureDatabaseBuilder
from src.core.mock_database_builder import MockDatabaseBuilder

logger = logging.getLogger(__name__)

class DatabaseDrivenIdentifier:
    """Enhanced identifier that uses database matching + AI analysis"""
    
    def __init__(self):
        self.image_matcher = ImageMatcher()
        self.ai_identifier = LegoIdentifier()
        self.db_builder = MinifigureDatabaseBuilder()
        self.mock_builder = MockDatabaseBuilder()
        
    async def identify_lego_items(self, image_path: str) -> IdentificationResult:
        """Identify LEGO items using database matching + AI analysis"""
        try:
            # Step 1: Database matching
            logger.info("Starting database matching...")
            db_matches = self.image_matcher.find_matches(image_path, limit=20)
            
            # Step 2: AI analysis for context and validation
            logger.info("Starting AI analysis...")
            ai_result = await self.ai_identifier.identify_lego_items(image_path)
            
            # Step 3: Combine results
            combined_result = self._combine_results(db_matches, ai_result, image_path)
            
            logger.info(f"Database matching found {len(db_matches)} matches")
            logger.info(f"AI analysis confidence: {ai_result.confidence_score:.2f}")
            logger.info(f"Combined confidence: {combined_result.confidence_score:.2f}")
            
            return combined_result
            
        except Exception as e:
            logger.error(f"Error in database-driven identification: {e}")
            # Fallback to AI-only
            return await self.ai_identifier.identify_lego_items(image_path)
    
    def _combine_results(self, db_matches: List[MatchResult], 
                        ai_result: IdentificationResult, 
                        image_path: str) -> IdentificationResult:
        """Combine database matches with AI analysis"""
        
        # Convert database matches to LegoItem objects
        identified_items = []
        confidence_scores = []
        
        for match in db_matches:
            if match.confidence >= 0.4:  # Minimum threshold for inclusion
                lego_item = LegoItem(
                    item_number=match.item_number,
                    name=match.name,
                    item_type=ItemType.MINIFIGURE,
                    condition=self._assess_condition_from_ai(ai_result, match.name),
                    year_released=match.year_released,
                    theme=match.theme,
                    category=self._extract_category_from_name(match.name),
                    pieces=None  # Could be populated from database
                )
                identified_items.append(lego_item)
                confidence_scores.append(match.confidence)
        
        # If no good database matches, use AI results
        if not identified_items and ai_result.identified_items:
            identified_items = ai_result.identified_items
            confidence_scores = [ai_result.confidence_score] * len(identified_items)
        
        # Calculate combined confidence
        if confidence_scores:
            avg_confidence = sum(confidence_scores) / len(confidence_scores)
            # Boost confidence if we have database matches
            if db_matches:
                avg_confidence = min(1.0, avg_confidence + 0.2)
        else:
            avg_confidence = 0.1
        
        # Create enhanced description
        description = self._create_enhanced_description(db_matches, ai_result)
        
        # Enhanced condition assessment
        condition_assessment = self._create_enhanced_condition_assessment(
            db_matches, ai_result
        )
        
        return IdentificationResult(
            confidence_score=avg_confidence,
            identified_items=identified_items,
            description=description,
            condition_assessment=condition_assessment
        )
    
    def _assess_condition_from_ai(self, ai_result: IdentificationResult, 
                                 item_name: str) -> ItemCondition:
        """Assess condition using AI analysis"""
        # Look for this item in AI results
        for item in ai_result.identified_items:
            if item_name.lower() in item.name.lower() or item.name.lower() in item_name.lower():
                return item.condition
        
        # Default to used_complete if not found
        return ItemCondition.USED_COMPLETE
    
    def _extract_category_from_name(self, name: str) -> Optional[str]:
        """Extract category from minifigure name"""
        name_lower = name.lower()
        
        # Common categories
        categories = {
            'police': ['police', 'officer', 'cop'],
            'construction': ['construction', 'worker', 'builder'],
            'chef': ['chef', 'cook', 'baker'],
            'astronaut': ['astronaut', 'space', 'pilot'],
            'ninja': ['ninja', 'warrior', 'fighter'],
            'superhero': ['spider', 'batman', 'superman', 'hero'],
            'civilian': ['civilian', 'person', 'figure'],
            'wizard': ['wizard', 'magic', 'sorcerer'],
            'knight': ['knight', 'warrior', 'soldier'],
            'pirate': ['pirate', 'sailor', 'captain']
        }
        
        for category, keywords in categories.items():
            if any(keyword in name_lower for keyword in keywords):
                return category
        
        return None
    
    def _create_enhanced_description(self, db_matches: List[MatchResult], 
                                   ai_result: IdentificationResult) -> str:
        """Create enhanced description combining database and AI info"""
        
        if not db_matches:
            return ai_result.description
        
        # Group matches by theme
        themes = {}
        for match in db_matches:
            if match.theme not in themes:
                themes[match.theme] = []
            themes[match.theme].append(match)
        
        # Create description
        parts = []
        
        if len(themes) == 1:
            theme = list(themes.keys())[0]
            matches = themes[theme]
            parts.append(f"Collection of {len(matches)} {theme} minifigures")
        else:
            parts.append(f"Collection of {len(db_matches)} minifigures from {len(themes)} different themes")
        
        # Add specific items
        specific_items = []
        for match in db_matches[:5]:  # Top 5 matches
            if match.confidence >= 0.6:
                specific_items.append(match.name)
        
        if specific_items:
            parts.append(f"Identified items include: {', '.join(specific_items)}")
        
        # Add AI context if available
        if ai_result.description and "Collection of" not in ai_result.description:
            parts.append(f"Additional context: {ai_result.description}")
        
        return ". ".join(parts) + "."
    
    def _create_enhanced_condition_assessment(self, db_matches: List[MatchResult], 
                                            ai_result: IdentificationResult) -> str:
        """Create enhanced condition assessment"""
        
        # Start with AI assessment
        ai_condition = ai_result.condition_assessment or "Condition assessment not available"
        
        # Add database context
        if db_matches:
            high_confidence_matches = [m for m in db_matches if m.confidence >= 0.7]
            if high_confidence_matches:
                ai_condition += f" Database matching found {len(high_confidence_matches)} high-confidence matches."
        
        return ai_condition
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        # Check both real and mock databases
        real_count = self.db_builder.get_minifigure_count()
        mock_count = self.mock_builder.get_minifigure_count()
        
        return {
            'total_minifigures': real_count + mock_count,
            'real_database_count': real_count,
            'mock_database_count': mock_count,
            'database_path': self.db_builder.db_path,
            'images_directory': str(self.db_builder.images_dir)
        }
    
    def search_database(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search the minifigure database"""
        # Search both real and mock databases
        real_results = self.db_builder.search_minifigures(query, limit)
        mock_results = self.mock_builder.search_minifigures(query, limit)
        
        # Combine and deduplicate
        all_results = real_results + mock_results
        seen = set()
        unique_results = []
        for result in all_results:
            key = result['item_number']
            if key not in seen:
                seen.add(key)
                unique_results.append(result)
        
        return unique_results[:limit]

# CLI interface for testing
async def main():
    """Test the database-driven identifier"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database-Driven LEGO Identifier")
    parser.add_argument("image", help="Path to image to identify")
    parser.add_argument("--search", help="Search database for minifigures")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    
    args = parser.parse_args()
    
    identifier = DatabaseDrivenIdentifier()
    
    if args.stats:
        stats = identifier.get_database_stats()
        print(f"Database Statistics:")
        print(f"  Total minifigures: {stats['total_minifigures']}")
        print(f"  Database path: {stats['database_path']}")
        print(f"  Images directory: {stats['images_directory']}")
        return
    
    if args.search:
        results = identifier.search_database(args.search)
        print(f"Search results for '{args.search}':")
        for result in results:
            print(f"  {result['item_number']}: {result['name']} ({result['theme']})")
        return
    
    # Identify image
    result = await identifier.identify_lego_items(args.image)
    
    print(f"Identification Results:")
    print(f"  Confidence: {result.confidence_score:.2f}")
    print(f"  Items found: {len(result.identified_items)}")
    print(f"  Description: {result.description}")
    print()
    
    for i, item in enumerate(result.identified_items, 1):
        print(f"{i}. {item.name}")
        print(f"   Item Number: {item.item_number or 'Unknown'}")
        print(f"   Theme: {item.theme}")
        print(f"   Condition: {item.condition}")
        print(f"   Year: {item.year_released or 'Unknown'}")
        print()

if __name__ == "__main__":
    asyncio.run(main())
