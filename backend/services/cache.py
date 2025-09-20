"""
Research data caching service to avoid re-researching the same competitors.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from backend.models.schemas import ResearchData
from config.settings import settings

logger = logging.getLogger(__name__)

class ResearchCache:
    """
    File-based cache for storing research data to avoid expensive re-research.
    """

    def __init__(self, cache_dir: str = "data/cache"):
        # Ensure cache directory is relative to project root, not current working directory
        if not Path(cache_dir).is_absolute():
            # Find project root (where run.py is located)
            project_root = Path(__file__).parent.parent.parent
            self.cache_dir = project_root / cache_dir
        else:
            self.cache_dir = Path(cache_dir)

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_age_days = settings.max_research_age_days

        # Log cache initialization for debugging
        logger.info(f"🗂️  CACHE INIT: Cache directory: {self.cache_dir} (absolute: {self.cache_dir.resolve()})")

    def _get_cache_file_path(self, competitor: str, research_focus: str) -> Path:
        """
        Generate cache file path for a competitor and research focus.
        """
        # Create a safe filename from competitor and focus
        safe_competitor = "".join(c for c in competitor if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_focus = "".join(c for c in research_focus[:30] if c.isalnum() or c in (' ', '-', '_')).rstrip()

        filename = f"{safe_competitor}_{safe_focus}.json".replace(" ", "_").lower()
        return self.cache_dir / filename

    def get_cached_research(self, competitor: str, research_focus: str) -> Optional[ResearchData]:
        """
        Retrieve cached research data if it exists and is still valid.
        """
        try:
            cache_file = self._get_cache_file_path(competitor, research_focus)

            if not cache_file.exists():
                logger.info(f"No cache found for {competitor}")
                return None

            # Read cache file
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # Check if cache is still valid
            cached_time = datetime.fromisoformat(cache_data['cached_at'])
            expiry_time = cached_time + timedelta(days=self.max_age_days)

            if datetime.now() > expiry_time:
                logger.info(f"Cache expired for {competitor} (cached {cached_time}, expires {expiry_time})")
                # Remove expired cache
                cache_file.unlink()
                return None

            # Convert back to ResearchData object
            research_data = self._deserialize_research_data(cache_data['research_data'])

            logger.info(f"✅ Cache hit for {competitor} - data from {cached_time.strftime('%Y-%m-%d %H:%M')}")
            return research_data

        except Exception as e:
            logger.error(f"Failed to read cache for {competitor}: {str(e)}")
            return None

    def cache_research(self, competitor: str, research_focus: str, research_data: ResearchData) -> bool:
        """
        Cache research data for future use.
        """
        try:
            cache_file = self._get_cache_file_path(competitor, research_focus)

            # Serialize research data
            cache_entry = {
                'competitor': competitor,
                'research_focus': research_focus,
                'cached_at': datetime.now().isoformat(),
                'research_data': self._serialize_research_data(research_data)
            }

            # Write to cache file
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_entry, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Cached research data for {competitor}")
            return True

        except Exception as e:
            logger.error(f"Failed to cache research for {competitor}: {str(e)}")
            return False

    def _serialize_research_data(self, research_data: ResearchData) -> Dict[str, Any]:
        """
        Convert ResearchData to JSON-serializable format.
        """
        return {
            'competitor': research_data.competitor,
            'ai_narrative': research_data.ai_narrative,
            'key_initiatives': research_data.key_initiatives,
            'investment_data': research_data.investment_data,
            'market_positioning': research_data.market_positioning,
            'sources': [
                {
                    'url': source.url,
                    'title': source.title,
                    'source_type': source.source_type,
                    'publication_date': source.publication_date.isoformat(),
                    'author': source.author,
                    'credibility_score': source.credibility_score
                }
                for source in research_data.sources
            ],
            'research_timestamp': research_data.research_timestamp.isoformat(),
            'confidence_score': research_data.confidence_score
        }

    def _deserialize_research_data(self, data: Dict[str, Any]) -> ResearchData:
        """
        Convert JSON data back to ResearchData object.
        """
        from backend.models.schemas import ResearchSource

        sources = [
            ResearchSource(
                url=source['url'],
                title=source['title'],
                source_type=source['source_type'],
                publication_date=datetime.fromisoformat(source['publication_date']),
                author=source.get('author'),
                credibility_score=source['credibility_score']
            )
            for source in data['sources']
        ]

        return ResearchData(
            competitor=data['competitor'],
            ai_narrative=data['ai_narrative'],
            key_initiatives=data['key_initiatives'],
            investment_data=data.get('investment_data'),
            market_positioning=data['market_positioning'],
            sources=sources,
            research_timestamp=datetime.fromisoformat(data['research_timestamp']),
            confidence_score=data['confidence_score']
        )

    def clear_cache(self, competitor: Optional[str] = None) -> int:
        """
        Clear cache for a specific competitor or all cache files.
        Returns number of files deleted.
        """
        try:
            deleted_count = 0

            if competitor:
                # Clear cache for specific competitor
                pattern = f"{competitor.lower().replace(' ', '_')}_*.json"
                for cache_file in self.cache_dir.glob(pattern):
                    cache_file.unlink()
                    deleted_count += 1
                    logger.info(f"Deleted cache file: {cache_file.name}")
            else:
                # Clear all cache files
                for cache_file in self.cache_dir.glob("*.json"):
                    cache_file.unlink()
                    deleted_count += 1

            logger.info(f"Cleared {deleted_count} cache files")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to clear cache: {str(e)}")
            return 0

    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get information about cached research data.
        """
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            cache_info = []

            for cache_file in cache_files:
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)

                    cached_time = datetime.fromisoformat(cache_data['cached_at'])
                    expiry_time = cached_time + timedelta(days=self.max_age_days)
                    is_expired = datetime.now() > expiry_time

                    cache_info.append({
                        'competitor': cache_data['competitor'],
                        'research_focus': cache_data['research_focus'],
                        'cached_at': cached_time.isoformat(),
                        'expires_at': expiry_time.isoformat(),
                        'is_expired': is_expired,
                        'sources_count': len(cache_data['research_data']['sources']),
                        'confidence_score': cache_data['research_data']['confidence_score']
                    })

                except Exception as e:
                    logger.warning(f"Failed to read cache file {cache_file}: {str(e)}")

            return {
                'total_cached': len(cache_info),
                'expired_count': sum(1 for info in cache_info if info['is_expired']),
                'cache_entries': sorted(cache_info, key=lambda x: x['cached_at'], reverse=True)
            }

        except Exception as e:
            logger.error(f"Failed to get cache info: {str(e)}")
            return {'total_cached': 0, 'expired_count': 0, 'cache_entries': []}

    def cleanup_expired_cache(self) -> int:
        """
        Remove expired cache files.
        Returns number of files deleted.
        """
        try:
            deleted_count = 0
            current_time = datetime.now()

            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)

                    cached_time = datetime.fromisoformat(cache_data['cached_at'])
                    expiry_time = cached_time + timedelta(days=self.max_age_days)

                    if current_time > expiry_time:
                        cache_file.unlink()
                        deleted_count += 1
                        logger.info(f"Deleted expired cache: {cache_file.name}")

                except Exception as e:
                    logger.warning(f"Failed to process cache file {cache_file}: {str(e)}")

            logger.info(f"Cleaned up {deleted_count} expired cache files")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup expired cache: {str(e)}")
            return 0

# Global cache instance
research_cache = ResearchCache()